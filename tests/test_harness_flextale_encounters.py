"""Tests for FlexTale encounters in new areas, DC targets, treasure and backtracking, through the engine."""
import pytest

from solo_roll.harness.errors import FlextaleDataError, IllegalActionError
from flextale_fakes import DEFAULT_TABLES, explore, make_engine


def encounter(engine):
    return engine.state()["encounter"]["current"]


def test_exploring_a_hall_rolls_the_hallway_table_and_stores_no_encounter(tmp_path):
    engine = make_engine(tmp_path, [1, 3])  # map: hall, encounter: none
    events = explore(engine)
    assert [e["type"] for e in events] == ["mechanics", "area_revealed", "mechanics", "encounter", "moved"]
    current = encounter(engine)
    assert current["area"] == "area-2"
    assert current["table"] == "quickstart/hallway-encounter-a"
    assert [o["kind"] for o in current["outcomes"]] == ["none"]


def test_a_chamber_uses_the_chamber_table_and_a_dead_end_its_own(tmp_path):
    engine = make_engine(tmp_path, [7, 1])
    explore(engine)
    assert encounter(engine)["table"] == "quickstart/chamber-encounter-a"
    engine = make_engine(tmp_path / "b", [12, 1])
    explore(engine)
    assert encounter(engine)["table"] == "quickstart/dead-end-encounter-a"


@pytest.mark.parametrize("roll,kind", [(13, "secret"), (9, "trap")])
def test_secret_and_trap_roll_their_detail_table(tmp_path, roll, kind):
    rolls = [1, roll, 1] + ([3] if kind == "trap" else [])  # a trap also rolls the DC table
    engine = make_engine(tmp_path, rolls)
    explore(engine)
    outcome = encounter(engine)["outcomes"][0]
    assert outcome["kind"] == kind
    assert outcome["detail"]["table"].startswith(f"quickstart/{'trap' if kind == 'trap' else 'secret-door'}-a")


def test_the_encounter_is_in_state_before_the_referee_sees_the_events(tmp_path):
    engine = make_engine(tmp_path, [1, 9, 1, 3])
    events = explore(engine)
    card = next(e for e in events if e["type"] == "encounter")
    assert card["outcomes"] == encounter(engine)["outcomes"]


def test_a_missing_encounter_table_raises_the_typed_error_and_changes_nothing(tmp_path):
    engine = make_engine(tmp_path, [1, 1], drop=("hallway-encounter-a",))
    before = engine.state()
    with pytest.raises(FlextaleDataError, match="hallway-encounter-a"):
        explore(engine)
    assert engine.state() == before


def test_the_difficulty_context_picks_the_table_letter(tmp_path):
    from flextale_fakes import DEFAULT_TABLES, write_tables
    tables = {n.replace("-a", "-c") if "hallway" in n else n: r for n, r in DEFAULT_TABLES.items()}
    engine = make_engine(tmp_path, [1, 1], tables=tables)
    engine.change_setting("difficulty", "context", "C")
    explore(engine)
    assert encounter(engine)["table"] == "quickstart/hallway-encounter-c"


def test_a_bad_difficulty_context_is_refused(tmp_path):
    from solo_roll.harness.errors import SettingError
    engine = make_engine(tmp_path, [])
    with pytest.raises(SettingError):
        engine.change_setting("difficulty", "context", "E")
    assert engine.settings()["options"][0]["value"] == "A"


def trap_engine(tmp_path, rolls, **kw):
    engine = make_engine(tmp_path, [1, 9, 1, *rolls], **kw)  # explore: hall, trap, first trap row
    explore(engine)
    return engine


def check(engine, against="STR", **inputs):
    return engine.act({"type": "procedure", "name": "encounter_check",
                       "inputs": {"member": "Brannoc", "against": against, **inputs}})


def test_a_trap_rolls_the_dc_table_for_the_difficulty_context(tmp_path):
    engine = trap_engine(tmp_path, [3])
    outcome = encounter(engine)["outcomes"][0]
    assert outcome["dc"]["table"] == "quickstart/difficulty-class-a-osr"
    assert (outcome["dc"]["modifier"], outcome["edge"], outcome["status"]) == (2, 0, "open")


def test_susceptible_and_resistant_dc_results_reroll_with_an_edge(tmp_path):
    engine = trap_engine(tmp_path, [1, 17])
    outcome = encounter(engine)["outcomes"][0]
    assert (outcome["dc"]["modifier"], outcome["edge"]) == (-2, -1)


def test_a_trap_that_rerolls_with_an_edge_carries_it(tmp_path):
    tables = {**DEFAULT_TABLES, "trap-a-osr": [(1, 1, "Slow: Reroll. Disadvantage on all checks."), (2, 20, "Pit: Save")]}
    engine = make_engine(tmp_path, [1, 9, 1, 2, 12], tables=tables)  # DC 12 = normal
    explore(engine)
    outcome = encounter(engine)["outcomes"][0]
    assert (outcome["detail"]["result"], outcome["edge"], outcome["dc"]["modifier"]) == ("Pit: Save", -1, 0)


def test_a_check_takes_its_target_from_the_dc_table_not_the_proposal(tmp_path):
    engine = trap_engine(tmp_path, [3])
    row = next(p for p in engine.procedures() if p["name"] == "encounter_check")
    assert row["target"] is True
    events = engine.act({"type": "propose", "procedure": "encounter_check", "reason": "disarm",
                         "inputs": {"member": "Brannoc", "against": "STR"}})
    proposal = engine.state()["proposals"]["pending"][0]
    assert proposal["target"]["value"] == 12  # STR 14 with +2 on the roll
    assert proposal["target"]["editable"] is False
    assert "DC table" in proposal["target"]["source"]
    with pytest.raises(IllegalActionError):
        engine.act({"type": "propose", "procedure": "encounter_check", "reason": "x",
                    "inputs": {"member": "Brannoc", "against": "STR", "target": 20}})


def test_an_ability_check_rolls_under_and_resolves_the_obstacle(tmp_path):
    engine = make_engine(tmp_path, [1, 11, 1, 3, 12])  # obstacle, DC +2
    explore(engine)
    events = check(engine, "STR")  # target 12, rolled 12
    card = next(e for e in events if e["type"] == "mechanics")
    assert (card["result"], card["target"]["value"]) == ("Success", 12)
    assert encounter(engine)["outcomes"][0]["status"] == "resolved"


def test_a_failed_save_marks_the_trap_failed(tmp_path):
    engine = trap_engine(tmp_path, [3, 12])  # breath save 15, DC +2: needs 13, rolled 12
    events = check(engine, "breath")
    assert next(e for e in events if e["type"] == "mechanics")["result"] == "Failure"
    assert encounter(engine)["outcomes"][0]["status"] == "failed"


def test_a_check_with_disadvantage_rolls_two_dice_and_keeps_the_worse(tmp_path):
    tables = {**DEFAULT_TABLES, "trap-a-osr": [(1, 1, "Slow: Reroll. Disadvantage on all checks."), (2, 20, "Pit: Save")]}
    engine = make_engine(tmp_path, [1, 9, 1, 2, 12, 16, 10], tables=tables)  # normal DC, then two check dice
    explore(engine)
    events = check(engine, "breath")  # needs 15 or more; the worse die is 10
    assert events[0]["rolls"] == [16, 10]
    assert engine.state()["encounter"]["current"]["outcomes"][0]["status"] == "failed"
