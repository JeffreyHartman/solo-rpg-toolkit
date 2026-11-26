"""Tests for the Referee's edit tools: `edit` changes a member or a monster, `monster_action` takes a monster's turn.

The dice are scripted; a test that must not roll gets no dice, so any roll fails it.
"""
import asyncio

from harness_fixtures import HAND_MADE_MAP, make_campaign, open_engine

from solo_roll import OSE_DATA_DIR
from solo_roll.harness.campaign import CampaignPaths, create_campaign, load_json, write_json
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.plugins.ose import OsePlugin
from solo_roll.harness.referee import Call, ScriptedReferee
from solo_roll.harness.referee.tools import RefereeTools
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


MONSTER_ACTION = "mcp__engine__monster_action"
BRANNOC = {"name": "Brannoc", "class": "Fighter", "level": 1, "hp": 6, "max_hp": 6, "ac": 5,
           "abilities": {"STR": 14}, "saves": {}}
GOBLIN = {"id": "m1", "name": "goblin", "hp": 4, "max_hp": 4, "ac": 6, "thac0": 19, "damage": "1d6",
          "status": "alive", "generic": False}
MONSTERS_FIRST = [2, 5]
PARTY_FIRST = [5, 2]


def ose_fight(tmp_path, rolls, rules=()):
    """An OSE campaign with no FlexTale, in a fight with one goblin, after an initiative roll."""
    root = create_campaign(tmp_path / "campaign", ["ose"], HAND_MADE_MAP, "gate", [dict(BRANNOC)],
                           settings={"ose": {rule: "on" for rule in rules}})
    paths = CampaignPaths(root)
    state = load_json(paths.state)
    state["combat"] = {"area": "gate", "outcome": None, "round": 0, "phase": "party", "first": "party",
                       "acted": [], "monsters": [dict(GOBLIN)]}
    write_json(paths.state, state)
    factories = {"ose": lambda: OsePlugin(OSE_DATA_DIR, wandering=None)}
    engine = open_campaign(root, ScriptedDice(rolls), factories)
    events = engine.act({"type": "procedure", "name": "initiative"})
    return root, engine, events


def test_with_no_monster_turn_trigger_the_engine_waits_for_the_referee_to_act(tmp_path):
    _, engine, events = ose_fight(tmp_path, MONSTERS_FIRST)

    [turn] = [e for e in events if e["type"] == "monster_turn"]
    assert turn["referee"] is True and "Referee" in turn["text"]
    assert "monsters_done" not in [e["type"] for e in events]
    assert engine.state()["combat"]["waiting"] == ["m1"]


def test_the_referee_attacks_for_the_monster_and_the_engine_rolls_the_attack(tmp_path):
    # d20 15 against THAC0 19 vs AC 5 (needs 14) hits; 1d6 damage 3. The party acts second.
    campaign, engine, _ = ose_fight(tmp_path, MONSTERS_FIRST + [15, 3])

    [result] = run_turn(engine, campaign, Call(MONSTER_ACTION, {
        "monster": "m1", "kind": "attack", "action": "stabs", "target": "Brannoc",
        "reason": "Cornered, the goblin fights."}))

    assert result["ok"], result.get("error")
    cards = [e for e in result["events"] if e["type"] == "mechanics"]
    assert cards[0]["reason"] == "Cornered, the goblin fights." and cards[0]["source"] == "Referee edit"
    attack = next(c for c in cards if c["procedure"] == "monster_attack")
    assert (attack["rolls"], attack["result"]) == ([15], "Hit")
    assert engine.state()["party"]["members"][0]["hp"] == 3
    combat = engine.state()["combat"]
    assert (combat["round"], combat["phase"], combat["waiting"]) == (1, "party", [])


def test_a_referee_driven_attack_uses_ascending_ac(tmp_path):
    campaign, engine, _ = ose_fight(tmp_path, MONSTERS_FIRST + [1], rules=["ascending_ac"])

    [result] = run_turn(engine, campaign, Call(MONSTER_ACTION, {
        "monster": "m1", "kind": "attack", "action": "stabs", "target": "Brannoc", "reason": "It attacks."}))

    attack = next(e for e in result["events"] if e.get("procedure") == "monster_attack")
    assert "ascending AC" in attack["target"]["source"]


def test_a_monster_takes_an_obvious_action_with_no_procedure_and_no_roll(tmp_path):
    campaign, engine, _ = ose_fight(tmp_path, MONSTERS_FIRST)

    [result] = run_turn(engine, campaign, Call(MONSTER_ACTION, {
        "monster": "m1", "kind": "flee", "action": "runs for the door", "target": "",
        "reason": "Its friends are dead and it is terrified."}))

    assert result["ok"], result.get("error")
    card = result["events"][0]
    assert (card["type"], card["dice"], card["rolls"]) == ("mechanics", "", [])
    assert card["reason"] == "Its friends are dead and it is terrified."
    assert "monster_fled" in [e["type"] for e in result["events"]]
    assert engine.state()["combat"] is None


def test_the_referee_cannot_act_for_a_monster_that_is_not_waiting(tmp_path):
    campaign, engine, _ = ose_fight(tmp_path, PARTY_FIRST)

    [result] = run_turn(engine, campaign, Call(MONSTER_ACTION, {
        "monster": "m1", "kind": "flee", "action": "runs", "target": "", "reason": "Scared."}))

    assert result["ok"] is False
    assert engine.state()["combat"]["monsters"][0]["status"] == "alive"


def test_the_referee_has_no_tool_that_rolls_or_takes_a_die_result(tmp_path):
    campaign, engine, _ = ose_fight(tmp_path, MONSTERS_FIRST + [2])
    tools = RefereeTools(engine, CampaignPaths(campaign))

    assert not [name for name in tools.engine_tools if "roll" in name or "dice" in name]
    [result] = run_turn(engine, campaign, Call(MONSTER_ACTION, {
        "monster": "m1", "kind": "attack", "action": "stabs", "target": "Brannoc", "reason": "It attacks.",
        "roll": 20, "rolls": [20]}))
    attack = next(e for e in result["events"] if e.get("procedure") == "monster_attack")
    assert (attack["rolls"], attack["result"]) == ([2], "Miss")


def test_an_hp_edit_that_takes_a_waiting_monster_to_zero_kills_it_and_ends_the_fight(tmp_path):
    campaign, engine, _ = ose_fight(tmp_path, MONSTERS_FIRST)

    [result] = run_turn(engine, campaign, Call(EDIT, {
        "who": "m1", "change": "hp", "value": "-4", "reason": "The rotten floor gives way under it."}))

    assert [e["type"] for e in result["events"]][-3:] == ["hp_changed", "monster_down", "combat_ended"]
    assert engine.state()["combat"] is None


def test_the_referee_guide_gives_the_rule_for_when_to_roll(tmp_path):
    from solo_roll.harness.referee.sdk import system_prompt

    prompt = system_prompt(open_engine(make_campaign(tmp_path)).referee_guides(), CampaignPaths(tmp_path / "campaign"))

    assert "outcome is obvious" in prompt and "outcome is uncertain" in prompt
    assert "mcp__engine__edit" in prompt and "mcp__engine__monster_action" in prompt
    assert "the player's own choices" in prompt
