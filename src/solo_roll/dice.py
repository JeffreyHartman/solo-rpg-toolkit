"""Dice notation: `NdN` with an optional modifier, rolled one die at a time.

Rolling 2d6 as a single draw from 2-12 gives a flat distribution, which would
break every OSE 2d6 table. Each die is drawn separately and summed.
"""
import re
from dataclasses import dataclass

from .rng import DiceSource

__all__ = ["DiceError", "DiceSpec", "parse_dice", "roll_dice"]

NOTATION = re.compile(r"^(\d*)d(\d+)(?:([+-])(\d+))?$", re.IGNORECASE)
MAX_COUNT = 100


class DiceError(Exception):
    """Raised when dice notation cannot be parsed."""


@dataclass(frozen=True)
class DiceSpec:
    count: int
    faces: int
    modifier: int = 0

    @property
    def minimum(self) -> int:
        return self.count + self.modifier

    @property
    def maximum(self) -> int:
        return self.count * self.faces + self.modifier

    @property
    def notation(self) -> str:
        text = f"{self.count}d{self.faces}"
        if self.modifier:
            text += f"{self.modifier:+d}"
        return text


def parse_dice(text: str) -> DiceSpec:
    compact = re.sub(r"\s+", "", str(text))
    match = NOTATION.match(compact)
    if not match:
        raise DiceError(f"invalid dice '{text}' — expected NdN, NdN+M, or dN")

    count_text, faces_text, sign, amount = match.groups()
    count = int(count_text) if count_text else 1
    faces = int(faces_text)
    if count < 1:
        raise DiceError(f"invalid dice '{text}' — need at least one die")
    if count > MAX_COUNT:
        raise DiceError(f"invalid dice '{text}' — at most {MAX_COUNT} dice")
    if faces < 2:
        raise DiceError(f"invalid dice '{text}' — dice must have at least 2 sides")

    modifier = 0
    if sign:
        modifier = int(amount) * (1 if sign == "+" else -1)
    return DiceSpec(count=count, faces=faces, modifier=modifier)


def roll_dice(spec: DiceSpec, dice: DiceSource) -> dict:
    rolls = [dice.roll(1, spec.faces) for _ in range(spec.count)]
    return {
        "dice": spec.notation,
        "rolls": rolls,
        "modifier": spec.modifier,
        "total": sum(rolls) + spec.modifier,
    }
