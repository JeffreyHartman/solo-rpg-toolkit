import json
from pathlib import Path
from typing import Any

from .rng import DiceSource
from .tables import TableError, roll_table


class QuicksetError(Exception):
    """Base error for quicksets module."""


class QuicksetNotFoundError(QuicksetError):
    pass


class QuicksetDataError(QuicksetError):
    pass


def _quickset_path(qs_id: str, data_dir: Path) -> Path:
    return data_dir / "quicksets" / f"{qs_id}.json"


def load_quickset(qs_id: str, data_dir: Path) -> dict[str, Any]:
    path = _quickset_path(qs_id, data_dir)
    if not path.exists():
        raise QuicksetNotFoundError(f"Quickset not found: {qs_id} (looked in {path})")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise QuicksetDataError(f"Invalid JSON in {path}: {exc}") from exc
    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        raise QuicksetDataError(f"{path}: 'steps' must be a non-empty list")
    for idx, step in enumerate(steps):
        if not isinstance(step, dict) or "label" not in step or "table" not in step:
            raise QuicksetDataError(f"{path}: step {idx} missing label/table")
    return payload


def run_quickset(qs_id: str, data_dir: Path, dice: DiceSource) -> dict[str, Any]:
    qs = load_quickset(qs_id, data_dir)
    results = []
    for step in qs["steps"]:
        try:
            rolled = roll_table(step["table"], data_dir, dice)
        except TableError as exc:
            raise QuicksetDataError(f"quickset {qs_id}: {exc}") from exc
        results.append({
            "label": step["label"],
            "table": step["table"],
            "roll": rolled["roll"],
            "result": rolled["result"],
        })
    return {
        "id": qs["id"],
        "name": qs["name"],
        "steps": results,
    }
