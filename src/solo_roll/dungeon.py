"""The OSE dungeon turn: clock, light, rest, and the wandering monster check.

The whole turn is one call so that an agent cannot run half of it. Skipping the
light decrement or the wandering check is the documented failure mode of leaving
a multi-step procedure in prose.
"""
import json
from pathlib import Path
from typing import Any

from .dice import parse_dice, roll_dice
from .rng import DiceSource
from .tables import roll_table

__all__ = [
    "DungeonError",
    "advance_clock",
    "advance_turn",
    "check_wandering",
    "load_state",
    "new_state",
    "save_state",
]

TURNS_BETWEEN_RESTS = 6  # one turn of rest every hour
ENCOUNTER_DISTANCE = "2d6"
SURPRISED_ON = 2  # a d6 result of 1 or 2 surprises that side


class DungeonError(Exception):
    """Raised when dungeon state cannot be read or written."""


def new_state(level: int = 1) -> dict[str, Any]:
    return {
        "turn": 0,
        "level": level,
        "room": None,
        "light": [],
        "turns_since_rest": 0,
        "wandering": None,
    }


def load_state(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise DungeonError(f"dungeon state not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise DungeonError(f"invalid JSON in {path}: {exc}") from exc


def save_state(path: Path, state: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def advance_turn(
    state: dict[str, Any], data_dir: Path, dice: DiceSource, rest: bool = False
) -> dict[str, Any]:
    """Advance one turn. With rest set, the turn is spent resting and
    turns_since_rest goes back to 0."""
    payload = advance_clock(state, rest=rest)
    payload["wandering"] = check_wandering(payload["state"], data_dir, dice)
    return payload


def advance_clock(state: dict[str, Any], rest: bool = False) -> dict[str, Any]:
    """Advance the turn counter and burn the light, without the wandering check."""
    state = json.loads(json.dumps(state))  # do not mutate the caller's dict
    state["turn"] = state.get("turn", 0) + 1
    state["turns_since_rest"] = 0 if rest else state.get("turns_since_rest", 0) + 1

    burning, expired = [], []
    for source in state.get("light") or []:
        source = dict(source)
        turns_left = source.get("turns_left")
        if not isinstance(turns_left, int) or isinstance(turns_left, bool):
            raise DungeonError(
                f"light source {source!r} needs an integer turns_left "
                '(for example {"kind": "torch", "bearer": "Hana", "turns_left": 6})'
            )
        source["turns_left"] = turns_left - 1
        if source["turns_left"] > 0:
            burning.append(source)
        else:
            expired.append({"kind": source.get("kind"), "bearer": source.get("bearer")})
    state["light"] = burning

    return {
        "turn": state["turn"],
        "level": state.get("level"),
        "room": state.get("room"),
        "light_expired": expired,
        "in_darkness": not burning,
        "rested": rest,
        "rest_due": state["turns_since_rest"] >= TURNS_BETWEEN_RESTS,
        "state": state,
    }


def check_wandering(
    state: dict[str, Any], data_dir: Path, dice: DiceSource
) -> dict[str, Any]:
    config = state.get("wandering")
    if not config:
        return {"checked": False, "reason": "no wandering table on this level"}

    table = config.get("table", config.get("wandering_table"))
    if not table:
        raise DungeonError(
            'wandering config in state/clock.json needs a "table" '
            '(for example {"table": "ose/my-level-1", "interval": 2})'
        )

    interval = int(config.get("interval", config.get("wandering_interval_turns", 2)))
    if interval < 1 or state["turn"] % interval != 0:
        return {"checked": False, "reason": f"checked every {interval} turns"}

    die = int(config.get("die", 6))
    chance = int(config.get("chance", 1))
    check = dice.roll(1, die)
    report: dict[str, Any] = {
        "checked": True,
        "check": {"roll": check, "needs": f"{chance}-in-{die}"},
        "encounter": check <= chance,
    }
    if not report["encounter"]:
        return report

    report["monster"] = roll_table(table, data_dir, dice)
    distance = roll_dice(parse_dice(ENCOUNTER_DISTANCE), dice)
    report["distance_feet"] = distance["total"] * 10
    report["surprise"] = {
        "party": dice.roll(1, 6) <= SURPRISED_ON,
        "monsters": dice.roll(1, 6) <= SURPRISED_ON,
    }
    reaction = config.get("reaction_table", "ose/reaction")
    report["reaction"] = roll_table(reaction, data_dir, dice)
    return report
