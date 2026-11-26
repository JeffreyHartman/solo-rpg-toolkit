"""Tests for FlexTale encounters in new areas, DC targets, treasure and backtracking, through the engine."""
import pytest

from solo_roll.harness.errors import FlextaleDataError, IllegalActionError
from flextale_fakes import DEFAULT_TABLES, explore, make_engine


def encounter(engine):
    return engine.state()["encounter"]["current"]


def test_exploring_a_hall_rolls_the_hallway_table_and_stores_no_encounter(tmp_path):
    engine = make_engine(tmp_path, [1, 3])  # map: hall, encounter: none
    events = explore(engine)
    assert [e["type"] for e in events] == ["mechanics", "area_revealed", "mechanics", "encounter", "moved", "turn"]
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
    tables = {**DEFAULT_TABLES, "trap-a-osr": [(1, 1, "Snare: reroll, disadvantage"), (2, 20, "Pit: Save")]}
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
    tables = {**DEFAULT_TABLES, "trap-a-osr": [(1, 1, "Snare: reroll, disadvantage"), (2, 20, "Pit: Save")]}
    engine = make_engine(tmp_path, [1, 9, 1, 2, 12, 16, 10], tables=tables)  # normal DC, then two check dice
    explore(engine)
    events = check(engine, "breath")  # needs 15 or more; the worse die is 10
    assert events[0]["rolls"] == [16, 10]
    assert engine.state()["encounter"]["current"]["outcomes"][0]["status"] == "failed"


def test_a_combat_result_leaves_a_pending_combat_and_a_combat_event_for_ticket_12(tmp_path):
    from solo_roll.harness.plugins.flextale.encounters import pending_combat

    engine = make_engine(tmp_path, [1, 16, 1, 4, 3, 5, 2])  # combat, monsters roll 1, then goblin hit points and initiative
    events = explore(engine)
    assert pending_combat(engine.state()) is None  # the fight has started
    outcome = encounter(engine)["outcomes"][0]
    assert (outcome["kind"], outcome["status"], outcome["detail"]["result"]) == ("combat", "started", "Two fake goblins")
    hook = next(e for e in events if e["type"] == "combat_encounter")
    assert (hook["area"], hook["outcome"], hook["monsters"]) == ("area-2", 0, "Two fake goblins")


def test_a_trap_that_is_a_monster_becomes_combat(tmp_path):
    tables = {**DEFAULT_TABLES, "trap-a-osr": [(1, 20, "Monster: Change the threat to combat")]}
    engine = make_engine(tmp_path, [1, 9, 1, 12, 4, 4, 4, 4, 5, 2], tables=tables)
    explore(engine)
    outcome = encounter(engine)["outcomes"][0]
    assert (outcome["kind"], outcome["via"]["result"].split(":")[0]) == ("combat", "Monster")


def test_combat_and_treasure_keeps_the_treasure_pending(tmp_path):
    engine = make_engine(tmp_path, [1, 19, 11, 3, 3, 3, 3, 5, 2])  # monsters roll 11: an ogre
    explore(engine)
    kinds = [(o["kind"], o["status"]) for o in encounter(engine)["outcomes"]]
    assert kinds == [("combat", "started"), ("treasure", "pending")]


def test_roll_twice_resolves_two_more_results_and_skips_further_roll_twice(tmp_path):
    engine = make_engine(tmp_path, [1, 18, 18, 3, 13, 1])  # twice; (twice again ignored); none; secret
    explore(engine)
    assert [o["kind"] for o in encounter(engine)["outcomes"]] == ["none", "secret"]


def treasure(engine):
    return engine.act({"type": "procedure", "name": "treasure"})


def inventory(engine):
    return engine.state()["inventory"]


def test_inventory_starts_empty(tmp_path):
    assert inventory(make_engine(tmp_path, [])) == {"gp": 0, "gems": {}, "items": {}}


def test_coin_treasure_rolls_the_amount_of_the_contexts_column(tmp_path):
    engine = make_engine(tmp_path, [3, 1, 3])  # low coin, sub-table, 1d4 = 3
    events = treasure(engine)
    assert inventory(engine)["gp"] == 3
    assert any(e["type"] == "treasure" for e in events)


def test_gem_treasure_counts_gems_by_name(tmp_path):
    engine = make_engine(tmp_path, [5, 1, 2])  # low gems, sub-table, 1d4x = 2
    treasure(engine)
    assert inventory(engine)["gems"] == {"Agate": 2}


def test_item_treasure_rolls_its_table_and_counts_the_item(tmp_path):
    engine = make_engine(tmp_path, [7, 1])
    treasure(engine)
    assert inventory(engine)["items"] == {"Fake Healing": 1}
    engine = make_engine(tmp_path / "b", [9])  # a scroll has no sub-table here
    treasure(engine)
    assert inventory(engine)["items"] == {"Scroll": 1}


