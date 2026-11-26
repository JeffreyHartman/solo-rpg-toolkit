"""FlexTale encounters: what a new area holds, the DC for its traps and obstacles, and backtracking.

State lives in `state["encounter"]`:
`current` is `{area, table, source, outcomes}` for the latest encounter roll or None. Each outcome is
`{kind, roll, result, status, detail, dc, edge}`. `kind` is none, trap, obstacle, secret, combat or
treasure. `status` is "noted" (nothing to resolve), "open" (a trap or obstacle waiting for a check),
"resolved", "failed", or "pending" (a combat or treasure that another procedure starts).
`visited` lists the areas the party has left or entered, and `backtracks` counts moves into them.
"""
import re
from pathlib import Path
from typing import Any

from ....rng import DiceSource
from ...errors import FlextaleDataError
from ...playerview import visible_outcomes
from ...registry import Event
from .tabledata import card, context_letter, roll

__all__ = [
    "BACKTRACK_INTERVAL",
    "area_table",
    "backtrack_trigger",
    "initial_encounter",
    "pending_combat",
    "reveal_trigger",
    "rest_trigger",
]

BACKTRACK_INTERVAL = 4
"""FlexTale re-rolls a random encounter on every fourth move into an area the party already knows."""

DETAIL_TABLES = {
    "trap": "trap-{c}-{system}",
    "obstacle": "obstacle-{c}",
    "secret": "secret-door-{c}",
    "combat": "combat-encounter-{c}",
}
KIND_PREFIXES = [("trap", "trap"), ("obstacle", "obstacle"), ("secret", "secret"), ("combat", "combat")]
MAX_REROLLS = 10
HIDDEN_KINDS = ("trap", "secret")
"""Outcome kinds the player has not found when they are rolled."""


def initial_encounter(_state: dict[str, Any]) -> dict[str, Any]:
    return {"current": None, "visited": [], "backtracks": 0}


def area_table(kind: str) -> str:
    return {"chamber": "chamber-encounter-{c}", "dead-end": "dead-end-encounter-{c}"}.get(kind, "hallway-encounter-{c}")


def pending_combat(state: dict[str, Any]) -> dict[str, Any] | None:
    """The first combat outcome of the current encounter that no combat has started from, or None."""
    current = state.get("encounter", {}).get("current")
    for outcome in (current or {}).get("outcomes", []):
        if outcome["kind"] == "combat" and outcome["status"] == "pending":
            return outcome
    return None


def reveal_trigger(data_dir: Path, system: str):
    def trigger(state: dict[str, Any], event: Event, ctx) -> list[Event]:
        area = state["map"]["areas"][event["area"]]
        if "kind" not in area:
            return []
        return roll_encounter(state, event["area"], data_dir, system, ctx, "new area")

    return trigger


def backtrack_trigger(data_dir: Path, system: str):
    def trigger(state: dict[str, Any], event: Event, ctx) -> list[Event]:
        enc = state["encounter"]
        visited = enc["visited"]
        if event["from"] not in visited:
            visited.append(event["from"])
        if event["to"] not in visited:
            visited.append(event["to"])
            return []
        enc["backtracks"] += 1
        if enc["backtracks"] % BACKTRACK_INTERVAL:
            return []
        return roll_encounter(state, event["to"], data_dir, system, ctx, "backtracking")

    return trigger


def rest_trigger(data_dir: Path, system: str):
    """The QuickStart rest rule: a rest rolls the encounter table of the area the party is in."""
    def trigger(state: dict[str, Any], event: Event, ctx) -> list[Event]:
        if not event.get("rested"):
            return []
        return roll_encounter(state, state["party"]["area"], data_dir, system, ctx, "rest")

    return trigger


def roll_encounter(
    state: dict[str, Any], area_id: str, data_dir: Path, system: str, ctx, source: str
) -> list[Event]:
    """Roll the encounter table of the area's kind, store the outcomes, and return the events."""
    letter = context_letter(ctx.settings)
    area = state["map"]["areas"][area_id]
    table = area_table(area.get("kind", "hall")).format(c=letter)
    events: list[Event] = []
    outcomes: list[dict[str, Any]] = []
    for kind, rolled in _draw(data_dir, table, ctx.dice, events):
        outcomes.extend(_outcomes(kind, rolled, data_dir, letter, system, ctx.dice, events))
    state["encounter"]["current"] = {
        "area": area_id, "table": f"quickstart/{table}", "source": source, "outcomes": outcomes,
    }
    name = area["name"]
    summary = ", ".join(o["kind"] for o in visible_outcomes(outcomes)) or "nothing obvious"
    events.append(
        {
            "type": "encounter", "area": area_id, "source": source, "outcomes": outcomes,
            "text": f"Encounter in {name} ({source}): {summary}.",
        }
    )
    for index, outcome in enumerate(outcomes):
        if outcome["kind"] == "combat":
            events.append(
                {
                    "type": "combat_encounter", "area": area_id, "outcome": index,
                    "monsters": outcome["detail"]["result"],
                    "text": f"Combat in {name}: {outcome['detail']['result']}",
                }
            )
    return events


