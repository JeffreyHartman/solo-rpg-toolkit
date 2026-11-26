"""The harness server: one WebSocket for the open campaign, plus the built web app.

Messages from the server, each a JSON object with a `type`:
  snapshot  {state, actions, settings} sent on connect when a campaign is open, and to every
                                      connection when a campaign is opened
  library   {campaigns, plugins}      sent on connect when no campaign is open, and in reply to
                                      list_campaigns; `plugins` maps each kind to installed names
  events    {events, state, actions}  sent to every connection after a command,
                                      including one a Referee tool ran
  player    {text}                    sent to every connection: the player's free text
  referee   {event}                   sent to every connection: one `referee.events` event
  settings  {settings}                sent to every connection after a setting changes
  error     {message}                 sent only to the connection that caused it

Pending judgment calls reach the browser in `state.judgments.pending`. Pending proposals reach it in `state.proposals.pending`; the events of
a proposal include a `proposal` event.

Messages from the browser:
  act       {command}                 run one engine command; the Referee then narrates it
  say       {text}                    free text for the Referee
  answer    {id, answer, inputs?}     answer a proposal: confirm, change (with the
                                      changed inputs) or reject; the Referee then narrates it
  answer_judgment {id, answer}        answer a judgment call card; the Referee then narrates it
  set_setting {section, key, value}   change one campaign setting
  list_campaigns {}                   ask for the library
  new_campaign {name, ruleset, generators, module?}  create a campaign and open it
  open_campaign {id}                  open a saved campaign

Referee turns run one at a time in the background, so `act` and `say` are
accepted while a turn streams; a `say` waits for the turn before it.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .engine import Engine
from .errors import HarnessError
from .library import Library
from .referee.base import Referee

__all__ = ["create_app"]

NO_BUILD_PAGE = """<!doctype html><meta charset="utf-8"><title>Harness</title>
<p>The web app is not built. Run <code>npm install && npm run build</code> in
<code>web/</code>, or run <code>npm run dev</code> there and open the Vite URL.</p>"""


class _Hub:
    def __init__(self, engine: Engine | None, referee: Referee | None, library: Library | None = None):
        self.engine = engine
        self.referee = referee
        self.library = library
        self.sockets: set[WebSocket] = set()
        self._turn_lock = asyncio.Lock()
        self._turns: set[asyncio.Task] = set()

    def snapshot(self) -> dict[str, Any]:
        assert self.engine is not None
        return {"state": self.engine.state(), "actions": self.engine.available_actions()}

    def snapshot_message(self) -> dict[str, Any]:
        assert self.engine is not None
        return {"type": "snapshot", **self.snapshot(), "settings": self.engine.settings()}

    def first_message(self) -> dict[str, Any]:
        if self.engine is None:
            return self.library_message()
        return self.snapshot_message()

    def library_message(self) -> dict[str, Any]:
        if self.library is None:
            return {"type": "library", "campaigns": [], "plugins": {}}
        return {"type": "library", "campaigns": self.library.campaigns(), "plugins": self.library.installed()}

    async def _switch(self, ws: WebSocket, create: dict[str, Any] | None, campaign_id: str | None) -> None:
        if self.library is None:
            await ws.send_json({"type": "error", "message": "This server has no campaign folder."})
            return
        try:
            if create is not None:
                campaign_id = self.library.create(
                    str(create.get("name") or ""),
                    ruleset=str(create.get("ruleset") or ""),
                    generators=list(create.get("generators") or []),
                    module=create.get("module") or None,
                )
            engine, referee = self.library.open(str(campaign_id))
        except HarnessError as exc:
            await ws.send_json({"type": "error", "message": str(exc)})
            return
        await self.close()
        self.engine, self.referee = engine, referee
        await self._broadcast(self.snapshot_message())

    async def handle(self, ws: WebSocket, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "list_campaigns":
            await ws.send_json(self.library_message())
        elif kind == "new_campaign":
            await self._switch(ws, message, None)
        elif kind == "open_campaign":
            await self._switch(ws, None, message.get("id"))
        elif self.engine is None and kind in ("act", "say", "answer", "answer_judgment", "set_setting"):
            await ws.send_json({"type": "error", "message": "No campaign is open."})
        elif kind == "act":
            await self._act(ws, message.get("command") or {})
        elif kind == "say":
            await self._say(ws, str(message.get("text") or ""))
        elif kind == "answer":
            command = {"type": "answer_proposal", "id": message.get("id"), "answer": message.get("answer")}
            if message.get("inputs") is not None:
                command["inputs"] = message["inputs"]
            await self._act(ws, command, lead="The player answered a proposal.")
        elif kind == "answer_judgment":
            command = {"type": "answer_judgment", "id": message.get("id"), "answer": message.get("answer")}
            await self._act(ws, command, lead="The player answered a judgment call.")
        elif kind == "set_setting":
            await self._set_setting(ws, message)
        else:
            await ws.send_json({"type": "error", "message": f"unknown message type {kind!r}"})

    async def _act(self, ws: WebSocket, command: dict[str, Any], lead: str = "The player clicked an action.") -> None:
        assert self.engine is not None
        try:
            events = self.engine.act(command)
        except HarnessError as exc:
            await ws.send_json({"type": "error", "message": str(exc)})
            return
        await self._broadcast_events(events)
        if self.referee is not None and events:
            self._start_turn(_narration_request(lead, events))

    async def _set_setting(self, ws: WebSocket, message: dict[str, Any]) -> None:
        assert self.engine is not None
        try:
            self.engine.change_setting(str(message.get("section")), str(message.get("key")), message.get("value"))
        except HarnessError as exc:
            await ws.send_json({"type": "error", "message": str(exc)})
            return
        await self._broadcast({"type": "settings", "settings": self.engine.settings()})

    async def _say(self, ws: WebSocket, text: str) -> None:
        if self.referee is None:
            await ws.send_json({"type": "error", "message": "No Referee is running for this campaign."})
            return
        await self._broadcast({"type": "player", "text": text})
        self._start_turn(text)

    def _start_turn(self, player_input: str) -> None:
        task = asyncio.create_task(self._run_turn(player_input))
        self._turns.add(task)
        task.add_done_callback(self._turns.discard)

    async def _run_turn(self, player_input: str) -> None:
        assert self.referee is not None
        async with self._turn_lock:
            try:
                async for event in self.referee.turn(player_input):
                    await self._broadcast({"type": "referee", "event": event})
                    if event["type"] == "tool_result" and event.get("events"):
                        await self._broadcast_events(event["events"])
            # Any adapter failure (a lost CLI, an auth error) must end the turn for the UI.
            except Exception as exc:  # noqa: BLE001
                await self._broadcast({"type": "referee", "event": {"type": "done", "error": str(exc)}})

    async def _broadcast_events(self, events: list[dict[str, Any]]) -> None:
        await self._broadcast({"type": "events", "events": events, **self.snapshot()})

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        for socket in list(self.sockets):
            try:
                await socket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError):
                self.sockets.discard(socket)

    async def close(self) -> None:
        for task in list(self._turns):
            task.cancel()
        if self.referee is not None:
            await self.referee.close()


def _narration_request(lead: str, events: list[dict[str, Any]]) -> str:
    lines = "\n".join(f"- {e.get('text') or e['type']}" for e in events)
    return f"{lead} The engine reports:\n{lines}\nNarrate the result."


def create_app(
    engine: Engine | None,
    web_dist: Path | None = None,
    referee: Referee | None = None,
    library: Library | None = None,
) -> FastAPI:
    """Serve `engine`, or no campaign yet when it is None. `library` lets the browser create and open campaigns."""
    hub = _Hub(engine, referee, library)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await hub.close()

    app = FastAPI(title="solo-rpg-toolkit harness", lifespan=lifespan)

    @app.websocket("/ws")
    async def campaign_socket(ws: WebSocket) -> None:
        await ws.accept()
        hub.sockets.add(ws)
        try:
            await ws.send_json(hub.first_message())
            while True:
                await hub.handle(ws, await ws.receive_json())
        except WebSocketDisconnect:
            pass
        finally:
            hub.sockets.discard(ws)

    if web_dist is not None and (Path(web_dist) / "index.html").exists():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    else:
        @app.get("/", response_class=HTMLResponse)
        def no_build() -> str:
            return NO_BUILD_PAGE

    return app
