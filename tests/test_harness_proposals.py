"""Tests for proposals, target numbers and confirm levels through `Engine.act`."""
from harness_fixtures import make_campaign, open_engine

from solo_roll.rng import ScriptedDice


def propose(engine, procedure, inputs, reason="The player tries it."):
    return engine.act({"type": "propose", "procedure": procedure, "inputs": inputs, "reason": reason})


def test_a_proposed_confirm_procedure_waits_as_a_proposal_card_and_rolls_nothing(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([]))

    events = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12},
                     reason="Brannoc forces the door.")

    assert [e["type"] for e in events] == ["proposal"]
    card = events[0]["proposal"]
    assert card["procedure"] == "ability_check"
    assert card["inputs"] == {"member": "Brannoc", "ability": "STR", "modifier": 0}
    assert card["target"] == {"value": 12, "source": "proposal input, set by the Referee", "editable": True}
    assert card["reason"] == "Brannoc forces the door."
    assert events[0]["text"]
    assert engine.state()["proposals"]["pending"] == [card]
