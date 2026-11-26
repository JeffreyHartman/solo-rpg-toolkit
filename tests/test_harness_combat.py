"""Tests for narrative combat: a combat encounter starts a fight that runs through engine procedures.

Every table here is a small fake written in `tmp_path`; the dice are scripted.
"""
import json

import pytest

from flextale_fakes import DEFAULT_TABLES, MAP, write_tables
from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.errors import FlextaleDataError, IllegalActionError
from solo_roll.harness.plugins.flextale import FlextalePlugin
from solo_roll.harness.plugins.ose import OsePlugin
from solo_roll.rng import ScriptedDice

BESTIARY = {
    "goblin": {"hd": 1, "ac": 6, "thac0": 19, "damage": "1d6"},
    "ogre": {"hd": 4, "ac": 5, "thac0": 16, "damage": "1d10"},
}
AI_ACTION = [(1, 10, "Attack the nearest"), (11, 15, "Maneuver for position"), (16, 19, "Defend"), (20, 20, "Flee")]
AI_TARGET = [(1, 10, "Closest foe"), (11, 20, "Weakest foe")]
TABLES = {**DEFAULT_TABLES, "simple-ai-action": AI_ACTION, "simple-ai-target": AI_TARGET}
BRANNOC = {"name": "Brannoc", "class": "Fighter", "level": 1, "hp": 6, "max_hp": 6, "ac": 5,
           "abilities": {"STR": 14, "DEX": 12}, "saves": {"breath": 15, "death": 12}}

# explore: map d20 (hall), encounter d20 (combat), combat table d20 (goblins).
TO_COMBAT = [1, 16, 1]
# goblin hit points (1d8 each), then initiative d6: party, monsters.
GOBLIN_HP = [4, 3]
PARTY_FIRST = [5, 2]
MONSTERS_FIRST = [2, 5]


def make(tmp_path, rolls, drop=(), party=None, rules=frozenset()):
    data = tmp_path / "data"
    write_tables(data, TABLES, drop)
    (data / "bestiary.json").write_text(json.dumps(BESTIARY))
    root = create_campaign(tmp_path / "campaign", ["ose", "flextale"], MAP, "start", [dict(BRANNOC)] if party is None else party,
                           settings={"ose": {rule: "on" for rule in rules}})
    factories = {"ose": lambda: OsePlugin(data_dir=data, wandering=None), "flextale": lambda: FlextalePlugin(data)}
    return open_campaign(root, ScriptedDice(rolls), factories)


def start(tmp_path, tail, drop=(), party=None, rules=frozenset()):
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + tail, drop=drop, party=party, rules=rules)
    events = engine.act({"type": "explore", "exit": "e1"})
    return engine, events


def attack(engine, target="m1", member="Brannoc"):
    return engine.act({"type": "procedure", "name": "attack", "inputs": {"member": member, "monster": target}})


def types(events):
    return [e["type"] for e in events]


def test_a_combat_encounter_starts_a_fight_with_monsters_from_the_bestiary(tmp_path):
    engine, events = start(tmp_path, PARTY_FIRST)
    combat = engine.state()["combat"]
    assert combat["round"] == 1 and combat["phase"] == "party"
    assert [(m["id"], m["name"], m["hp"], m["ac"], m["status"]) for m in combat["monsters"]] == [
        ("m1", "goblin", 4, 6, "alive"), ("m2", "goblin", 3, 6, "alive")]
    assert {"combat_started", "phase_changed"} <= set(types(events))
    initiative = next(e for e in events if e.get("procedure") == "initiative")
    assert initiative["rolls"] == [5, 2]
    assert engine.state()["encounter"]["current"]["outcomes"][0]["status"] == "started"


