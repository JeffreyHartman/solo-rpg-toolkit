"""Tests for the Referee's edit tools: `edit` changes a member or a monster, `monster_action` takes a monster's turn.

The dice are scripted; a test that must not roll gets no dice, so any roll fails it.
"""
import asyncio

from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.referee import Call, ScriptedReferee
from solo_roll.rng import ScriptedDice

EDIT = "mcp__engine__edit"


def run_turn(engine, campaign, *steps):
    referee = ScriptedReferee(engine, CampaignPaths(campaign), turns=[list(steps)])

    async def collect():
        return [event async for event in referee.turn("Go on.")]

    return [e for e in asyncio.run(collect()) if e["type"] == "tool_result"]


def burn_out_the_torch(engine):
    for _ in range(6):
        engine.act({"type": "procedure", "name": "rest"})
    assert engine.state()["dungeon"]["light"] == []


def test_the_referee_lights_a_torch_for_a_character_and_the_light_burns(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    burn_out_the_torch(engine)

    [result] = run_turn(engine, campaign, Call(EDIT, {
        "who": "Brannoc", "change": "light", "value": "torch", "reason": "Brannoc found a torch in the sconce."}))

    assert result["ok"], result.get("error")
    assert engine.state()["dungeon"]["light"] == [{"kind": "torch", "bearer": "Brannoc", "turns_left": 6}]
    events = engine.act({"type": "procedure", "name": "rest"})
    assert "darkness" not in [e["type"] for e in events]
    assert engine.state()["dungeon"]["light"][0]["turns_left"] == 5


def test_each_edit_shows_a_mechanics_card_with_what_changed_and_the_reason(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    edits = [
        ("add_item", "rope", "Brannoc gains rope"),
        ("remove_item", "rope", "Brannoc loses rope"),
        ("condition", "poisoned", "Brannoc is poisoned"),
        ("clear_condition", "poisoned", "Brannoc is no longer poisoned"),
        ("hp", "+0", "Brannoc gains 0 HP"),
    ]

    results = run_turn(engine, campaign, *[
        Call(EDIT, {"who": "Brannoc", "change": change, "value": value, "reason": f"Reason {n}."})
        for n, (change, value, _) in enumerate(edits)])

    for n, (result, (_, _, did)) in enumerate(zip(results, edits)):
        assert result["ok"], result.get("error")
        card = result["events"][0]
        assert card["type"] == "mechanics"
        assert (card["result"], card["reason"], card["source"]) == (did, f"Reason {n}.", "Referee edit")
        assert f"Reason {n}." in card["text"]
    assert engine.state()["party"]["members"][0].get("items") == []


def test_an_edit_with_no_reason_is_refused_and_changes_nothing(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    [result] = run_turn(engine, campaign, Call(EDIT, {"who": "Brannoc", "change": "add_item", "value": "rope", "reason": " "}))

    assert result["ok"] is False
    assert "items" not in engine.state()["party"]["members"][0]


def test_an_hp_change_in_dice_is_rolled_with_the_engine_dice(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign, ScriptedDice([4]))
    engine.act({"type": "edit", "who": "Brannoc", "change": "hp", "value": "+10", "reason": "Healed at the shrine."})

    [result] = run_turn(engine, campaign, Call(EDIT, {
        "who": "Brannoc", "change": "hp", "value": "-1d6", "reason": "The ceiling falls on him."}))

    card = result["events"][0]
    assert (card["dice"], card["rolls"], card["total"]) == ("1d6", [4], 4)
    assert engine.state()["party"]["members"][0]["hp"] == 6
