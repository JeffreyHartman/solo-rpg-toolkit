import pytest
from collections.abc import Callable

from solo_roll.rng import ScriptedDice


@pytest.fixture
def scripted_dice() -> Callable[[list[int]], ScriptedDice]:
    def _make(values: list[int]) -> ScriptedDice:
        return ScriptedDice(values)
    return _make
