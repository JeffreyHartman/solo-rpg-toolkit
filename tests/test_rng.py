import pytest

from solo_roll.rng import RandomDice, ScriptedDice


def test_scripted_dice_yields_in_order():
    dice = ScriptedDice([3, 7, 1])
    assert dice.roll(1, 10) == 3
    assert dice.roll(1, 10) == 7
    assert dice.roll(1, 10) == 1


def test_scripted_dice_raises_when_exhausted():
    dice = ScriptedDice([5])
    dice.roll(1, 10)
    with pytest.raises(RuntimeError):
        dice.roll(1, 10)


def test_scripted_dice_validates_against_bounds():
    # A scripted value outside [low, high] is a test-authoring bug and must fail loudly.
    dice = ScriptedDice([11])
    with pytest.raises(ValueError):
        dice.roll(1, 10)


def test_random_dice_stays_in_bounds():
    dice = RandomDice(seed=0)
    for _ in range(100):
        value = dice.roll(1, 10)
        assert 1 <= value <= 10


def test_random_dice_reproducible_with_same_seed():
    a = RandomDice(seed=42)
    b = RandomDice(seed=42)
    for _ in range(20):
        assert a.roll(1, 100) == b.roll(1, 100)


def test_scripted_dice_fixture_returns_working_instance(scripted_dice):
    dice = scripted_dice([4, 5])
    assert dice.roll(1, 6) == 4
    assert dice.roll(1, 6) == 5
