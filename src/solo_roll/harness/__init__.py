"""The browser harness: engine, plugin registry, and the server behind the web app.

The server needs the `harness` extra (FastAPI, uvicorn). The engine and the
plugins import only the standard library and `solo_roll`.
"""
