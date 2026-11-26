"""Tests for proposals, target numbers and confirm levels through `Engine.act`."""
import pytest
from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.errors import IllegalActionError

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


def answer(engine, proposal_id, reply, inputs=None):
    command = {"type": "answer_proposal", "id": proposal_id, "answer": reply}
    if inputs is not None:
        command["inputs"] = inputs
    return engine.act(command)


def test_confirming_a_proposal_runs_it_and_the_card_names_the_target_source(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([9]))
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})[0]["proposal"]

    events = answer(engine, proposal["id"], "confirm")

    assert [e["type"] for e in events] == ["proposal_answered", "mechanics"]
    card = events[1]
    assert (card["procedure"], card["rolls"], card["total"], card["result"]) == ("ability_check", [9], 9, "Success")
    assert card["target"] == {"value": 12, "source": "proposal input, set by the Referee"}
    assert engine.state()["proposals"]["pending"] == []


def test_a_rejected_proposal_rolls_nothing_and_changes_no_state(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([]))
    before = engine.state()
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})[0]["proposal"]

    events = answer(engine, proposal["id"], "reject")

    assert [(e["type"], e["answer"]) for e in events] == [("proposal_answered", "reject")]
    after = engine.state()
    assert after["proposals"]["pending"] == []
    assert {k: v for k, v in after.items() if k != "proposals"} == {k: v for k, v in before.items() if k != "proposals"}


def test_a_changed_proposal_runs_with_the_players_inputs_and_target(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([11]))
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})[0]["proposal"]

    events = answer(engine, proposal["id"], "change", {"ability": "DEX", "target": 10})

    card = events[1]
    assert card["result"] == "Failure"
    assert card["target"] == {"value": 10, "source": "proposal input, set by the player"}
    assert "DEX" in card["text"]


def test_a_change_that_keeps_the_target_keeps_the_referees_source(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([11]))
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})[0]["proposal"]

    events = answer(engine, proposal["id"], "change", {"modifier": -2})

    assert (events[1]["total"], events[1]["result"]) == (9, "Success")
    assert events[1]["target"]["source"] == "proposal input, set by the Referee"


def test_a_change_with_a_bad_input_is_refused_and_the_proposal_stays_pending(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([]))
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})[0]["proposal"]

    with pytest.raises(IllegalActionError):
        answer(engine, proposal["id"], "change", {"ability": "LUCK"})

    assert engine.state()["proposals"]["pending"] == [proposal]


def test_a_change_that_sends_the_same_target_back_keeps_the_referees_source(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([11]))
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})[0]["proposal"]

    events = answer(engine, proposal["id"], "change", {"ability": "DEX", "target": "12"})

    assert events[1]["target"] == {"value": 12, "source": "proposal input, set by the Referee"}