def test_an_unlisted_monster_gets_a_generic_stat_block(tmp_path):
    tables = {**TABLES, "combat-encounter-a": [(1, 20, "A fake wisp")]}
    data = tmp_path / "data"
    write_tables(data, tables)
    root = create_campaign(tmp_path / "c", ["ose", "flextale"], MAP, "start", [dict(BRANNOC)])
    factories = {"ose": lambda: OsePlugin(data_dir=data, wandering=None), "flextale": lambda: FlextalePlugin(data)}
    engine = open_campaign(root, ScriptedDice(TO_COMBAT + [4] + PARTY_FIRST), factories)
    engine.act({"type": "explore", "exit": "e1"})
    [monster] = engine.state()["combat"]["monsters"]
    assert (monster["name"], monster["ac"], monster["damage"], monster["generic"]) == ("fake wisp", 9, "1d6", True)


def test_a_full_fight_runs_to_victory_through_the_engine(tmp_path):
    tail = PARTY_FIRST + [
        15, 4,        # attack m1: needs 13, rolls 15, damage 4+1 kills the 4 hp goblin
        1, 1, 10,     # m2 acts: attack, closest foe, rolls 10 against need 14: miss
        5, 2,         # round 2 initiative: party first
        18, 2,        # attack m2: needs 13, rolls 18, damage 2+1 kills the 3 hp goblin
    ]
    engine, _ = start(tmp_path, tail)
    first = attack(engine)
    assert types(first).count("mechanics") == 6  # attack, damage, ai action, ai target, goblin attack, initiative
    assert engine.state()["combat"]["monsters"][0]["status"] == "dead"
    assert engine.state()["combat"]["round"] == 2
    last = attack(engine, "m2")
    assert "combat_ended" in types(last)
    state = engine.state()
    assert state["combat"] is None
    assert state["encounter"]["current"]["outcomes"][0]["status"] == "resolved"
    assert state["party"]["members"][0]["hp"] == 6
    assert any(e["type"] == "combat_ended" and e["result"] == "victory" for e in last)


def test_the_attack_target_number_comes_from_thac0_and_armor_class(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [15, 4, 1, 1, 10, 5, 2])
    card = next(e for e in attack(engine) if e.get("procedure") == "attack")
    assert card["target"]["value"] == 13
    assert "AC 6" in card["target"]["source"]
    assert card["result"] == "Hit"


def test_a_miss_does_no_damage(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [11, 1, 1, 10, 1, 1, 10, 5, 2])
    events = attack(engine)
    assert engine.state()["combat"]["monsters"][0]["hp"] == 4
    assert not any(e["type"] == "damage" and e["target"] == "m1" for e in events)


def test_monsters_that_win_initiative_act_first_and_hurt_through_the_engine(tmp_path):
    tail = MONSTERS_FIRST + [
        1, 1, 15, 4,   # m1: attack, closest, rolls 15 against need 14: hits for 4
        1, 1, 3,       # m2: attack, closest, misses
    ]
    engine, events = start(tmp_path, tail)
    state = engine.state()
    assert state["party"]["members"][0]["hp"] == 2
    assert state["combat"]["phase"] == "party"
    assert any(e["type"] == "damage" and e["target"] == "Brannoc" and e["hp"] == 2 for e in events)


def test_the_party_loses_when_every_member_is_down(tmp_path):
    party = [{**BRANNOC, "hp": 3, "max_hp": 6}]
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + MONSTERS_FIRST + [1, 1, 20, 6], party=party)
    events = engine.act({"type": "explore", "exit": "e1"})
    state = engine.state()
    assert state["party"]["members"][0]["hp"] == 0
    assert state["combat"] is None
    assert any(e["type"] == "combat_ended" and e["result"] == "defeat" for e in events)


def test_a_monster_that_flees_leaves_the_fight_and_the_last_one_ends_it(tmp_path):
    tail = MONSTERS_FIRST + [20, 20]  # both goblins roll Flee
    engine, events = start(tmp_path, tail)
    assert engine.state()["combat"] is None
    assert any(e["type"] == "combat_ended" and e["result"] == "victory" for e in events)


