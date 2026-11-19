import json

import pytest

from solo_roll.dungeon import DungeonError, advance_turn, load_state, save_state
from solo_roll.rng import ScriptedDice

WANDERING = {
    "name": "ose/w", "description": "d", "dice": "d6",
    "entries": ["bat", "spider", "goblins", "jelly", "basilisk omen", "goblin raid"],
}
REACTION = {
    "name": "ose/reaction", "description": "d", "dice": "2d6",
    "ranges": [
        {"min": -10, "max": 2, "result": "Hostile, attacks"},
        {"min": 3, "max": 5, "result": "Unfriendly, may attack"},
        {"min": 6, "max": 8, "result": "Neutral, uncertain"},
        {"min": 9, "max": 11, "result": "Indifferent, uninterested"},
        {"min": 12, "max": 30, "result": "Friendly, helpful"},
    ],
}


@pytest.fixture
def data_dir(tmp_path):
    root = tmp_path / "data"
    for name, payload in (("ose/w", WANDERING), ("ose/reaction", REACTION)):
        path = root / "tables" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    return root


def base_state(**over):
    state = {
        "turn": 0,
        "level": 1,
        "room": None,
        "light": [{"kind": "torch", "bearer": "Hana", "turns_left": 6}],
        "turns_since_rest": 0,
        "wandering": None,
    }
    state.update(over)
    return state


class TestClock:
    def test_advances_one_turn(self, data_dir):
        payload = advance_turn(base_state(), data_dir, ScriptedDice([]))
        assert payload["state"]["turn"] == 1

    def test_burns_one_turn_of_light(self, data_dir):
        payload = advance_turn(base_state(), data_dir, ScriptedDice([]))
        assert payload["state"]["light"][0]["turns_left"] == 5

    def test_reports_light_going_out(self, data_dir):
        state = base_state(light=[{"kind": "torch", "bearer": "Hana", "turns_left": 1}])
        payload = advance_turn(state, data_dir, ScriptedDice([]))
        assert payload["light_expired"] == [{"kind": "torch", "bearer": "Hana"}]
        assert payload["state"]["light"] == []

    def test_darkness_is_flagged(self, data_dir):
        state = base_state(light=[{"kind": "torch", "bearer": "Hana", "turns_left": 1}])
        payload = advance_turn(state, data_dir, ScriptedDice([]))
        assert payload["in_darkness"] is True

    def test_six_turns_triggers_rest_due(self, data_dir):
        state = base_state(turns_since_rest=5, light=[])
        payload = advance_turn(state, data_dir, ScriptedDice([]))
        assert payload["rest_due"] is True

    def test_rest_not_due_before_six(self, data_dir):
        payload = advance_turn(base_state(turns_since_rest=2), data_dir, ScriptedDice([]))
        assert payload["rest_due"] is False


class TestWandering:
    def setup_wandering(self, **over):
        cfg = {"table": "ose/w", "interval": 2, "chance": 1, "die": 6}
        cfg.update(over)
        return base_state(turn=1, wandering=cfg)

    def test_no_check_on_off_turns(self, data_dir):
        payload = advance_turn(base_state(turn=0, wandering={
            "table": "ose/w", "interval": 2, "chance": 1, "die": 6}),
            data_dir, ScriptedDice([]))
        assert payload["wandering"]["checked"] is False

    def test_check_happens_on_the_interval(self, data_dir):
        payload = advance_turn(self.setup_wandering(), data_dir, ScriptedDice([4]))
        assert payload["wandering"]["checked"] is True
        assert payload["wandering"]["encounter"] is False

    def test_encounter_rolls_the_full_chain(self, data_dir):
        # d6 check, table d6, 2d6 distance, 2 surprise d6, 2d6 reaction
        dice = ScriptedDice([1, 3, 4, 2, 5, 2, 4, 4])
        payload = advance_turn(self.setup_wandering(), data_dir, dice)
        w = payload["wandering"]
        assert w["encounter"] is True
        assert w["monster"]["result"] == "goblins"
        assert w["distance_feet"] == 60
        assert w["surprise"]["party"] is False
        assert w["surprise"]["monsters"] is True
        assert w["reaction"]["result"] == "Neutral, uncertain"

    def test_no_wandering_config_means_no_check(self, data_dir):
        payload = advance_turn(base_state(turn=1), data_dir, ScriptedDice([]))
        assert payload["wandering"]["checked"] is False