def classify(text: str) -> str:
    low = text.strip().lower()
    if low.startswith("no encounter"):
        return "none"
    if low.startswith("combat and treasure"):
        return "combat+treasure"
    if low.startswith("roll twice"):
        return "twice"
    for prefix, kind in KIND_PREFIXES:
        if low.startswith(prefix):
            return kind
    raise FlextaleDataError(f"cannot tell what the encounter result '{text[:40]}' means")


def _draw(data_dir: Path, table: str, dice: DiceSource, events: list[Event]):
    """Yield `(kind, rolled)` for one table roll; a Roll Twice result yields two plain rolls instead."""
    rolled = roll(data_dir, table, dice)
    kind = classify(rolled["result"])
    events.append(_card_for(kind, card("encounter", rolled, "Encounter")))
    if kind != "twice":
        yield kind, rolled
        return
    for _ in range(2):
        for _attempt in range(MAX_REROLLS):
            again = roll(data_dir, table, dice)
            again_kind = classify(again["result"])
            events.append(_card_for(again_kind, card("encounter", again, "Encounter")))
            if again_kind != "twice":
                yield again_kind, again
                break
        else:
            raise FlextaleDataError(f"table {table} kept rolling Roll Twice")


def _outcomes(kind, rolled, data_dir, letter, system, dice, events) -> list[dict[str, Any]]:
    base = {"roll": rolled["roll"], "result": rolled["result"], "detail": None, "dc": None, "edge": 0}
    if kind == "none":
        return [{**base, "kind": "none", "status": "noted"}]
    if kind == "combat+treasure":
        combat = _detailed("combat", base, data_dir, letter, system, dice, events)
        return [combat, {**base, "kind": "treasure", "status": "pending"}]
    return [_detailed(kind, base, data_dir, letter, system, dice, events)]


def _card_for(kind: str, event: Event) -> Event:
    """Flag a card of a trap or secret so the browser does not show it."""
    return {**event, "hidden": True} if kind in HIDDEN_KINDS else event


def _detailed(kind, base, data_dir, letter, system, dice, events) -> dict[str, Any]:
    first_card = len(events)
    outcome = _detail_outcome(kind, base, data_dir, letter, system, dice, events)
    if outcome["kind"] in HIDDEN_KINDS:
        outcome["hidden"] = True
        events[first_card:] = [{**e, "hidden": True} for e in events[first_card:]]
    return outcome


def _detail_outcome(kind, base, data_dir, letter, system, dice, events) -> dict[str, Any]:
    edge = 0
    for _ in range(MAX_REROLLS):
        table = DETAIL_TABLES[kind].format(c=letter, system=system)
        rolled = roll(data_dir, table, dice)
        events.append(card("encounter", rolled, kind.capitalize()))
        text = rolled["result"]
        if kind == "trap" and text.lower().startswith("monster"):
            via = _detail(rolled)
            outcome = _detailed("combat", base, data_dir, letter, system, dice, events)
            outcome["via"] = via
            return outcome
        if re.match(r"^[^:]*:\s*reroll", text, re.IGNORECASE):
            edge += _edge_of(text)
            continue
        break
    else:
        raise FlextaleDataError(f"table {table} kept asking for a reroll")
    outcome = {**base, "kind": kind, "detail": _detail(rolled), "edge": edge}
    if kind in ("trap", "obstacle"):
        outcome["status"] = "open"
        outcome["dc"] = _roll_dc(data_dir, letter, system, dice, events)
        outcome["edge"] = max(-1, min(1, edge + outcome["dc"]["edge"]))
    elif kind == "combat":
        outcome["status"] = "pending"
    else:
        outcome["status"] = "noted"
    return outcome


def _detail(rolled: dict[str, Any]) -> dict[str, Any]:
    return {"table": rolled["table"], "roll": rolled["roll"], "result": rolled["result"]}


def _edge_of(text: str) -> int:
    if "disadvantage" in text.lower():
        return -1
    return 1 if "advantage" in text.lower() else 0


def _roll_dc(data_dir, letter, system, dice, events) -> dict[str, Any]:
    """Roll the DC table for a trap or obstacle: a modifier added to the d20, plus an advantage edge."""
    table = f"difficulty-class-{letter}-{system}"
    edge = 0
    for _ in range(MAX_REROLLS):
        rolled = roll(data_dir, table, dice)
        events.append(card("difficulty-class", rolled, "DC"))
        text = rolled["result"].strip()
        low = text.lower()
        if low.startswith(("susceptible", "resistant")):
            edge += -1 if low.startswith("susceptible") else 1
            continue
        match = re.search(r"([+-])\s*(\d+)\s+on roll", text)
        if match:
            modifier = int(match.group(2)) * (1 if match.group(1) == "+" else -1)
        elif low.startswith("normal"):
            modifier = 0
        else:
            raise FlextaleDataError(f"cannot read the DC result '{text[:40]}' of table {rolled['table']}")
        return {"table": rolled["table"], "roll": rolled["roll"], "result": text[:60], "modifier": modifier, "edge": edge}
    raise FlextaleDataError(f"table {table} kept asking for a reroll")
