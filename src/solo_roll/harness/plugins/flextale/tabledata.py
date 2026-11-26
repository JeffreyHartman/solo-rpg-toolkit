"""Rolls FlexTale tables from the imported data folder and turns a missing table into `FlextaleDataError`."""
from pathlib import Path
from typing import Any

from ....rng import DiceSource
from ....tables import TableNotFoundError, roll_table
from ...errors import FlextaleDataError
from ...registry import Event

__all__ = ["CONTEXTS", "card", "context_letter", "roll"]

CONTEXTS = ["A", "B", "C", "D"]


def roll(data_dir: Path, name: str, dice: DiceSource) -> dict[str, Any]:
    """Roll `quickstart/<name>`. A table the importer did not write raises `FlextaleDataError`."""
    try:
        return roll_table(f"quickstart/{name}", data_dir, dice)
    except TableNotFoundError as exc:
        raise FlextaleDataError(
            f"FlexTale table quickstart/{name} not found in {data_dir}; run `solo-flextale-import <pdf>`. "
            "The importer skips a table whose book ranges are wrong; correct it in overrides.json and import again."
        ) from exc


def context_letter(settings: Any) -> str:
    """The campaign's difficulty context as a lowercase table suffix."""
    value = settings.get("difficulty", "context", "A") if settings is not None else "A"
    return value.lower()


def card(procedure: str, rolled: dict[str, Any], label: str) -> Event:
    """A mechanics card for one table roll."""
    return {
        "type": "mechanics",
        "text": f"{label}: rolled {rolled['roll']} on {rolled['dice']}: {rolled['result']}",
        "procedure": procedure,
        "dice": rolled["dice"],
        "rolls": rolled["rolls"],
        "total": rolled["roll"],
        "result": rolled["result"],
        "source": f"table {rolled['table']}",
    }
