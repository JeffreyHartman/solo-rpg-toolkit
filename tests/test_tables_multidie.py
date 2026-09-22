import json

import pytest

from solo_roll.rng import ScriptedDice
from solo_roll.tables import TableDataError, roll_table


def write_table(tmp_path, name, payload):
    path = tmp_path / "tables" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return tmp_path


REACTION = {
    "name": "ose/reaction",
    "display_name": "Monster Reaction",
    "description": "OSE 2d6 monster reaction roll.",
    "dice": "2d6",
    "ranges": [
        {"min": -10, "max": 2, "result": "Hostile, attacks"},
        {"min": 3, "max": 5, "result": "Unfriendly, may attack"},
        {"min": 6, "max": 8, "result": "Neutral, uncertain"},
        {"min": 9, "max": 11, "result": "Indifferent, uninterested"},
        {"min": 12, "max": 30, "result": "Friendly, helpful"},
    ],
}


class TestMultiDieTables:
    def test_rolls_each_die_separately(self, tmp_path):
        data = write_table(tmp_path, "ose/reaction", REACTION)
        payload = roll_table("ose/reaction", data, ScriptedDice([1, 1]))
        assert payload["rolls"] == [1, 1]
        assert payload["roll"] == 2
        assert payload["result"] == "Hostile, attacks"

    def test_midpoint_band(self, tmp_path):
        data = write_table(tmp_path, "ose/reaction", REACTION)
        payload = roll_table("ose/reaction", data, ScriptedDice([3, 4]))
        assert payload["roll"] == 7
        assert payload["result"] == "Neutral, uncertain"

    def test_flat_entries_still_work(self, tmp_path):
        data = write_table(tmp_path, "t", {
            "name": "t", "description": "d", "dice": "d6",
            "entries": ["a", "b", "c", "d", "e", "f"],
        })
        payload = roll_table("t", data, ScriptedDice([3]))
        assert payload["result"] == "c"
        assert payload["roll"] == 3

    def test_flat_entries_rejected_for_multi_die(self, tmp_path):
        data = write_table(tmp_path, "t", {
            "name": "t", "description": "d", "dice": "2d6",
            "entries": ["a"] * 12,
        })
        with pytest.raises(TableDataError):
            roll_table("t", data, ScriptedDice([1, 1]))


class TestModifier:
    def test_modifier_shifts_result(self, tmp_path):
        data = write_table(tmp_path, "ose/reaction", REACTION)
        payload = roll_table("ose/reaction", data, ScriptedDice([3, 4]), modifier=2)
        assert payload["roll"] == 9
        assert payload["natural"] == 7
        assert payload["modifier"] == 2
        assert payload["result"] == "Indifferent, uninterested"

    def test_modifier_can_push_past_the_ends(self, tmp_path):
        data = write_table(tmp_path, "ose/reaction", REACTION)
        payload = roll_table("ose/reaction", data, ScriptedDice([6, 6]), modifier=2)
        assert payload["roll"] == 14
        assert payload["result"] == "Friendly, helpful"

    def test_modifier_omitted_when_zero(self, tmp_path):
        data = write_table(tmp_path, "ose/reaction", REACTION)
        payload = roll_table("ose/reaction", data, ScriptedDice([2, 2]))
        assert payload["modifier"] == 0
