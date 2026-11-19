import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .rng import DiceSource


# The highest yes threshold. The book's chart prints "20 99 x" for it.
MAX_YES_THRESHOLD = 99
EXCEPTIONAL_YES_CAP_AT_99 = 20
# One above the d100 range, so no roll is an Exceptional No.
EXCEPTIONAL_NO_FLOOR_NEVER = 101


@dataclass(frozen=True)
class Thresholds:
    yes_threshold: int
    exceptional_yes_cap: int
    exceptional_no_floor: int


def thresholds(yes_threshold: int) -> Thresholds:
    if not (1 <= yes_threshold <= 99):
        raise ValueError(f"yes_threshold out of range: {yes_threshold}")
    if yes_threshold == MAX_YES_THRESHOLD:
        return Thresholds(yes_threshold, EXCEPTIONAL_YES_CAP_AT_99,
                          EXCEPTIONAL_NO_FLOOR_NEVER)
    exc_yes = yes_threshold // 5
    exc_no = 101 - math.ceil((100 - yes_threshold) / 5)
    return Thresholds(
        yes_threshold=yes_threshold,
        exceptional_yes_cap=exc_yes,
        exceptional_no_floor=exc_no,
    )


def read_d100(d1: int, d2: int) -> int:
    for d in (d1, d2):
        if not (0 <= d <= 9):
            raise ValueError(f"d10 face out of range [0,9]: {d}")
    if d1 == 0 and d2 == 0:
        return 100
    return d1 * 10 + d2


def classify_outcome(roll: int, t: Thresholds) -> tuple[str, bool]:
    """Returns (outcome, is_exceptional)."""
    if roll <= t.exceptional_yes_cap:
        return "exceptional_yes", True
    if roll <= t.yes_threshold:
        return "yes", False
    if roll >= t.exceptional_no_floor:
        return "exceptional_no", True
    return "no", False


def is_random_event(d1: int, d2: int, cf: int) -> bool:
    return d1 == d2 and 1 <= d1 <= cf


KnownLikelihood = frozenset({
    "certain", "nearly_certain", "very_likely", "likely",
    "50_50", "unlikely", "very_unlikely", "nearly_impossible", "impossible",
})


class FateChartError(Exception):
    """Raised when fate-chart loading or lookup fails."""


@dataclass(frozen=True)
class FateChart:
    likelihoods: tuple[str, ...]
    thresholds: dict[str, tuple[int, ...]]


def load_fate_chart(data_dir: Path) -> FateChart:
    path = data_dir / "charts" / "mythic-fate.json"
    if not path.exists():
        raise FateChartError(f"Fate chart not found: {path}")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise FateChartError(f"Invalid JSON in {path}: {exc}") from exc

    likelihoods = tuple(payload.get("likelihoods", []))
    if set(likelihoods) != KnownLikelihood:
        raise FateChartError(f"{path}: likelihoods do not match known set")

    raw_thresholds = payload.get("thresholds", {})
    thresholds_out: dict[str, tuple[int, ...]] = {}
    for key in likelihoods:
        row = raw_thresholds.get(key)
        if not isinstance(row, list) or len(row) != 9:
            raise FateChartError(f"{path}: thresholds[{key}] must be list of 9 ints")
        for value in row:
            if not isinstance(value, int) or not (1 <= value <= 99):
                raise FateChartError(f"{path}: threshold {value} out of range for {key}")
        thresholds_out[key] = tuple(row)

    return FateChart(likelihoods=likelihoods, thresholds=thresholds_out)


def fate_check(
    likelihood: str,
    cf: int,
    chart: FateChart,
    dice: DiceSource,
) -> dict[str, Any]:
    if likelihood not in chart.thresholds:
        raise FateChartError(f"Unknown likelihood: {likelihood}")
    if not (1 <= cf <= 9):
        raise FateChartError(f"CF out of range [1,9]: {cf}")

    yes_threshold = chart.thresholds[likelihood][cf - 1]
    t = thresholds(yes_threshold)

    d1 = dice.roll(0, 9)
    d2 = dice.roll(0, 9)
    roll = read_d100(d1, d2)
    outcome, is_exc = classify_outcome(roll, t)
    event = is_random_event(d1, d2, cf)

    return {
        "likelihood": likelihood,
        "cf": cf,
        "yes_threshold": t.yes_threshold,
        "exceptional_yes_cap": t.exceptional_yes_cap,
        "exceptional_no_floor": t.exceptional_no_floor,
        "dice": [d1, d2],
        "roll": roll,
        "outcome": outcome,
        "exceptional": is_exc,
        "random_event_triggered": event,
    }