def test_a_non_attack_action_changes_nothing_but_is_reported(tmp_path):
    engine, events = start(tmp_path, MONSTERS_FIRST + [12, 17, 5, 2])
    acts = [e for e in events if e["type"] == "monster_acted"]
    assert [a["action"] for a in acts] == ["Maneuver for position", "Defend"]
    assert engine.state()["party"]["members"][0]["hp"] == 6


def test_a_missing_ai_target_table_raises_the_typed_error_and_changes_nothing(tmp_path):
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + MONSTERS_FIRST + [1], drop=("simple-ai-target",))
    # The explore command itself fails: the fight cannot start without the table.
    before = engine.state()
    with pytest.raises(FlextaleDataError, match="simple-ai-target"):
        engine.act({"type": "explore", "exit": "e1"})
    assert engine.state() == before


def test_available_actions_list_attacks_in_the_party_phase_only(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [11, 1, 1, 10, 1, 1, 10, 5, 2])
    labels = [a["label"] for a in engine.available_actions() if a["command"].get("name") == "attack"]
    assert labels == ["Brannoc attacks goblin m1 (4 HP)", "Brannoc attacks goblin m2 (3 HP)"]


def test_an_attack_outside_the_party_phase_or_on_a_dead_monster_is_refused(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [15, 4, 1, 1, 10, 5, 2])
    attack(engine)
    with pytest.raises(IllegalActionError, match="dead"):
        attack(engine, "m1")
    with pytest.raises(IllegalActionError, match="no monster"):
        attack(engine, "m9")


def test_a_special_action_uses_the_members_turn(tmp_path):
    engine, events = start(tmp_path, PARTY_FIRST + [1, 1, 10, 1, 1, 10, 5, 2])
    result = engine.act({"type": "procedure", "name": "special_action",
                         "inputs": {"member": "Brannoc", "description": "Kicks over the brazier"}})
    assert any(e["type"] == "special_action" for e in result)
    assert engine.state()["combat"]["round"] == 2


def test_movement_is_refused_during_combat(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST)
    with pytest.raises(IllegalActionError, match="combat"):
        engine.act({"type": "move", "to": "start"})


def test_the_referee_proposal_of_an_attack_waits_for_the_player(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [15, 4, 1, 1, 10, 5, 2])
    proposed = engine.act({"type": "propose", "procedure": "attack", "reason": "He lunges",
                           "inputs": {"member": "Brannoc", "monster": "m1"}})
    assert types(proposed) == ["proposal"]
    assert engine.state()["combat"]["monsters"][0]["hp"] == 4
    engine.act({"type": "answer_proposal", "id": "p1", "answer": "confirm"})
    assert engine.state()["combat"]["monsters"][0]["hp"] == 0


def test_a_monster_ai_procedure_runs_as_auto(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST)
    levels = {p["name"]: p["confirm"] for p in engine.procedures()}
    assert levels["simple_ai"] == "auto"
    assert levels["initiative"] == "auto"
    assert levels["attack"] == "confirm"


def test_a_defeat_logs_combat_ended_after_the_monsters_act_and_nothing_after_it(tmp_path):
    party = [{**BRANNOC, "hp": 3, "max_hp": 6}]
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + MONSTERS_FIRST + [1, 1, 20, 6], party=party)
    events = engine.act({"type": "explore", "exit": "e1"})
    ended = next(i for i, e in enumerate(events) if e["type"] == "combat_ended")
    assert not any(e["type"] == "phase_changed" for e in events[ended:])


def test_a_fight_with_no_standing_member_is_refused_and_changes_nothing(tmp_path):
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + MONSTERS_FIRST + [1, 1], party=[])
    before = engine.state()
    with pytest.raises(IllegalActionError, match="standing"):
        engine.act({"type": "explore", "exit": "e1"})
    assert engine.state() == before


def test_exploring_takes_a_dungeon_turn(tmp_path):
    engine, events = start(tmp_path, PARTY_FIRST)
    assert "turn" in types(events)
    assert engine.state()["dungeon"]["turn"] == 1