def test_no_treasure_and_contact_poison_reroll(tmp_path):
    engine = make_engine(tmp_path, [2])
    treasure(engine)
    assert inventory(engine) == {"gp": 0, "gems": {}, "items": {}}
    engine = make_engine(tmp_path / "b", [1, 9])  # poison: reroll into a scroll
    events = treasure(engine)
    assert inventory(engine)["items"] == {"Scroll": 1}
    assert "contact poison" in next(e for e in events if e["type"] == "treasure")["text"].lower()


def test_additional_treasure_applies_both_rolls(tmp_path):
    engine = make_engine(tmp_path, [11, 9, 7, 1])  # scroll and potion
    treasure(engine)
    assert inventory(engine)["items"] == {"Scroll": 1, "Fake Healing": 1}


def test_favorable_treasure_asks_the_player_to_pick_a_draw(tmp_path):
    engine = make_engine(tmp_path, [13, 9, 7, 1])  # draws: scroll (9) and potion (7)
    events = treasure(engine)
    assert inventory(engine)["items"] == {}
    card = engine.state()["judgments"]["pending"][0]
    assert card["category"] == "treasure"
    assert card["options"] == ["First draw: Scroll", "Second draw: Fake Healing"]
    assert card["suggestion"] == "First draw: Scroll"  # the higher first roll
    assert not any(e["type"] == "treasure" for e in events)
    engine.act({"type": "answer_judgment", "id": card["id"], "answer": "Second draw: Fake Healing"})
    assert inventory(engine)["items"] == {"Fake Healing": 1}
    assert engine.state()["judgments"]["pending"] == []


def test_the_referee_owning_treasure_picks_its_suggestion(tmp_path):
    engine = make_engine(tmp_path, [13, 9, 7, 1])
    engine.change_setting("judgment", "treasure", "referee")
    treasure(engine)
    assert inventory(engine)["items"] == {"Scroll": 1}


def test_the_difficulty_context_picks_the_coin_column_and_tables(tmp_path):
    from flextale_fakes import DEFAULT_TABLES

    tables = {n.replace("-a", "-b") if n.startswith("treasure") else n: r for n, r in DEFAULT_TABLES.items()}
    engine = make_engine(tmp_path, [3, 1, 2, 4], tables=tables)  # 2d4 = 2 + 4
    engine.change_setting("difficulty", "context", "B")
    treasure(engine)
    assert inventory(engine)["gp"] == 6


def test_a_missing_treasure_table_raises_the_typed_error_and_keeps_the_inventory(tmp_path):
    engine = make_engine(tmp_path, [3], drop=("treasure-low-coin-a-osr",))
    with pytest.raises(FlextaleDataError, match="treasure-low-coin-a-osr"):
        treasure(engine)
    assert inventory(engine)["gp"] == 0


def test_pending_treasure_is_taken_once_and_not_offered_while_combat_is_pending(tmp_path):
    engine = make_engine(tmp_path, [1, 19, 11, 3, 3, 3, 3, 5, 2, 3, 1, 4])
    explore(engine)
    assert "treasure" not in [a["command"].get("name") for a in engine.available_actions()]
    treasure(engine)
    assert inventory(engine)["gp"] == 4
    assert encounter(engine)["outcomes"][1]["status"] == "resolved"


def shuttle(engine, times):
    events = []
    for i in range(times):
        events += engine.act({"type": "move", "to": "start" if i % 2 == 0 else "area-2"})
    return events


def test_backtracking_rolls_a_random_encounter_on_every_fourth_known_area(tmp_path):
    engine = make_engine(tmp_path, [1, 1, 15, 1, 4, 3, 5, 2])  # explore (hall, none); fourth move: combat, goblins
    explore(engine)
    quiet = shuttle(engine, 3)  # exhausts ScriptedDice if any of these rolled
    assert not [e for e in quiet if e["type"] == "encounter"]
    events = engine.act({"type": "move", "to": "area-2"})
    card = next(e for e in events if e["type"] == "encounter")
    assert (card["source"], card["area"]) == ("backtracking", "area-2")
    assert encounter(engine)["outcomes"][0]["kind"] == "combat"
    assert any(e["type"] == "combat_encounter" for e in events)


def test_the_backtrack_count_continues_after_a_roll(tmp_path):
    engine = make_engine(tmp_path, [1, 1, 3, 3])
    explore(engine)
    shuttle(engine, 4)
    shuttle(engine, 3)
    events = engine.act({"type": "move", "to": "area-2"})
    assert [e["source"] for e in events if e["type"] == "encounter"] == ["backtracking"]
    assert engine.state()["encounter"]["backtracks"] == 8


