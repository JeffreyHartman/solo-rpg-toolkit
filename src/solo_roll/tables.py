import json
from pathlib import Path
from typing import Any

from .rng import DiceSource


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

    dice = payload.get("dice")
    if dice not in DICE_FACES:
        raise TableDataError(f"{path}: unknown dice '{dice}'")
    faces = DICE_FACES[dice]

    has_entries = "entries" in payload
    has_ranges = "ranges" in payload
    if has_entries and has_ranges:
        raise TableDataError(f"{path}: both 'entries' and 'ranges' present")
    if not has_entries and not has_ranges:
        raise TableDataError(f"{path}: neither 'entries' nor 'ranges' present")

    if has_entries:
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
        if low > high or low < 1 or high > faces:
            raise TableDataError(f"{path}: range {low}-{high} invalid for {dice}")
        for value in range(low, high + 1):
            if value in covered:
                raise TableDataError(f"{path}: range value {value} overlaps")
            covered.add(value)
    missing = set(range(1, faces + 1)) - covered
    if missing:
        raise TableDataError(f"{path}: ranges do not cover {sorted(missing)}")


def roll_table(name: str, data_dir: Path, dice: DiceSource) -> dict[str, Any]:
    table = load_table(name, data_dir)
    faces = DICE_FACES[table["dice"]]
    roll = dice.roll(1, faces)

    if "entries" in table:
        result = table["entries"][roll - 1]
    else:
        result = _lookup_range(table["ranges"], roll)

    return {
        "table": name,
        "display_name": table.get("display_name", table["name"]),
        "dice": table["dice"],
        "roll": roll,
        "result": result,
    }


def _lookup_range(ranges: list[dict[str, Any]], roll: int) -> str:
    for band in ranges:
        if band["min"] <= roll <= band["max"]:
            return band["result"]
    raise TableDataError(f"roll {roll} not covered by ranges (loader should have rejected)")