def test_a_monster_attack_uses_the_targets_armor_class_and_names_it(tmp_path):
    party = [{**BRANNOC, "ac": 3}]
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + MONSTERS_FIRST + [1, 1, 20, 1, 1, 1, 3], party=party)
    events = engine.act({"type": "explore", "exit": "e1"})
    card = next(e for e in events if e.get("procedure") == "monster_attack")
    assert card["target"]["value"] == 16
    assert "Brannoc's AC 3" in card["target"]["source"]


ASCENDING = frozenset({"ascending_ac"})
VARIABLE = frozenset({"variable_weapon_damage"})
# Goblin AC 6 is ascending AC 13; a level 1 attacker has attack bonus +0 and STR 14 adds 1.


def test_ascending_ac_hits_at_the_ascending_target_and_names_the_rule(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [12, 4, 1, 1, 10, 5, 2], rules=ASCENDING)
    card = next(e for e in attack(engine) if e.get("procedure") == "attack")
    assert card["target"]["value"] == 13
    assert card["result"] == "Hit"
    assert card["total"] == 13
    assert "ascending AC 13" in card["target"]["source"]
    assert "attack bonus +0" in card["target"]["source"]
    assert "ascending AC" in card["source"]


def test_ascending_ac_misses_one_below_the_target(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [11, 1, 1, 10, 1, 1, 10, 5, 2], rules=ASCENDING)
    card = next(e for e in attack(engine) if e.get("procedure") == "attack")
    assert card["result"] == "Miss"
    assert card["total"] == 12


def test_ascending_attack_bonus_comes_from_thac0(tmp_path):
    party = [{**BRANNOC, "thac0": 17}]
    engine, _ = start(tmp_path, PARTY_FIRST + [10, 4, 1, 1, 10, 5, 2], party=party, rules=ASCENDING)
    card = next(e for e in attack(engine) if e.get("procedure") == "attack")
    assert card["total"] == 13
    assert card["result"] == "Hit"
    assert "attack bonus +2" in card["target"]["source"]


def test_a_monster_attack_uses_the_ascending_ac_of_the_target(tmp_path):
    party = [{**BRANNOC, "ac": 3}]
    engine = make(tmp_path, TO_COMBAT + GOBLIN_HP + MONSTERS_FIRST + [1, 1, 16, 1, 1, 1, 3], party=party, rules=ASCENDING)
    events = engine.act({"type": "explore", "exit": "e1"})
    card = next(e for e in events if e.get("procedure") == "monster_attack")
    assert card["target"]["value"] == 16
    assert "ascending AC 16" in card["target"]["source"]
    assert "ascending AC" in card["source"]
    assert card["result"] == "Hit"


def test_a_weapon_die_is_rolled_with_variable_weapon_damage(tmp_path):
    party = [{**BRANNOC, "weapon": {"name": "sword", "damage": "1d8"}}]
    engine, _ = start(tmp_path, PARTY_FIRST + [15, 8, 1, 1, 10, 5, 2], party=party, rules=VARIABLE)
    events = attack(engine)
    card = next(e for e in events if e.get("procedure") == "damage")
    assert card["dice"] == "1d8"
    assert card["rolls"] == [8]
    assert "default" not in card["text"]


def test_no_weapon_data_rolls_the_default_die_and_the_card_says_so(tmp_path):
    engine, _ = start(tmp_path, PARTY_FIRST + [15, 4, 1, 1, 10, 5, 2], rules=VARIABLE)
    card = next(e for e in attack(engine) if e.get("procedure") == "damage")
    assert card["dice"] == "1d6"
    assert "default" in card["text"]


def test_without_the_rule_a_weapon_die_is_ignored(tmp_path):
    party = [{**BRANNOC, "weapon": {"name": "sword", "damage": "1d8"}}]
    engine, _ = start(tmp_path, PARTY_FIRST + [15, 4, 1, 1, 10, 5, 2], party=party)
    card = next(e for e in attack(engine) if e.get("procedure") == "damage")
    assert card["dice"] == "1d6"
