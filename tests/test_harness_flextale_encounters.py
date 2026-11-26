"""Tests for FlexTale encounters in new areas, DC targets, treasure and backtracking, through the engine."""
import pytest

from solo_roll.harness.errors import FlextaleDataError
from flextale_fakes import explore, make_engine


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
