import random
from typing import Protocol


class DiceSource(Protocol):
    def roll(self, low: int, high: int) -> int: ...


class RandomDice:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def roll(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)


class ScriptedDice:
    def __init__(self, values: list[int]):
        self._values = list(values)
        self._index = 0

    def roll(self, low: int, high: int) -> int:
        if self._index >= len(self._values):
            raise RuntimeError(
                f"ScriptedDice exhausted after {self._index} rolls"
            )
        value = self._values[self._index]
        self._index += 1
        if not (low <= value <= high):
            raise ValueError(
                f"ScriptedDice value {value} out of bounds [{low}, {high}]"
            )
        return value
