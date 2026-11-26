"""Tests for the OSE `create_character` procedure through `Engine.act`."""
import pytest
from harness_fixtures import HAND_MADE_MAP, open_engine

from solo_roll.character import CLASS_HIT_DICE
from solo_roll.harness.campaign import CampaignPaths, create_campaign
from solo_roll.harness.errors import IllegalActionError
from solo_roll.rng import ScriptedDice

# STR 9, INT 12, WIS 7, DEX 14, CON 16, CHA 10: three dice each, then the d8 hit die.
FIGHTER_ROLLS = [3, 3, 3, 4, 4, 4, 2, 2, 3, 5, 5, 4, 6, 5, 5, 3, 3, 4, 5]


def empty_party_campaign(tmp_path):
    return create_campaign(
        tmp_path / "campaign", plugins=["ose"], map_data=HAND_MADE_MAP, start="gate", party=[]
    )


def create(name="Brannoc", character_class="Fighter", **extra):
    return {"type": "procedure", "name": "create_character",
            "inputs": {"class": character_class, "character_name": name, **extra}}


def test_creating_a_character_rolls_3d6_in_order_and_adds_a_party_member(tmp_path):
    engine = open_engine(empty_party_campaign(tmp_path), ScriptedDice(FIGHTER_ROLLS))

    events = engine.act(create(description="A scarred gate guard."))

    (member,) = engine.state()["party"]["members"]
    assert member["name"] == "Brannoc"
    assert member["class"] == "Fighter"
    assert member["description"] == "A scarred gate guard."
    assert member["abilities"] == {"STR": 9, "INT": 12, "WIS": 7, "DEX": 14, "CON": 16, "CHA": 10}
    assert member["max_hp"] == member["hp"] == 7  # d8 roll 5 + CON modifier 2
    assert [e["type"] for e in events] == ["mechanics", "character_created"]


def test_the_new_character_has_a_note_with_a_mechanical_block(tmp_path):
    root = empty_party_campaign(tmp_path)
    engine = open_engine(root, ScriptedDice(FIGHTER_ROLLS))

    engine.act(create())

    note = (CampaignPaths(root).vault / "Characters" / "Brannoc.md").read_text()
    assert "Class: Fighter" in note


@pytest.mark.parametrize("bad", [{"character_name": "  "}, {"class": "Wizard"}])
def test_a_nameless_character_or_unknown_class_is_refused_with_no_dice_used(tmp_path, bad):
    engine = open_engine(empty_party_campaign(tmp_path), ScriptedDice([]))

    with pytest.raises(IllegalActionError):
        engine.act(create() | {"inputs": create()["inputs"] | bad})

    assert engine.state()["party"]["members"] == []


def test_a_class_whose_requirements_the_rolls_miss_is_refused_and_the_party_is_unchanged(tmp_path):
    low_int = [3, 3, 3, 1, 1, 1, *FIGHTER_ROLLS[6:]]  # INT 3, below the Elf minimum of 9
    engine = open_engine(empty_party_campaign(tmp_path), ScriptedDice(low_int))

    with pytest.raises(IllegalActionError, match="INT"):
        engine.act(create(character_class="Elf"))

    assert engine.state()["party"]["members"] == []


def test_the_first_character_carries_the_unclaimed_torch(tmp_path):
    engine = open_engine(empty_party_campaign(tmp_path), ScriptedDice(FIGHTER_ROLLS))

    engine.act(create())

    assert engine.state()["dungeon"]["light"][0]["bearer"] == "Brannoc"


def test_the_referee_can_create_the_character_the_player_agreed_on(tmp_path):
    import asyncio

    from solo_roll.harness.referee import Call, ScriptedReferee

    root = empty_party_campaign(tmp_path)
    engine = open_engine(root, ScriptedDice(FIGHTER_ROLLS))
    args = {"class": "Fighter", "character_name": "Brannoc", "description": "A scarred gate guard."}
    referee = ScriptedReferee(engine, CampaignPaths(root), turns=[[Call("mcp__engine__create_character", args)]])

    async def run():
        return [e async for e in referee.turn("Brannoc it is.")]

    result = next(e for e in asyncio.run(run()) if e["type"] == "tool_result")

    assert result["ok"]
    assert engine.state()["party"]["members"][0]["description"] == "A scarred gate guard."


def test_a_new_character_stores_class_saves_and_unarmored_armor_class(tmp_path):
    engine = open_engine(empty_party_campaign(tmp_path), ScriptedDice(FIGHTER_ROLLS))

    engine.act(create())

    (member,) = engine.state()["party"]["members"]
    assert member["saves"] == {"death": 12, "wands": 13, "paralysis": 14, "breath": 15, "spells": 16}
    assert member["ac"] == 9


def test_every_class_has_all_five_saves():
    from solo_roll.character import CLASS_SAVES, SAVES

    assert set(CLASS_SAVES) == set(CLASS_HIT_DICE)
    assert all(tuple(row) == SAVES for row in CLASS_SAVES.values())