class TestStateFile:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "clock.json"
        save_state(path, base_state())
        assert load_state(path)["turn"] == 0

    def test_missing_file_is_an_error(self, tmp_path):
        with pytest.raises(DungeonError):
            load_state(tmp_path / "absent.json")

    def test_six_turns_burns_a_torch_out(self, data_dir, tmp_path):
        path = tmp_path / "clock.json"
        save_state(path, base_state())
        for _ in range(6):
            payload = advance_turn(load_state(path), data_dir, ScriptedDice([]))
            save_state(path, payload["state"])
        assert load_state(path)["light"] == []
        assert load_state(path)["turn"] == 6


class TestRest:
    """`advance_turn(rest=True)` resets `turns_since_rest` and still spends the
    turn. Rest rule: OSE Classic Fantasy Adventures, 'Resting': one turn of rest
    per hour (6 turns); without it, -1 to attack and damage. Audit finding 6."""

    def test_rest_turn_resets_the_counter(self, data_dir):
        payload = advance_turn(base_state(turns_since_rest=6), data_dir,
                               ScriptedDice([]), rest=True)
        assert payload["state"]["turns_since_rest"] == 0
        assert payload["rest_due"] is False
        assert payload["rested"] is True

    def test_rest_turn_still_spends_the_turn_and_burns_light(self, data_dir):
        payload = advance_turn(base_state(), data_dir, ScriptedDice([]), rest=True)
        assert payload["state"]["turn"] == 1
        assert payload["state"]["light"][0]["turns_left"] == 5

    def test_counter_counts_again_after_a_rest(self, data_dir):
        state = advance_turn(base_state(turns_since_rest=6), data_dir,
                             ScriptedDice([]), rest=True)["state"]
        payload = advance_turn(state, data_dir, ScriptedDice([]))
        assert payload["state"]["turns_since_rest"] == 1
        assert payload["rest_due"] is False


class TestWanderingConfigAliases:
    """`advance_turn` accepts the key names docs/dungeon-schema.md uses for the
    wandering config. Audit finding 7."""

    def test_schema_key_names_are_accepted_as_aliases(self, data_dir):
        cfg = {"wandering_table": "ose/w", "wandering_interval_turns": 3}
        off = advance_turn(base_state(turn=1, wandering=cfg), data_dir, ScriptedDice([]))
        assert off["wandering"]["checked"] is False  # turn 2, interval 3
        on = advance_turn(base_state(turn=2, wandering=cfg), data_dir, ScriptedDice([4]))
        assert on["wandering"]["checked"] is True

    def test_missing_table_is_a_dungeon_error_not_a_key_error(self, data_dir):
        state = base_state(turn=1, wandering={"interval": 2})
        with pytest.raises(DungeonError, match="table"):
            advance_turn(state, data_dir, ScriptedDice([1]))


class TestLightShape:
    """`advance_turn` rejects a light entry whose `turns_left` is not an integer.
    Audit finding 16."""

    @pytest.mark.parametrize("entry", [
        {"kind": "torch", "bearer": "Hana", "turns": 6},
        {"kind": "torch", "bearer": "Hana", "turns_left": "6"},
        {"kind": "torch", "bearer": "Hana", "turns_left": None},
    ])
    def test_rejects_entries_without_integer_turns_left(self, data_dir, entry):
        with pytest.raises(DungeonError, match="turns_left"):
            advance_turn(base_state(light=[entry]), data_dir, ScriptedDice([]))
