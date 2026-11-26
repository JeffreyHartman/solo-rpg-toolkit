"""Tests for the OSE optional rules a campaign declares in its settings, through real campaign loading.

A Library-made OSE campaign uses Ascending Armour Class and Variable Weapon Damage. A campaign with
no declaration uses descending AC and the default damage die.
"""
from harness_fixtures import BUILTIN_PLUGINS, HAND_MADE_MAP

from solo_roll.harness.campaign import CampaignPaths, create_campaign, load_json, write_json
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.library import Library
from solo_roll.rng import ScriptedDice

BRANNOC = {"name": "Brannoc", "class": "Fighter", "level": 1, "hp": 6, "max_hp": 6, "ac": 5,
           "abilities": {"STR": 14}, "saves": {}}
GOBLIN = {"id": "m1", "name": "goblin", "hp": 4, "max_hp": 4, "ac": 6, "thac0": 19, "damage": "1d6",
          "status": "alive", "generic": False}
# Initiative party 5, monsters 2; the attack d20 rolls 12; the damage d6 rolls 4.
ROLLS = [5, 2, 12, 4]


def into_a_fight(root):
    paths = CampaignPaths(root)
    state = load_json(paths.state)
    state["party"]["members"] = [dict(BRANNOC)]
    state["combat"] = {"area": state["party"]["area"], "outcome": None, "round": 0, "phase": "party",
                       "first": "party", "acted": [], "monsters": [dict(GOBLIN)]}
    write_json(paths.state, state)


def attack_cards(engine):
    engine.act({"type": "procedure", "name": "initiative"})
    events = engine.act({"type": "procedure", "name": "attack", "inputs": {"member": "Brannoc", "monster": "m1"}})
    return {e["procedure"]: e for e in events if e["type"] == "mechanics"}


def test_a_new_ose_campaign_uses_ascending_ac_and_variable_weapon_damage(tmp_path):
    library = Library(tmp_path / "campaigns", BUILTIN_PLUGINS, dice=lambda: ScriptedDice(list(ROLLS)))
    campaign_id = library.create("Delve", ruleset="ose", generators=[])
    into_a_fight(library.root / campaign_id)
    engine, _ = library.open(campaign_id)

    cards = attack_cards(engine)

    assert "ascending AC 13" in cards["attack"]["target"]["source"]
    assert "default" in cards["damage"]["text"]


def test_a_campaign_with_no_declaration_uses_descending_ac_and_the_default_die(tmp_path):
    root = create_campaign(tmp_path / "campaign", ["ose"], HAND_MADE_MAP, "gate", [])
    into_a_fight(root)
    engine = open_campaign(root, ScriptedDice(list(ROLLS)), BUILTIN_PLUGINS)

    cards = attack_cards(engine)

    assert cards["attack"]["target"]["source"] == "OSE attack throw: THAC0 19 vs AC 6, STR +1"
    assert cards["attack"]["result"] == "Hit"
    assert cards["damage"]["dice"] == "1d6" and "default" not in cards["damage"]["text"]