def test_a_missing_table_on_the_backtrack_roll_rolls_the_move_back(tmp_path):
    engine = make_engine(tmp_path, [1, 1])
    explore(engine)
    shuttle(engine, 3)
    import os
    os.remove(tmp_path / "data/tables/quickstart/hallway-encounter-a.json")
    with pytest.raises(FlextaleDataError):
        engine.act({"type": "move", "to": "area-2"})
    assert engine.state()["party"]["area"] == "start"


def test_state_note_lists_the_inventory_and_the_current_encounter(tmp_path):
    engine = make_engine(tmp_path, [1, 11, 1, 3, 3, 1, 3])  # obstacle with DC +2; then low coin 3
    explore(engine)
    treasure(engine)
    note = (tmp_path / "campaign" / "vault" / "State.md").read_text()
    assert "Coins: 3 gp" in note
    assert "obstacle (open): Rubble: Strength check" in note


def test_the_settings_list_the_difficulty_context_as_an_option(tmp_path):
    engine = make_engine(tmp_path, [])
    engine.change_setting("difficulty", "context", "D")
    row = engine.settings()["options"][0]
    assert (row["section"], row["choices"], row["value"], row["default"]) == ("difficulty", ["A", "B", "C", "D"], "D", "A")


def _visible(engine):
    from solo_roll.harness.playerview import player_state
    return player_state(engine.state())


def test_an_unfound_trap_and_a_secret_stay_out_of_state_note_and_player_view(tmp_path):
    engine = make_engine(tmp_path, [1, 9, 1, 3])  # trap with a DC
    events = explore(engine)
    assert encounter(engine)["outcomes"][0]["kind"] == "trap"
    note = (tmp_path / "campaign" / "vault" / "State.md").read_text()
    assert "trap" not in note.lower() and "Dart" not in note and "Pit" not in note
    assert _visible(engine)["encounter"]["current"]["outcomes"] == []
    hidden = [e for e in events if e.get("hidden")]
    assert hidden and all(e["type"] == "mechanics" for e in hidden)
    text = next(e for e in events if e["type"] == "encounter")["text"]
    assert "trap" not in text.lower()

    engine = make_engine(tmp_path / "b", [1, 13, 1])
    explore(engine)
    assert "hidden latch" not in (tmp_path / "b" / "campaign" / "vault" / "State.md").read_text()
    assert _visible(engine)["encounter"]["current"]["outcomes"] == []


def test_a_trap_shows_after_its_check_is_made(tmp_path):
    engine = make_engine(tmp_path, [1, 9, 1, 3, 5])  # trap with DC +2, then a save roll
    explore(engine)
    check(engine, "breath")
    assert [o["kind"] for o in _visible(engine)["encounter"]["current"]["outcomes"]] == ["trap"]
    assert "trap (" in (tmp_path / "campaign" / "vault" / "State.md").read_text()


def test_the_player_view_drops_unknown_areas_with_their_links_and_exits():
    from solo_roll.harness.playerview import player_state
    state = {"map": {
        "areas": {"a": {"known": True}, "b": {"known": False}},
        "connections": [{"a": "a", "b": "b"}],
        "open_exits": [{"id": "x", "area": "a"}, {"id": "y", "area": "b"}],
    }}
    seen = player_state(state)["map"]
    assert list(seen["areas"]) == ["a"] and seen["connections"] == []
    assert [e["id"] for e in seen["open_exits"]] == ["x"]
    assert len(state["map"]["areas"]) == 2


def test_resting_rolls_the_current_areas_encounter_table_after_the_turn(tmp_path):
    engine = make_engine(tmp_path, [1, 1, 11, 1, 3])  # explore a hall with no encounter; rest rolls an obstacle with DC +2
    explore(engine)
    events = engine.act({"type": "procedure", "name": "rest"})
    assert [e["type"] for e in events if e["type"] in ("turn", "encounter")] == ["turn", "encounter"]
    current = encounter(engine)
    assert (current["area"], current["source"]) == ("area-2", "rest")
    assert current["table"] == "quickstart/hallway-encounter-a"
    assert [o["kind"] for o in current["outcomes"]] == ["obstacle"]



def test_a_check_against_a_save_takes_the_names_from_the_character(tmp_path):
    party = [{"name": "Brannoc", "abilities": {"STR": 14}, "saves": {"doom": 15}}]
    engine = make_engine(tmp_path, [1, 9, 1, 3, 15], party=party)  # trap with DC +2
    explore(engine)
    with pytest.raises(IllegalActionError, match="breath"):
        check(engine, "breath")
    events = check(engine, "doom")
    assert next(e for e in events if e["type"] == "mechanics")["target"]["value"] == 13
