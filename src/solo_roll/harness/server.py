"""The harness server: one WebSocket for the open campaign, plus the built web app.

Messages from the server, each a JSON object with a `type`:
  snapshot  {state, actions}          sent once on connect
  events    {events, state, actions}  sent to every connection after a command
  error     {message}                 sent only to the connection that caused it

Messages from the browser:
  act       {command}                 run one engine command
"""
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .engine import Engine
from .errors import HarnessError

__all__ = ["create_app"]

NO_BUILD_PAGE = """<!doctype html><meta charset="utf-8"><title>Harness</title>
<p>The web app is not built. Run <code>npm install && npm run build</code> in
<code>web/</code>, or run <code>npm run dev</code> there and open the Vite URL.</p>"""


class _Hub:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.sockets: set[WebSocket] = set()

    def snapshot(self) -> dict[str, Any]:
        return {"state": self.engine.state(), "actions": self.engine.available_actions()}

    async def handle(self, ws: WebSocket, message: dict[str, Any]) -> None:
        if message.get("type") != "act":
            await ws.send_json({"type": "error", "message": f"unknown message type {message.get('type')!r}"})
            return
        try:
            events = self.engine.act(message.get("command") or {})
        except HarnessError as exc:
            await ws.send_json({"type": "error", "message": str(exc)})
            return
        payload = {"type": "events", "events": events, **self.snapshot()}
        for socket in list(self.sockets):
            await socket.send_json(payload)


def create_app(engine: Engine, web_dist: Path | None = None) -> FastAPI:
    app = FastAPI(title="solo-rpg-toolkit harness")
    hub = _Hub(engine)

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
