"""Tests for the `propose` engine tool, driven through `ScriptedReferee`."""
import asyncio

from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.referee import Call, ScriptedReferee
from solo_roll.rng import ScriptedDice

FORCE_DOOR = {
    "procedure": "ability_check",
    "inputs": {"member": "Brannoc", "ability": "STR", "target": 12},
    "reason": "Brannoc forces the stuck door.",
}


def run_turn(engine, campaign, *steps):
    referee = ScriptedReferee(engine, CampaignPaths(campaign), turns=[list(steps)])

    async def collect():
        return [event async for event in referee.turn("I force the door.")]

    return asyncio.run(collect())


def test_proposing_a_confirm_procedure_leaves_a_proposal_for_the_player(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign, ScriptedDice([]))

    start, result, _ = run_turn(engine, campaign, Call("mcp__engine__propose", FORCE_DOOR))

    assert start["label"] == "Proposing Ability check"
    assert result["ok"] is True
    assert [e["type"] for e in result["events"]] == ["proposal"]
    assert result["output"]["status"] == "waiting for the player"
    assert result["output"]["proposal"]["id"] == engine.state()["proposals"]["pending"][0]["id"]


def test_proposing_an_auto_procedure_runs_it_and_returns_its_card(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign, ScriptedDice([1]))
    search = {"procedure": "search", "inputs": {}, "reason": "Brannoc checks the walls."}

    _, result, _ = run_turn(engine, campaign, Call("mcp__engine__propose", search))

    assert result["output"]["status"] == "ran"
    assert result["events"][0]["type"] == "mechanics"
    assert result["output"]["events"] == result["events"]


def test_a_proposal_with_a_bad_input_is_a_failed_tool_result(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign, ScriptedDice([]))
    bad = {**FORCE_DOOR, "inputs": {"member": "Brannoc", "ability": "LUCK", "target": 12}}

    _, result, _ = run_turn(engine, campaign, Call("mcp__engine__propose", bad))

    assert result["ok"] is False
    assert "ability" in result["error"]
    assert engine.state()["proposals"]["pending"] == []


def test_the_state_tool_lists_the_procedures_the_referee_can_propose(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    _, result, _ = run_turn(engine, campaign, Call("mcp__engine__state", {}))

    check = next(p for p in result["output"]["procedures"] if p["name"] == "ability_check")
    assert check["confirm"] == "confirm"
    assert check["target"] is True
    assert check["inputs"]["ability"]["choices"] == ["STR", "INT", "WIS", "DEX", "CON", "CHA"]
