"""The harness server: one WebSocket for the open campaign, plus the built web app.

Messages from the server, each a JSON object with a `type`:
  snapshot  {state, actions}          sent once on connect
  events    {events, state, actions}  sent to every connection after a command,
                                      including one a Referee tool ran
  player    {text}                    sent to every connection: the player's free text
  referee   {event}                   sent to every connection: one `referee.events` event
  error     {message}                 sent only to the connection that caused it

Messages from the browser:
  act       {command}                 run one engine command; the Referee then narrates it
  say       {text}                    free text for the Referee

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
from .referee.base import Referee

__all__ = ["create_app"]

NO_BUILD_PAGE = """<!doctype html><meta charset="utf-8"><title>Harness</title>
<p>The web app is not built. Run <code>npm install && npm run build</code> in
<code>web/</code>, or run <code>npm run dev</code> there and open the Vite URL.</p>"""


class _Hub:
    def __init__(self, engine: Engine, referee: Referee | None):
        self.engine = engine
        self.referee = referee
        self.sockets: set[WebSocket] = set()
        self._turn_lock = asyncio.Lock()
        self._turns: set[asyncio.Task] = set()

    def snapshot(self) -> dict[str, Any]:
        return {"state": self.engine.state(), "actions": self.engine.available_actions()}

    async def handle(self, ws: WebSocket, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "act":
            await self._act(ws, message.get("command") or {})
        elif kind == "say":
            await self._say(ws, str(message.get("text") or ""))
        else:
            await ws.send_json({"type": "error", "message": f"unknown message type {kind!r}"})

    async def _act(self, ws: WebSocket, command: dict[str, Any]) -> None:
        try:
            events = self.engine.act(command)
        except HarnessError as exc:
            await ws.send_json({"type": "error", "message": str(exc)})
            return
        await self._broadcast_events(events)
        if self.referee is not None and events:
            self._start_turn(_narration_request(events))

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


def _narration_request(events: list[dict[str, Any]]) -> str:
    lines = "\n".join(f"- {e.get('text') or e['type']}" for e in events)
    return f"The player clicked an action. The engine reports:\n{lines}\nNarrate the result."


def create_app(engine: Engine, web_dist: Path | None = None, referee: Referee | None = None) -> FastAPI:
    hub = _Hub(engine, referee)

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
            await ws.send_json({"type": "snapshot", **hub.snapshot()})
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
