"""Tests for the proposal and campaign settings messages of `harness.server.create_app`."""
import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from harness_fixtures import make_campaign, open_engine  # noqa: E402

from solo_roll.harness.campaign import CampaignPaths  # noqa: E402
from solo_roll.harness.referee import Call, Say, ScriptedReferee  # noqa: E402
from solo_roll.harness.server import create_app  # noqa: E402
from solo_roll.rng import ScriptedDice  # noqa: E402

FORCE_DOOR = {
    "procedure": "ability_check",
    "inputs": {"member": "Brannoc", "ability": "STR", "target": 12},
    "reason": "Brannoc forces the stuck door.",
}


def receive_until_done(ws):
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message["type"] == "referee" and message["event"]["type"] == "done":
            return messages


def test_the_snapshot_carries_the_campaign_settings(tmp_path):
    client = TestClient(create_app(open_engine(make_campaign(tmp_path))))
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()

    levels = {row["procedure"]: row["level"] for row in hello["settings"]["confirm"]}
    assert levels["ability_check"] == "confirm"
    assert levels["search"] == "auto"


def test_a_referee_proposal_reaches_the_player_and_the_answer_is_narrated(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign, ScriptedDice([4]))
    referee = ScriptedReferee(
        engine, CampaignPaths(campaign),
        turns=[[Say("You set your shoulder."), Call("mcp__engine__propose", FORCE_DOOR)], [Say("It gives.")]],
    )
    client = TestClient(create_app(engine, referee=referee))
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "say", "text": "I force the door."})
        proposed = next(m for m in receive_until_done(ws) if m["type"] == "events")
        [pending] = proposed["state"]["proposals"]["pending"]
        ws.send_json({"type": "answer", "id": pending["id"], "answer": "confirm"})
        answered = [m for m in receive_until_done(ws) if m["type"] != "context"]

    assert [e["type"] for e in proposed["events"]] == ["proposal"]
    assert answered[0]["type"] == "events"
    assert [e["type"] for e in answered[0]["events"]] == ["proposal_answered", "mechanics"]
    assert answered[0]["events"][1]["target"]["source"] == "proposal input, set by the Referee"
    assert answered[0]["state"]["proposals"]["pending"] == []
    assert "Success" in referee.turns_seen[1].player_input


def test_an_answer_to_no_pending_proposal_returns_an_error(tmp_path):
    client = TestClient(create_app(open_engine(make_campaign(tmp_path))))
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "answer", "id": "p9", "answer": "confirm"})
        error = ws.receive_json()

    assert error["type"] == "error"
    assert "p9" in error["message"]


def test_a_setting_change_reaches_every_connection_and_persists(tmp_path):
    campaign = make_campaign(tmp_path)
    client = TestClient(create_app(open_engine(campaign)))
    with client.websocket_connect("/ws") as changer, client.websocket_connect("/ws") as watcher:
        changer.receive_json()
        watcher.receive_json()
        changer.send_json({"type": "set_setting", "section": "confirm", "key": "search", "value": "confirm"})
        mine, theirs = changer.receive_json(), watcher.receive_json()

    assert mine == theirs
    assert mine["type"] == "settings"
    assert {r["procedure"]: r["level"] for r in mine["settings"]["confirm"]}["search"] == "confirm"
    assert open_engine(campaign).confirm_level("search") == "confirm"


def test_a_bad_setting_returns_an_error(tmp_path):
    client = TestClient(create_app(open_engine(make_campaign(tmp_path))))
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "set_setting", "section": "confirm", "key": "search", "value": "never"})
        error = ws.receive_json()

    assert error["type"] == "error"
