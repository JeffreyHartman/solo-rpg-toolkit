"""Tests for judgment calls: a procedure step raises one, the player answers, the setting moves it to the Referee."""
import pytest
from harness_fixtures import BUILTIN_PLUGINS, HAND_MADE_MAP

from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.errors import IllegalActionError, SettingError
from solo_roll.harness.judgment import judgment_request
from solo_roll.rng import ScriptedDice


class ProgressPlugin:
    """One procedure: roll, ask whether the roll marks progress, then mark it or not."""

    name = "progress"
    kind = "generator"

    def register(self, registry):
        registry.add_judgment_category("progress", "Does an action mark progress?")
        registry.add_state_default("progress", lambda state: 0)
        registry.add_procedure("scout", self._scout, label="Scout")

    @staticmethod
    def _scout(state, command, ctx):
        if "judgment" not in command:
            roll = ctx.dice.roll(1, 6)
            return [
                {"type": "mechanics", "procedure": "scout", "rolls": [roll], "text": f"Scout rolls {roll}."},
                judgment_request(
                    "progress",
                    "Does the scouting mark progress?",
                    suggestion="yes",
                    reason="The party learned the layout.",
                    options=["yes", "no"],
                    data={"roll": roll},
                ),
            ]
        answer = command["judgment"]["answer"]
        if answer == "yes":
            state["progress"] += 1
        return [{"type": "scouted", "progress": state["progress"], "text": f"Progress is {state['progress']}."}]


FACTORIES = {**BUILTIN_PLUGINS, "progress": ProgressPlugin}


def make_engine(tmp_path, rolls=()):
    root = create_campaign(
        tmp_path / "campaign", plugins=["ose", "progress"], map_data=HAND_MADE_MAP, start="gate", party=[{"name": "Brannoc"}]
    )
    return open_campaign(root, ScriptedDice(list(rolls)), FACTORIES)


def reopen(tmp_path):
    return open_campaign(tmp_path / "campaign", ScriptedDice([]), FACTORIES)


def scout(engine):
    return engine.act({"type": "procedure", "name": "scout"})


def test_a_judgment_call_blocks_its_procedure_until_the_player_answers(tmp_path):
    engine = make_engine(tmp_path, [4])

    events = scout(engine)

    assert [e["type"] for e in events] == ["mechanics", "judgment_call"]
    card = events[1]["judgment"]
    assert (card["category"], card["question"], card["suggestion"]) == (
        "progress",
        "Does the scouting mark progress?",
        "yes",
    )
    assert card["options"] == ["yes", "no"]
    assert engine.state()["judgments"]["pending"] == [card]
    assert engine.state()["progress"] == 0

    answered = engine.act({"type": "answer_judgment", "id": card["id"], "answer": "yes"})

    assert [e["type"] for e in answered] == ["judgment_answered", "scouted"]
    assert answered[0]["answer"] == "yes"
    assert engine.state()["progress"] == 1
    assert engine.state()["judgments"]["pending"] == []


def test_the_owner_setting_defaults_to_ask_changes_any_time_and_persists(tmp_path):
    engine = make_engine(tmp_path)
    row = lambda e: next(r for r in e.settings()["judgment"] if r["category"] == "progress")  # noqa: E731
    assert row(engine)["owner"] == "ask"

    engine.change_setting("judgment", "progress", "referee")

    reopened = reopen(tmp_path)
    assert row(reopened)["owner"] == "referee"
    engine.change_setting("judgment", "progress", "ask")
    assert row(reopen(tmp_path))["owner"] == "ask"


def test_a_bad_owner_or_category_is_refused_and_saves_nothing(tmp_path):
    engine = make_engine(tmp_path)
    with pytest.raises(SettingError):
        engine.change_setting("judgment", "progress", "nobody")
    with pytest.raises(SettingError):
        engine.change_setting("judgment", "no-such", "referee")
    assert engine.judgment_owner("progress") == "ask"


def test_when_the_referee_decides_the_log_records_the_decision_and_its_reason(tmp_path):
    engine = make_engine(tmp_path, [4])
    engine.change_setting("judgment", "progress", "referee")

    events = scout(engine)

    assert [e["type"] for e in events] == ["mechanics", "judgment_decided", "scouted"]
    decided = events[1]
    assert (decided["answer"], decided["reason"]) == ("yes", "The party learned the layout.")
    assert engine.state()["progress"] == 1
    assert engine.state()["judgments"]["pending"] == []
    raw = next((tmp_path / "campaign" / "vault" / "Sessions" / "Raw").glob("*.md")).read_text()
    assert "The party learned the layout." in raw


def test_an_answer_outside_the_options_or_to_an_unknown_card_is_refused(tmp_path):
    engine = make_engine(tmp_path, [4])
    card = scout(engine)[1]["judgment"]

    with pytest.raises(IllegalActionError):
        engine.act({"type": "answer_judgment", "id": card["id"], "answer": "maybe"})
    with pytest.raises(IllegalActionError):
        engine.act({"type": "answer_judgment", "id": "j99", "answer": "yes"})
    assert len(engine.state()["judgments"]["pending"]) == 1


def test_the_player_can_answer_no_and_the_procedure_continues_from_that_answer(tmp_path):
    engine = make_engine(tmp_path, [4])
    card = scout(engine)[1]["judgment"]

    engine.act({"type": "answer_judgment", "id": card["id"], "answer": "no"})

    assert engine.state()["progress"] == 0


def test_the_referee_can_raise_a_judgment_call_outside_any_procedure(tmp_path):
    engine = make_engine(tmp_path)
    command = {
        "type": "judgment",
        "category": "progress",
        "question": "Does talking to the guard mark progress?",
        "suggestion": "no",
        "reason": "Nothing was learned.",
    }

    card = engine.act(command)[0]["judgment"]
    assert engine.state()["judgments"]["pending"] == [card]
    assert card["resume"] is None
    assert engine.act({"type": "answer_judgment", "id": card["id"], "answer": "yes"})[0]["answer"] == "yes"

    engine.change_setting("judgment", "progress", "referee")
    assert [e["type"] for e in engine.act(command)] == ["judgment_decided"]


def test_an_unknown_category_is_refused(tmp_path):
    engine = make_engine(tmp_path)
    with pytest.raises(IllegalActionError):
        engine.act({"type": "judgment", "category": "x", "question": "q", "suggestion": "s", "reason": "r"})
