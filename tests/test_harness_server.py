"""Tests for the WebSocket protocol of `harness.server.create_app`."""
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from harness_fixtures import make_campaign, open_engine  # noqa: E402

from solo_roll.harness.server import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path):
    engine = open_engine(make_campaign(tmp_path))
    return TestClient(create_app(engine))


def test_a_new_connection_gets_the_state_and_available_actions(client):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()

    assert hello["type"] == "snapshot"
    assert hello["state"]["party"]["area"] == "gate"
    assert [a["id"] for a in hello["actions"]] == ["move:hall"]


def test_a_move_command_returns_its_events_with_the_new_state(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        reply = ws.receive_json()

    assert reply["type"] == "events"
    assert [e["type"] for e in reply["events"]] == ["moved", "area_revealed"]
    assert reply["state"]["party"]["area"] == "hall"
    assert {a["id"] for a in reply["actions"]} == {"move:gate", "move:crypt"}


def test_a_refused_command_returns_an_error_and_the_socket_stays_open(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "crypt"}})
        error = ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        reply = ws.receive_json()

    assert error["type"] == "error"
    assert "crypt" in error["message"]
    assert reply["type"] == "events"


def test_an_unknown_message_type_returns_an_error(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "dance"})
        error = ws.receive_json()

    assert error["type"] == "error"


def test_events_reach_every_open_connection(client):
    with client.websocket_connect("/ws") as mover, client.websocket_connect("/ws") as watcher:
        mover.receive_json()
        watcher.receive_json()
        mover.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        mover.receive_json()
        seen = watcher.receive_json()

    assert seen["type"] == "events"
    assert seen["state"]["party"]["area"] == "hall"


def test_the_built_web_app_is_served_at_the_root(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>harness</title>")
    engine = open_engine(make_campaign(tmp_path))

    response = TestClient(create_app(engine, web_dist=dist)).get("/")

    assert response.status_code == 200
    assert "harness" in response.text
