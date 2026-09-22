"""OSE checks the referee makes: morale and surprise.

Morale 2 and 12 are not rolled. The book says a 2 never fights unless cornered
and a 12 fights until killed, so rolling them would invent a result.
"""
from .dice import parse_dice, roll_dice
from .rng import DiceSource

__all__ = ["CheckError", "morale_check", "surprise_check"]

SURPRISED_ON = 2  # a d6 result of 1 or 2


class CheckError(Exception):
    """Raised when a check is asked for with out-of-range inputs."""


def morale_check(score: int, dice: DiceSource, modifier: int = 0) -> dict:
    if not isinstance(score, int) or not 2 <= score <= 12:
        raise CheckError(f"morale score must be 2-12, got {score}")

    if score == 12:
        return {"score": 12, "checked": False, "holds": True,
                "result": "Morale 12 fights until killed; no check is made."}
    if score == 2:
        return {"score": 2, "checked": False, "holds": False,
                "result": "Morale 2 never fights unless absolutely cornered."}

    # Adjustments are never applied to monsters with a morale of 2 or 12.
    rolled = roll_dice(parse_dice("2d6"), dice)
    total = rolled["total"] + modifier
    holds = total <= score
    return {
        "score": score,
        "checked": True,
        "rolls": rolled["rolls"],
        "natural": rolled["total"],
        "modifier": modifier,
        "roll": total,
        "holds": holds,
        "result": ("Continues to fight." if holds
                   else "Surrenders or attempts to flee."),
    }


def surprise_check(dice: DiceSource) -> dict:
    roll = dice.roll(1, 6)
    return {
        "roll": roll,
        "surprised": roll <= SURPRISED_ON,
        "result": ("Surprised, loses one round." if roll <= SURPRISED_ON
                   else "Not surprised."),
    }
