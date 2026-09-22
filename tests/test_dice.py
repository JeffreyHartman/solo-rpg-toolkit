import pytest

from solo_roll.dice import DiceError, DiceSpec, parse_dice, roll_dice
from solo_roll.rng import ScriptedDice


class TestParseDice:
    def test_plain_die(self):
        assert parse_dice("d20") == DiceSpec(count=1, faces=20, modifier=0)

    def test_multiple_dice(self):
        assert parse_dice("3d6") == DiceSpec(count=3, faces=6, modifier=0)

    def test_positive_modifier(self):
        assert parse_dice("1d8+1") == DiceSpec(count=1, faces=8, modifier=1)

    def test_negative_modifier(self):
        assert parse_dice("2d6-2") == DiceSpec(count=2, faces=6, modifier=-2)

    def test_whitespace_and_case(self):
        assert parse_dice(" 2D6 + 1 ") == DiceSpec(count=2, faces=6, modifier=1)

    @pytest.mark.parametrize("bad", ["", "d", "6", "0d6", "2d1", "d0", "2d6+", "xd6", "2d6+x"])
    def test_rejects_malformed(self, bad):
        with pytest.raises(DiceError):
            parse_dice(bad)

    def test_rejects_absurd_count(self):
        with pytest.raises(DiceError):
            parse_dice("1000d6")


class TestSpecBounds:
    def test_bounds_without_modifier(self):
        spec = parse_dice("2d6")
        assert (spec.minimum, spec.maximum) == (2, 12)

    def test_bounds_with_modifier(self):
        spec = parse_dice("2d6+1")
        assert (spec.minimum, spec.maximum) == (3, 13)


class TestRollDice:
    def test_sums_individual_dice(self):
        payload = roll_dice(parse_dice("3d6"), ScriptedDice([4, 1, 6]))
        assert payload["rolls"] == [4, 1, 6]
        assert payload["total"] == 11

    def test_applies_modifier(self):
        payload = roll_dice(parse_dice("1d8+2"), ScriptedDice([5]))
        assert payload["rolls"] == [5]
        assert payload["modifier"] == 2
        assert payload["total"] == 7

    def test_reports_notation(self):
        payload = roll_dice(parse_dice("2d6-1"), ScriptedDice([3, 3]))
        assert payload["dice"] == "2d6-1"

    def test_each_die_rolled_separately(self):
        # A 2d6 rolled as one 2-12 draw would have a flat distribution; it must not.
        payload = roll_dice(parse_dice("2d6"), ScriptedDice([1, 1]))
        assert payload["total"] == 2
