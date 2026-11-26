"""Tests for the WebSocket protocol of `harness.server.create_app`."""
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from harness_fixtures import make_campaign, open_engine  # noqa: E402

from solo_roll.harness.campaign import CampaignPaths  # noqa: E402
from solo_roll.harness.referee import Call, Say, ScriptedReferee  # noqa: E402
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
    assert [a["id"] for a in hello["actions"] if a["id"].startswith("move:")] == ["move:hall"]


def test_a_move_command_returns_its_events_with_the_new_state(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        reply = ws.receive_json()

    assert reply["type"] == "events"
    assert [e["type"] for e in reply["events"]] == ["moved", "area_revealed"]
    assert reply["state"]["party"]["area"] == "hall"
    assert {a["id"] for a in reply["actions"] if a["id"].startswith("move:")} == {"move:gate", "move:crypt"}


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


def referee_client(tmp_path, *turns):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    referee = ScriptedReferee(engine, CampaignPaths(campaign), turns=list(turns))
    return TestClient(create_app(engine, referee=referee)), referee


def receive_until_done(ws):
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message["type"] == "referee" and message["event"]["type"] == "done":
            return messages


def test_free_text_echoes_the_player_and_streams_the_narration(tmp_path):
    client, referee = referee_client(tmp_path, [Say("Dust "), Say("drifts.")])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "I look around."})
        messages = receive_until_done(ws)

    assert messages[0] == {"type": "player", "text": "I look around."}
    assert [m["event"]["type"] for m in messages[1:]] == ["text", "text", "done"]
    assert "".join(m["event"].get("text", "") for m in messages[1:]) == "Dust drifts."
    assert referee.turns_seen[0].player_input == "I look around."


def test_an_engine_tool_in_a_turn_also_sends_the_engine_events_and_new_state(tmp_path):
    client, _ = referee_client(tmp_path, [Say("You go."), Call("mcp__engine__move", {"to": "hall"})])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "I walk east."})
        messages = receive_until_done(ws)

    kinds = [m["event"]["type"] if m["type"] == "referee" else m["type"] for m in messages]
    assert kinds == ["player", "text", "tool_start", "tool_result", "events", "done"]
    events = messages[4]
    assert [e["type"] for e in events["events"]] == ["moved", "area_revealed"]
    assert events["state"]["party"]["area"] == "hall"


def test_a_clicked_action_is_narrated_by_the_referee_after_its_events(tmp_path):
    client, referee = referee_client(tmp_path, [Say("The hall is long.")])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        messages = receive_until_done(ws)

    assert messages[0]["type"] == "events"
    assert [m["event"]["type"] for m in messages[1:]] == ["text", "done"]
    assert "Long Hall" in referee.turns_seen[0].player_input


def test_the_referee_stream_reaches_every_open_connection(tmp_path):
    client, _ = referee_client(tmp_path, [Say("Hello.")])
    with client.websocket_connect("/ws") as talker, client.websocket_connect("/ws") as watcher:
        talker.receive_json()
        watcher.receive_json()
        talker.send_json({"type": "say", "text": "Hi."})
        receive_until_done(talker)
        seen = receive_until_done(watcher)

    assert seen[0]["type"] == "player"
    assert seen[1]["event"] == {"type": "text", "text": "Hello."}


def test_free_text_with_no_referee_returns_an_error(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "Hello?"})
        error = ws.receive_json()

    assert error["type"] == "error"
    assert "Referee" in error["message"]


def test_a_referee_that_fails_ends_the_turn_with_an_error(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    class BrokenReferee:
        async def turn(self, player_input):
            yield {"type": "text", "text": "Hm"}
            raise RuntimeError("the CLI went away")

        async def close(self):
            pass

    client = TestClient(create_app(engine, referee=BrokenReferee()))
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "Hello?"})
        messages = receive_until_done(ws)

    assert messages[-1]["event"]["type"] == "done"
    assert "the CLI went away" in messages[-1]["event"]["error"]


# New campaign and Open campaign screens

from harness_fixtures import BUILTIN_PLUGINS  # noqa: E402

from solo_roll.harness.library import Library  # noqa: E402
from solo_roll.rng import ScriptedDice  # noqa: E402

CREATION_ROLLS = [3, 3, 3, 4, 4, 4, 2, 2, 3, 5, 5, 4, 6, 5, 5, 3, 3, 4, 5]


@pytest.fixture
def library_client(tmp_path):
    library = Library(tmp_path / "campaigns", BUILTIN_PLUGINS, dice=lambda: ScriptedDice(list(CREATION_ROLLS)))
    return TestClient(create_app(None, library=library)), library


def test_with_no_campaign_open_a_connection_gets_the_library(library_client):
    client, library = library_client
    library.create("Old Delve", ruleset="ose", generators=[])

    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()

    assert hello["type"] == "library"
    assert hello["plugins"]["ruleset"] == ["ose"]
    assert [c["name"] for c in hello["campaigns"]] == ["Old Delve"]


def test_a_new_campaign_opens_with_an_empty_party_and_a_character_is_made_by_procedure(library_client):
    client, _ = library_client
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "new_campaign", "name": "Delve", "ruleset": "ose", "generators": ["flextale"]})
        opened = ws.receive_json()
        ws.send_json({"type": "act", "command": {
            "type": "procedure", "name": "create_character",
            "inputs": {"class": "Fighter", "character_name": "Brannoc"}}})
        created = ws.receive_json()

    assert opened["type"] == "snapshot"
    assert opened["state"]["party"]["members"] == []
    assert [m["name"] for m in created["state"]["party"]["members"]] == ["Brannoc"]


def test_a_refused_new_campaign_returns_an_error_and_keeps_the_library_open(library_client):
    client, _ = library_client
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "new_campaign", "name": "Bad", "ruleset": "flextale", "generators": []})
        error = ws.receive_json()

    assert error["type"] == "error"


def test_open_campaign_switches_every_connection_and_list_returns_to_the_library(library_client):
    client, library = library_client
    campaign_id = library.create("Delve", ruleset="ose", generators=[])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "open_campaign", "id": campaign_id})
        opened = ws.receive_json()
        ws.send_json({"type": "list_campaigns"})
        listing = ws.receive_json()

    assert opened["type"] == "snapshot"
    assert listing["type"] == "library"


def test_act_with_no_campaign_open_returns_an_error(library_client):
    client, _ = library_client
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "x"}})
        error = ws.receive_json()

    assert error["type"] == "error"
