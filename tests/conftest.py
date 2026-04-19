import pytest

from solo_roll.rng import ScriptedDice


@pytest.fixture
def scripted_dice():
    def _make(values: list[int]) -> ScriptedDice:
        return ScriptedDice(values)
    return _make
