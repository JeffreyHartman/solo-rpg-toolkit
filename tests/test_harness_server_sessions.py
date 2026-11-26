"""Tests for the session and context messages of `harness.server.create_app`, with `ScriptedReferee`."""
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from harness_fixtures import make_campaign, open_engine  # noqa: E402

from solo_roll.harness.campaign import CampaignPaths  # noqa: E402
from solo_roll.harness.referee import Call, Say, ScriptedReferee  # noqa: E402
from solo_roll.harness.server import create_app  # noqa: E402

NOTE = "Sessions/Session 001 - The Gate.md"


def referee_client(tmp_path, *turns):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    referee = ScriptedReferee(engine, CampaignPaths(campaign), turns=list(turns))
    return TestClient(create_app(engine, referee=referee)), referee, engine


def receive_until(ws, kind):
    messages = []
    while True:
        messages.append(ws.receive_json())
        if messages[-1]["type"] == kind:
            return messages


def test_a_context_reading_follows_each_turn_with_what_the_referee_got(tmp_path):
    client, referee, _ = referee_client(tmp_path, [Say("Dust.")])
    referee.context_tokens = 4200
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "I look around."})
        context = receive_until(ws, "context")[-1]

    assert (context["tokens"], context["over"]) == (4200, False)
    assert context["budget"] == 60000
    assert [p["label"] for p in context["parts"]] == ["Session opening", "State snapshot", "Player input"]


def test_a_reading_over_the_budget_warns_and_play_goes_on(tmp_path):
    client, referee, _ = referee_client(tmp_path, [Say("One.")], [Say("Two.")])
    referee.context_tokens = 90000
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "first"})
        warned = receive_until(ws, "context")[-1]
        ws.send_json({"type": "say", "text": "second"})
        messages = receive_until(ws, "context")

    assert warned["over"] is True
    assert "Two." in [m["event"].get("text") for m in messages if m["type"] == "referee"]
    assert len(referee.turns_seen) == 2


def test_a_new_connection_gets_the_latest_context_reading(tmp_path):
    client, referee, _ = referee_client(tmp_path, [Say("Dust.")])
    referee.context_tokens = 4200
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["context"] is None
        ws.send_json({"type": "say", "text": "I look around."})
        receive_until(ws, "context")
    with client.websocket_connect("/ws") as late:
        hello = late.receive_json()

    assert hello["context"]["tokens"] == 4200


def test_model_and_effort_changes_reach_the_next_turn_in_the_same_conversation(tmp_path):
    client, referee, engine = referee_client(tmp_path, [Say("One.")], [Say("Two.")])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "first"})
        ws.send_json({"type": "set_setting", "section": "referee", "key": "model", "value": "opus"})
        ws.send_json({"type": "set_setting", "section": "referee", "key": "effort", "value": "high"})
        ws.send_json({"type": "say", "text": "second"})
        messages = receive_until(ws, "context")
        messages += receive_until(ws, "context")

    first, second = referee.turns_seen
    assert (first.model, first.effort) == ("sonnet", "low")
    assert (second.model, second.effort) == ("opus", "high")
    assert first.conversation == second.conversation
    settings = [m for m in messages if m["type"] == "settings"][-1]["settings"]
    assert settings["referee"]["model"] == "opus"
    assert engine.settings()["referee"]["effort"] == "high"


def test_a_bad_referee_setting_returns_an_error_and_changes_nothing(tmp_path):
    client, referee, _ = referee_client(tmp_path)
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "set_setting", "section": "referee", "key": "model", "value": "gpt"})
        error = ws.receive_json()

    assert error["type"] == "error"
    assert referee.model == "sonnet"


def test_compact_runs_a_manual_compact_and_sends_the_new_reading(tmp_path):
    client, referee, _ = referee_client(tmp_path)
    referee.context_tokens = 1100
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "compact"})
        context = receive_until(ws, "context")[-1]

    assert referee.compacts == 1
    assert context["tokens"] == 1100


def test_new_session_starts_the_next_session_and_a_new_conversation(tmp_path):
    client, referee, engine = referee_client(tmp_path, [Say("You stand at the gate.")], [Say("Session two.")])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        receive_until(ws, "context")
        ws.send_json({"type": "new_session"})
        messages = receive_until(ws, "session")
        ws.send_json({"type": "say", "text": "Where am I?"})
        receive_until(ws, "context")

    assert messages[-1] == {"type": "session", "session": 2, "note": None}
    assert [e["type"] for e in messages[0]["events"]] == ["session_ended"]
    assert engine.state()["session"] == 2
    opening = referee.turns_seen[-1]
    assert opening.conversation == referee.turns_seen[0].conversation + 1
    assert "Session 2 starts" in opening.prompt and '"area": "hall"' in opening.prompt


def test_end_session_has_the_referee_write_the_clean_note_then_starts_the_next_session(tmp_path):
    write_note = Call("Write", {"file_path": NOTE, "content": "---\ntype: session\nsession: 1\n---\n# The Gate\n"})
    client, referee, engine = referee_client(tmp_path, [Say("The hall.")], [Say("Writing it up."), write_note])
    paths = engine.paths
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        receive_until(ws, "context")
        ws.send_json({"type": "end_session"})
        messages = receive_until(ws, "session")

    request = referee.turns_seen[-1].player_input
    assert "Sessions/Raw/Session 001.md" in request and "Sessions/Session 001 - " in request
    assert "NPCs/" in request and "Locations/" in request
    assert (paths.vault / NOTE).parent == paths.raw_log(1).parent.parent
    assert messages[-1] == {"type": "session", "session": 2, "note": NOTE}
    assert engine.state()["session"] == 2


def test_end_session_without_a_note_keeps_the_session_open(tmp_path):
    client, referee, engine = referee_client(tmp_path, [Say("The hall.")], [Say("I forgot.")])
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "move", "to": "hall"}})
        receive_until(ws, "context")
        ws.send_json({"type": "end_session"})
        error = receive_until(ws, "error")[-1]

    assert "session note" in error["message"]
    assert engine.state()["session"] == 1
    assert referee.turns_seen[-1].conversation == referee.turns_seen[0].conversation


def test_end_session_before_any_play_returns_an_error(tmp_path):
    client, referee, _ = referee_client(tmp_path)
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "end_session"})
        error = ws.receive_json()

    assert error["type"] == "error"
    assert referee.turns_seen == []


def test_session_controls_with_no_referee_return_an_error(tmp_path):
    client = TestClient(create_app(open_engine(make_campaign(tmp_path))))
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "compact"})
        error = ws.receive_json()

    assert error["type"] == "error"


def test_a_budget_change_sends_the_reading_against_the_new_budget(tmp_path):
    client, referee, _ = referee_client(tmp_path, [Say("Dust.")])
    referee.context_tokens = 4200
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "I look around."})
        receive_until(ws, "context")
        ws.send_json({"type": "set_setting", "section": "referee", "key": "budget", "value": 4000})
        context = receive_until(ws, "context")[-1]

    assert (context["tokens"], context["budget"], context["over"]) == (4200, 4000, True)
