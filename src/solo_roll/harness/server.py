"""The harness server: one WebSocket for the open campaign, plus the built web app.

Messages from the server, each a JSON object with a `type`:
  snapshot  {state, actions, settings, context}
                                      sent on connect when a campaign is open, and to every
                                      connection when a campaign is opened; `context` is
                                      the latest `context` message, or null
  library   {campaigns, plugins}      sent on connect when no campaign is open, and in reply to
                                      list_campaigns; `plugins` maps each kind to installed names
  events    {events, state, actions}  sent to every connection after a command,
                                      including one a Referee tool ran
  player    {text}                    sent to every connection: the player's free text
  referee   {event}                   sent to every connection: one `referee.events` event
  settings  {settings}                sent to every connection after a setting changes
  context   {tokens, budget, over, parts?}
                                      sent to every connection after each Referee turn
                                      and each compact: the context reading, the budget,
                                      whether the reading passed it (a warning only), and
                                      what the Referee got that turn (`Referee.turn_context`)
  session   {session, note}           sent to every connection when the next session
                                      starts; `note` is the clean note End session wrote
  error     {message}                 sent only to the connection that caused it; an error of
                                      the End session flow that the Referee's end_session
                                      tool started goes to every connection

Pending judgment calls reach the browser in `state.judgments.pending`. Pending proposals reach it in `state.proposals.pending`; the events of
a proposal include a `proposal` event.

Messages from the browser:
  act       {command}                 run one engine command; the Referee then narrates it
  say       {text}                    free text for the Referee; the text and the Referee's
                                      narration go into the session's raw log
  answer    {id, answer, inputs?}     answer a proposal: confirm, change (with the
                                      changed inputs) or reject; the Referee then narrates it
  answer_judgment {id, answer}        answer a judgment call card; the Referee then narrates it
  set_setting {section, key, value}   change one campaign setting; a `referee` model or
                                      effort reaches the Referee before its next turn
  compact     {}                      compact the Referee conversation now
  new_session {}                      start the next session and a new Referee conversation
  end_session {}                      the Referee writes the clean session note and updates
                                      records, then the next session starts; with no note
                                      written, the session stays open and the sender gets an error;
                                      the Referee's end_session tool runs the same flow after its turn
  list_campaigns {}                   ask for the library
  new_campaign {name, ruleset, generators, module?}  create a campaign and open it
  open_campaign {id}                  open a saved campaign

Referee turns run one at a time in the background, so `act` and `say` are
accepted while a turn streams; a `say` waits for the turn before it. Referee
setting changes, compact, and the session messages wait for the turn too.
"""
import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .engine import Engine
from .errors import HarnessError
from .library import Library
from .referee.base import Referee, end_session_request
from .referee.tools import END_SESSION_TOOL
from .vault import session_note

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
        self._context: dict[str, Any] | None = None
        self._end_requested = False
        """Set when the latest turn called the Referee's end_session tool."""

    def snapshot(self) -> dict[str, Any]:
        assert self.engine is not None
        return {"state": self.engine.state(), "actions": self.engine.available_actions()}

    def snapshot_message(self) -> dict[str, Any]:
        assert self.engine is not None
        return {"type": "snapshot", **self.snapshot(), "settings": self.engine.settings(), "context": self._context}

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
        self.engine, self.referee, self._context = engine, referee, None
        await self._broadcast(self.snapshot_message())

    async def handle(self, ws: WebSocket, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "list_campaigns":
            await ws.send_json(self.library_message())
        elif kind == "new_campaign":
            await self._switch(ws, message, None)
        elif kind == "open_campaign":
            await self._switch(ws, None, message.get("id"))
        elif self.engine is None and kind in (
            "act", "say", "answer", "answer_judgment", "set_setting", "compact", "new_session", "end_session"
        ):
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
        elif kind in ("compact", "new_session", "end_session"):
            if self.referee is None:
                await ws.send_json({"type": "error", "message": "No Referee is running for this campaign."})
                return
            control = {"compact": self._compact, "new_session": self._new_session, "end_session": self._end_session}
            self._start(control[kind](ws))
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
        if self.referee is None or message.get("section") != "referee":
            return
        if message.get("key") in ("model", "effort"):
            self._start(self._apply_referee_setting(str(message["key"]), str(message.get("value"))))
        elif message.get("key") == "budget" and self._context is not None:
            self._context = self._reading(self._context["tokens"], self._context["parts"])
            await self._broadcast(self._context)

    async def _say(self, ws: WebSocket, text: str) -> None:
        if self.referee is None:
            await ws.send_json({"type": "error", "message": "No Referee is running for this campaign."})
            return
        assert self.engine is not None
        self.engine.log_chat("Player", text)
        await self._broadcast({"type": "player", "text": text})
        self._start_turn(text)

    def _start_turn(self, player_input: str) -> None:
        self._start(self._run_turn(player_input))

    def _start(self, work) -> None:
        task = asyncio.create_task(work)
        self._turns.add(task)
        task.add_done_callback(self._turns.discard)

    async def _run_turn(self, player_input: str) -> None:
        async with self._turn_lock:
            await self._stream_turn(player_input, log=True)
            if self._end_requested:
                await self._end_session_locked(self._broadcast)

    async def _stream_turn(self, player_input: str, log: bool = False) -> bool:
        """Run one Referee turn and send the context reading after it. Call with the turn lock held.

        With `log`, the narration goes into the raw log: the text after the turn's last tool call,
        since text before a tool call is a status line. Returns False if the turn ended with an error.
        """
        assert self.referee is not None
        ok = True
        self._end_requested = False
        narration: list[str] = []
        try:
            async for event in self.referee.turn(player_input):
                await self._broadcast({"type": "referee", "event": event})
                if event["type"] == "text":
                    narration.append(event["text"])
                elif event["type"] == "tool_start":
                    narration.clear()
                if event["type"] == "tool_result" and event.get("events"):
                    await self._broadcast_events(event["events"])
                if event["type"] == "tool_result" and event["tool"] == END_SESSION_TOOL and event["ok"]:
                    self._end_requested = True
                if event["type"] == "done" and event.get("error"):
                    ok = False
            if log:
                self.engine.log_chat("Referee", "".join(narration))
            await self._send_context(self.referee.turn_context())
        # Any adapter failure (a lost CLI, an auth error) must end the turn for the UI.
        except Exception as exc:  # noqa: BLE001
            await self._broadcast({"type": "referee", "event": {"type": "done", "error": str(exc)}})
            return False
        return ok

    async def _send_context(self, parts: list[dict[str, Any]] | None = None) -> None:
        """Send the context reading. With no `parts` (after a compact), the last turn's parts stay."""
        assert self.referee is not None
        tokens = await self.referee.context_usage()
        if parts is None:
            parts = self._context["parts"] if self._context else []
        self._context = self._reading(tokens, parts)
        await self._broadcast(self._context)

    def _reading(self, tokens: int | None, parts: list[dict[str, Any]]) -> dict[str, Any]:
        budget = self.engine.settings()["referee"]["budget"]
        over = tokens is not None and tokens > budget
        return {"type": "context", "tokens": tokens, "budget": budget, "over": over, "parts": parts}

    async def _apply_referee_setting(self, key: str, value: str) -> None:
        assert self.referee is not None
        async with self._turn_lock:
            try:
                await (self.referee.set_model(value) if key == "model" else self.referee.set_effort(value))
            except Exception as exc:  # noqa: BLE001
                await self._broadcast({"type": "error", "message": f"The Referee could not change {key}: {exc}"})

    async def _compact(self, ws: WebSocket) -> None:
        assert self.referee is not None
        async with self._turn_lock:
            try:
                await self.referee.compact()
                await self._send_context()
            except Exception as exc:  # noqa: BLE001
                await _send(ws, {"type": "error", "message": f"Compact failed: {exc}"})

    async def _new_session(self, ws: WebSocket) -> None:
        async with self._turn_lock:
            await self._next_session(note=None)

    async def _end_session(self, ws: WebSocket) -> None:
        async with self._turn_lock:
            await self._end_session_locked(lambda payload: _send(ws, payload))

    async def _end_session_locked(self, reply: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        """Run End session: the Referee writes the note, then the next session starts. Call with the turn lock held.

        `reply` gets the errors. An end_session tool call inside the write-up turn does not start another one.
        """
        paths = self.engine.paths
        session = self.engine.state()["session"]
        if not paths.raw_log(session).exists():
            await reply({"type": "error", "message": f"Session {session} has no play to write up yet."})
            return
        ok = await self._stream_turn(end_session_request(paths, session))
        self._end_requested = False
        if not ok:
            await reply({"type": "error", "message": "End session failed; the session stays open."})
            return
        note = session_note(paths, session)
        if note is None:
            await reply({
                "type": "error",
                "message": "The Referee did not write the session note, so the session stays open. Try End session again.",
            })
            return
        await self._next_session(note=note.relative_to(paths.vault).as_posix())

    async def _next_session(self, note: str | None) -> None:
        """Start the next session and a new Referee conversation. Call with the turn lock held."""
        assert self.referee is not None
        events = self.engine.new_session()
        if events:
            await self._broadcast_events(events)
        await self.referee.new_session()
        await self._broadcast({"type": "session", "session": self.engine.state()["session"], "note": note})

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


async def _send(ws: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await ws.send_json(payload)
    except (WebSocketDisconnect, RuntimeError):
        pass


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
