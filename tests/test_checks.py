import json

import pytest

from solo_roll.checks import CheckError, morale_check, surprise_check
from solo_roll.character import roll_character
from solo_roll.rng import ScriptedDice


class TestMorale:
    def test_equal_to_score_holds(self):
        result = morale_check(8, ScriptedDice([4, 4]))
        assert result["roll"] == 8
        assert result["holds"] is True

    def test_above_score_breaks(self):
        result = morale_check(8, ScriptedDice([5, 4]))
        assert result["roll"] == 9
        assert result["holds"] is False
        assert "flee" in result["result"].lower()

    def test_modifier_applies(self):
        result = morale_check(8, ScriptedDice([4, 4]), modifier=1)
        assert result["roll"] == 9
        assert result["holds"] is False

    def test_twelve_never_checks(self):
        result = morale_check(12, ScriptedDice([]))
        assert result["holds"] is True
        assert result["checked"] is False

    def test_two_never_holds(self):
        result = morale_check(2, ScriptedDice([]))
        assert result["holds"] is False
        assert result["checked"] is False

    @pytest.mark.parametrize("bad", [1, 13, -3])
    def test_rejects_out_of_range_score(self, bad):
        with pytest.raises(CheckError):
            morale_check(bad, ScriptedDice([]))


class TestSurprise:
    def test_one_and_two_surprise(self):
        assert surprise_check(ScriptedDice([1]))["surprised"] is True
        assert surprise_check(ScriptedDice([2]))["surprised"] is True

    def test_three_and_up_do_not(self):
        assert surprise_check(ScriptedDice([3]))["surprised"] is False
        assert surprise_check(ScriptedDice([6]))["surprised"] is False


class TestCharacter:
    def test_rolls_six_scores_in_order(self):
        rolled = roll_character(ScriptedDice([3, 3, 3] * 6 + [5]))
        assert list(rolled["abilities"]) == ["STR", "INT", "WIS", "DEX", "CON", "CHA"]
        assert rolled["abilities"]["STR"] == 9

    def test_three_dice_per_score(self):
        rolled = roll_character(ScriptedDice([1, 2, 3, 4, 5, 6, 1, 1, 1, 6, 6, 6, 2, 2, 2, 3, 3, 3, 4]))
        assert rolled["abilities"]["STR"] == 6
        assert rolled["abilities"]["INT"] == 15
        assert rolled["abilities"]["WIS"] == 3
        assert rolled["abilities"]["CON"] == 6

    def test_hit_points_use_the_class_hit_die(self):
        rolled = roll_character(ScriptedDice([3] * 18 + [7]), character_class="Fighter")
        assert rolled["hit_die"] == "d8"
        assert rolled["hit_points"] == 7

    def test_hit_points_never_below_one(self):
        rolled = roll_character(ScriptedDice([1, 1, 1] + [3] * 15 + [1]), character_class="Magic-User")
        assert rolled["hit_points"] >= 1

    def test_constitution_modifies_hit_points(self):
        # CON 18 is +3 in OSE.
        dice = ScriptedDice([3] * 12 + [6, 6, 6] + [3] * 3 + [4])
        rolled = roll_character(dice, character_class="Fighter")
        assert rolled["abilities"]["CON"] == 18
        assert rolled["hit_points"] == 7

    def test_rejects_unknown_class(self):
        with pytest.raises(CheckError):
            roll_character(ScriptedDice([3] * 19), character_class="Warlock")
