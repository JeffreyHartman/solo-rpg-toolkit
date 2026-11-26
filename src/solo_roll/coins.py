"""Reads one context slot of a FlexTale coin-table result."""
import re

_AMOUNT = re.compile(r"(\d+)d(\d+)(?:\s*x\s*(\d+)(k?))?(?:\s*gp)?")


def parse_coin_slot(result: str, index: int) -> tuple[int, int, int] | None:
    """Returns `(dice count, sides, factor)` for slot `index` of a `/`-separated result, or None if it has none or cannot be read."""
    slots = [s.strip() for s in result.split("/")]
    if index >= len(slots):
        return None
    match = _AMOUNT.fullmatch(slots[index])
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 1) * (1000 if match.group(4) else 1)
