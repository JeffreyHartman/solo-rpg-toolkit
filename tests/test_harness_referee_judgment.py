"""Tests for the `judgment_call` engine tool and the judgment messages of the server."""
import asyncio

import pytest
from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.referee import Call, Say, ScriptedReferee

ARGS = {
    "category": "ruling",
    "question": "Does the rope hold the whole party?",
    "suggestion": "yes",
    "reason": "The rope is new and the party is small.",
}


def run_turn(engine, campaign, *steps):
    referee = ScriptedReferee(engine, CampaignPaths(campaign), turns=[list(steps)])

    async def collect():
        return [event async for event in referee.turn("We climb.")]

    return asyncio.run(collect())


def test_the_referee_tool_leaves_a_card_for_the_player_when_the_player_owns_the_category(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    start, result, _ = run_turn(engine, campaign, Call("mcp__engine__judgment_call", ARGS))

    assert start["label"] == "Raising a judgment call"
    assert result["output"]["status"] == "waiting for the player"
    assert [e["type"] for e in result["events"]] == ["judgment_call"]
    assert engine.state()["judgments"]["pending"][0]["suggestion"] == "yes"


def test_the_referee_tool_reports_its_logged_decision_when_the_referee_owns_the_category(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    engine.change_setting("judgment", "ruling", "referee")

    _, result, _ = run_turn(engine, campaign, Call("mcp__engine__judgment_call", ARGS))

    assert result["output"] == {"status": "decided", "answer": "yes", "reason": ARGS["reason"]}
    assert engine.state()["judgments"]["pending"] == []


def test_an_unknown_category_is_a_failed_tool_result_and_the_state_tool_lists_the_known_ones(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    _, bad, _, state, _ = run_turn(
        engine,
        campaign,
        Call("mcp__engine__judgment_call", {**ARGS, "category": "x"}),
        Call("mcp__engine__state", {}),
    )

    assert bad["ok"] is False
    assert state["output"]["judgment_categories"][0]["category"] == "ruling"
    assert state["output"]["judgment_categories"][0]["owner"] == "ask"


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from solo_roll.harness.server import create_app  # noqa: E402


def receive_until_done(ws):
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message["type"] == "referee" and message["event"]["type"] == "done":
            return messages


def test_a_judgment_answer_reaches_the_engine_and_is_narrated_and_an_owner_change_is_broadcast(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    referee = ScriptedReferee(
        engine,
        CampaignPaths(campaign),
        turns=[[Call("mcp__engine__judgment_call", ARGS)], [Say("The rope holds.")]],
    )
    client = TestClient(create_app(engine, referee=referee))
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["settings"]["judgment"][0]["owner"] == "ask"
        ws.send_json({"type": "say", "text": "We climb."})
        receive_until_done(ws)
        card = engine.state()["judgments"]["pending"][0]

        ws.send_json({"type": "answer_judgment", "id": card["id"], "answer": "yes"})
        messages = receive_until_done(ws)
        assert any(m["type"] == "events" and m["events"][0]["type"] == "judgment_answered" for m in messages)

        ws.send_json({"type": "set_setting", "section": "judgment", "key": "ruling", "value": "referee"})
        changed = ws.receive_json()
        assert changed["settings"]["judgment"][0]["owner"] == "referee"
