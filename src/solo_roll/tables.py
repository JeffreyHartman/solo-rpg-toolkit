import json
from pathlib import Path
from typing import Any

from .dice import DiceError, parse_dice, roll_dice
from .rng import DiceSource


# Single-die shorthands kept for the tables that already ship. Any NdN notation
# parses, so a 2d6 reaction or morale table needs no code change.
DICE_FACES: dict[str, int] = {
    "d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100,
}


class TableError(Exception):
    """Base error for table module."""


class TableNotFoundError(TableError):
    """Raised when a table name cannot be resolved to a file."""


class TableDataError(TableError):
    """Raised when a table file's contents violate the schema."""


def _table_path(name: str, data_dir: Path) -> Path:
    return data_dir / "tables" / f"{name}.json"


def load_table(name: str, data_dir: Path) -> dict[str, Any]:
    path = _table_path(name, data_dir)
    if not path.exists():
        raise TableNotFoundError(f"Table not found: {name} (looked in {path})")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise TableDataError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise TableDataError(f"{path}: expected a JSON object, got {type(payload).__name__}")

    _validate(payload, path)
    return payload


def _validate(payload: dict[str, Any], path: Path) -> None:
    if not isinstance(payload.get("name"), str):
        raise TableDataError(f"{path}: 'name' must be a non-empty string")

    if "description" in payload and not isinstance(payload["description"], str):
        raise TableDataError(f"{path}: 'description' must be a string when present")

    dice = payload.get("dice")
    if not isinstance(dice, str):
        raise TableDataError(f"{path}: 'dice' must be a string, got {type(dice).__name__}")
    try:
        spec = parse_dice(dice)
    except DiceError as exc:
        raise TableDataError(f"{path}: {exc}") from exc
    faces = spec.maximum

    has_entries = "entries" in payload
    has_ranges = "ranges" in payload
    if has_entries and has_ranges:
        raise TableDataError(f"{path}: both 'entries' and 'ranges' present")
    if not has_entries and not has_ranges:
        raise TableDataError(f"{path}: neither 'entries' nor 'ranges' present")

    if has_entries:
        if spec.count != 1:
            raise TableDataError(
                f"{path}: flat 'entries' need a single die; {dice} is not uniform, use 'ranges'"
            )
        entries = payload["entries"]
        if not isinstance(entries, list) or len(entries) != faces:
            raise TableDataError(
                f"{path}: expected {faces} entries for {dice}, got {len(entries) if isinstance(entries, list) else type(entries).__name__}"
            )
        return

    # Ranged — validate coverage.
    ranges = payload["ranges"]
    if not isinstance(ranges, list) or not ranges:
        raise TableDataError(f"{path}: ranges must be a non-empty list")
    covered: set[int] = set()
    for band in ranges:
        low = band.get("min")
        high = band.get("max")
        if not isinstance(low, int) or not isinstance(high, int):
            raise TableDataError(f"{path}: range min/max must be ints")
        if "result" not in band or not isinstance(band["result"], str):
            raise TableDataError(f"{path}: range band missing or non-string 'result'")
        if low > high:
            raise TableDataError(f"{path}: range {low}-{high} invalid for {dice}")
        # Bands may extend past the natural range so that a modifier still lands
        # somewhere, so only the reachable values are checked for overlap.
        for value in range(max(low, spec.minimum), min(high, spec.maximum) + 1):
            if value in covered:
                raise TableDataError(f"{path}: range value {value} overlaps")
            covered.add(value)
    missing = set(range(spec.minimum, spec.maximum + 1)) - covered
    if missing:
        raise TableDataError(f"{path}: ranges do not cover {sorted(missing)}")


def roll_table(
    name: str, data_dir: Path, dice: DiceSource, modifier: int = 0
) -> dict[str, Any]:
    table = load_table(name, data_dir)
    spec = parse_dice(table["dice"])
    rolled = roll_dice(spec, dice)
    natural = rolled["total"]
    total = natural + modifier

    if "entries" in table:
        index = min(max(total, spec.minimum), spec.maximum)
        result = table["entries"][index - 1]
    else:
        result = _lookup_range(table["ranges"], total)

    return {
        "table": name,
        "display_name": table.get("display_name", table["name"]),
        "dice": table["dice"],
        "rolls": rolled["rolls"],
        "natural": natural,
        "modifier": modifier,
        "roll": total,
        "result": result,
    }


def _lookup_range(ranges: list[dict[str, Any]], roll: int) -> str:
    for band in ranges:
        if band["min"] <= roll <= band["max"]:
            return band["result"]
    # A modifier can carry the total past the outermost band, so clamp to it.
    lowest = min(ranges, key=lambda b: b["min"])
    highest = max(ranges, key=lambda b: b["max"])
    return lowest["result"] if roll < lowest["min"] else highest["result"]
