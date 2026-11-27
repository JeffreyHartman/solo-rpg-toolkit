"""Tests for proposals, target numbers and confirm levels through `Engine.act`."""
import pytest
from harness_fixtures import BUILTIN_PLUGINS, HAND_MADE_MAP, make_campaign, open_engine

from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.errors import HarnessError, IllegalActionError
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


def campaign_with_scores(tmp_path):
    member = {"name": "Brannoc", "abilities": {"STR": 14, "DEX": 8}, "saves": {"breath": 15}}
    return create_campaign(tmp_path / "scored", ["ose"], HAND_MADE_MAP, "gate", [member])


def test_a_target_from_character_data_is_not_an_input_and_the_card_names_it(tmp_path):
    engine = open_engine(campaign_with_scores(tmp_path), ScriptedDice([14]))

    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR"})[0]["proposal"]
    card = answer(engine, proposal["id"], "confirm")[1]

    assert proposal["target"] == {"value": 14, "source": "Brannoc's STR score", "editable": False}
    assert (card["result"], card["target"]) == ("Success", {"value": 14, "source": "Brannoc's STR score"})


def test_the_referee_cannot_set_a_target_that_character_data_gives(tmp_path):
    engine = open_engine(campaign_with_scores(tmp_path), ScriptedDice([]))

    with pytest.raises(IllegalActionError, match="Brannoc's STR score"):
        propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 18})

    assert engine.state()["proposals"]["pending"] == []


def test_changing_the_ability_finds_the_new_score(tmp_path):
    engine = open_engine(campaign_with_scores(tmp_path), ScriptedDice([9]))
    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR"})[0]["proposal"]

    card = answer(engine, proposal["id"], "change", {"ability": "DEX"})[1]

    assert (card["result"], card["target"]) == ("Failure", {"value": 8, "source": "Brannoc's DEX score"})


def test_a_proposal_with_no_target_from_data_or_input_is_refused(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([]))

    with pytest.raises(IllegalActionError, match="target"):
        propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR"})


def test_a_saving_throw_succeeds_at_or_over_the_save_from_character_data(tmp_path):
    engine = open_engine(campaign_with_scores(tmp_path), ScriptedDice([13]))
    proposal = propose(engine, "saving_throw", {"member": "Brannoc", "save": "breath", "modifier": 2})[0]["proposal"]

    card = answer(engine, proposal["id"], "confirm")[1]

    assert (card["procedure"], card["total"], card["result"]) == ("saving_throw", 15, "Success")
    assert card["target"] == {"value": 15, "source": "Brannoc's save vs breath"}


@pytest.mark.parametrize("natural, result", [(1, "Success"), (20, "Failure")])
def test_a_natural_1_or_20_decides_an_ability_check(tmp_path, natural, result):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([natural]))
    proposal = propose(engine, "ability_check",
                       {"member": "Brannoc", "ability": "STR", "target": 10, "modifier": 15 if natural == 1 else -15})
    card = answer(engine, proposal[0]["proposal"]["id"], "confirm")[1]

    assert card["result"] == result


def test_a_proposed_auto_procedure_runs_at_once_and_shows_its_card(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([1]))

    events = propose(engine, "search", {}, reason="Brannoc checks the walls.")

    assert [e["type"] for e in events][:2] == ["mechanics", "turn"]
    assert events[0]["procedure"] == "search"
    assert engine.state()["proposals"]["pending"] == []


class FixedDcPlugin:
    """A generator that gives ability checks a target number from its own data."""

    name = "dcs"
    kind = "generator"

    def register(self, registry):
        registry.add_target_source("ability_check", lambda state, inputs, ctx: {"value": 11, "source": "DC table: tricky"})


def test_another_plugin_can_supply_the_target_of_a_procedure(tmp_path):
    root = create_campaign(tmp_path / "dc", ["ose", "dcs"], HAND_MADE_MAP, "gate", [{"name": "Brannoc"}])
    engine = open_campaign(root, ScriptedDice([]), {**BUILTIN_PLUGINS, "dcs": FixedDcPlugin})

    proposal = propose(engine, "ability_check", {"member": "Brannoc", "ability": "WIS"})[0]["proposal"]

    assert proposal["target"] == {"value": 11, "source": "DC table: tricky", "editable": False}


def test_a_confirm_level_change_persists_and_makes_an_auto_procedure_wait(tmp_path):
    root = make_campaign(tmp_path)
    open_engine(root).change_setting("confirm", "search", "confirm")

    engine = open_engine(root, ScriptedDice([]))
    events = propose(engine, "search", {})

    assert engine.confirm_level("search") == "confirm"
    assert [e["type"] for e in events] == ["proposal"]


def test_a_confirm_procedure_set_to_auto_runs_when_proposed(tmp_path):
    engine = open_engine(make_campaign(tmp_path), ScriptedDice([5]))
    engine.change_setting("confirm", "ability_check", "auto")

    events = propose(engine, "ability_check", {"member": "Brannoc", "ability": "STR", "target": 12})

    assert [e["type"] for e in events] == ["mechanics"]
    assert events[0]["target"]["source"] == "proposal input, set by the Referee"


@pytest.mark.parametrize("section, key, value", [
    ("confirm", "search", "sometimes"),
    ("confirm", "no_such_procedure", "auto"),
    ("no_such_section", "x", 1),
])
def test_a_bad_setting_is_refused_and_not_saved(tmp_path, section, key, value):
    root = make_campaign(tmp_path)
    engine = open_engine(root)

    with pytest.raises(HarnessError):
        engine.change_setting(section, key, value)

    assert open_engine(root).settings() == engine.settings()
    assert engine.confirm_level("search") == "auto"


def test_the_settings_list_each_procedure_with_its_default_and_current_level(tmp_path):
    engine = open_engine(make_campaign(tmp_path))
    engine.change_setting("confirm", "listen", "confirm")

    rows = {row["procedure"]: row for row in engine.settings()["confirm"]}

    assert rows["listen"] == {"procedure": "listen", "label": "Listen at the door", "default": "auto", "level": "confirm"}
    assert rows["ability_check"]["label"] == "Ability check"
    assert rows["ability_check"]["level"] == "confirm"


class AimPlugin:
    """A generator whose targeted `aim` procedure returns its own card, a follow-up card and a card with its own target."""

    name = "aim"
    kind = "generator"

    def register(self, registry):
        registry.add_procedure("aim", self._aim, label="Aim", target=True)
        registry.add_target_source("aim", lambda state, inputs, ctx: {"value": 13, "source": "the mark"})

    @staticmethod
    def _aim(state, command, ctx):
        return [
            {"type": "mechanics", "procedure": "aim", "text": "Aimed."},
            {"type": "mechanics", "procedure": "follow_up", "text": "Followed up."},
            {"type": "mechanics", "procedure": "counter", "target": {"value": 5, "source": "own"}, "text": "Countered."},
        ]


def test_the_target_goes_only_on_the_card_of_the_procedure_that_ran(tmp_path):
    root = create_campaign(tmp_path / "aim", ["ose", "aim"], HAND_MADE_MAP, "gate", [{"name": "Brannoc"}])
    engine = open_campaign(root, ScriptedDice([]), {**BUILTIN_PLUGINS, "aim": AimPlugin})

    events = engine.act({"type": "procedure", "name": "aim", "inputs": {}})

    cards = {e["procedure"]: e for e in events if e["type"] == "mechanics"}
    assert cards["aim"]["target"] == {"value": 13, "source": "the mark"}
    assert "target" not in cards["follow_up"]
    assert cards["counter"]["target"] == {"value": 5, "source": "own"}
