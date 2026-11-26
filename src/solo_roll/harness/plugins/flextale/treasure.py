"""FlexTale treasure: rolls the treasure tables and adds the result to `state["inventory"]`.

The inventory is `{"gp": int, "gems": {name: count}, "items": {name: count}}`. Coin amounts come from
the per-ruleset coin tables, one `NdM gp` slot per difficulty context.
"""
import re
from pathlib import Path
from typing import Any

from ....coins import parse_coin_slot
from ....rng import DiceSource
from ...errors import FlextaleDataError
from ...judgment import judgment_request
from ...registry import Action, CommandContext, Event, Registry
from .encounters import pending_combat
from .tabledata import CONTEXTS, card, context_letter, roll

__all__ = ["initial_inventory", "register", "treasure_actions"]

ITEM_TABLES = {"potion": "potion-{c}", "mundane": "mundane-items-{c}", "armor": "armor-{c}", "weapon": "weapon-{c}"}
LEVELS = ("low", "medium", "high")
MAX_DEPTH = 2
MAX_REROLLS = 10


def initial_inventory(_state: dict[str, Any]) -> dict[str, Any]:
    return {"gp": 0, "gems": {}, "items": {}}


def register(registry: Registry, data_dir: Path, ruleset: str) -> None:
    registry.add_state_default("inventory", initial_inventory)
    registry.add_judgment_category("treasure", "Treasure choices the book leaves to the player")
    registry.add_procedure("treasure", _treasure(data_dir, ruleset), label="Collect treasure")
    registry.add_action_provider(treasure_actions)


def treasure_actions(state: dict[str, Any]) -> list[Action]:
    current = state.get("encounter", {}).get("current") or {}
    waiting = any(o["kind"] == "treasure" and o["status"] == "pending" for o in current.get("outcomes", []))
    if not waiting or pending_combat(state) or state.get("combat"):
        return []
    return [{"id": "treasure", "label": "Collect the treasure", "command": {"type": "procedure", "name": "treasure"}}]


def _treasure(data_dir: Path, ruleset: str):
    def run(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
        events: list[Event] = []
        notes: list[str] = []
        if "judgment" in command:
            gain = command["judgment"]["data"]["gain"]
            _settle(gain, command["judgment"]["answer"])
        else:
            gain = _draw(data_dir, context_letter(ctx.settings), ruleset, ctx.dice, events, notes, 0)
            for outcome in (state.get("encounter", {}).get("current") or {}).get("outcomes", []):
                if outcome["kind"] == "treasure" and outcome["status"] == "pending":
                    outcome["status"] = "resolved"
                    break
        if gain["choices"]:
            first, second = gain["choices"][0]
            options = [f"First draw: {_describe(first)}", f"Second draw: {_describe(second)}"]
            events.append(
                judgment_request(
                    "treasure",
                    "Favorable Treasure: which draw does the party keep?",
                    suggestion=options[0] if first["first"] >= second["first"] else options[1],
                    reason="The draw with the higher first roll is the better treasure.",
                    options=options,
                    data={"gain": gain},
                )
            )
            return events
        inventory = state["inventory"]
        inventory["gp"] += gain["gp"]
        for key in ("gems", "items"):
            for name, count in gain[key].items():
                inventory[key][name] = inventory[key].get(name, 0) + count
        events.append({"type": "treasure", "gain": gain, "text": f"Treasure: {_describe(gain)}." + "".join(f" {n}" for n in notes)})
        return events

    return run


def _describe(gain: dict[str, Any]) -> str:
    parts = [f"{gain['gp']} gp"] if gain["gp"] else []
    parts += [f"{n} x {name}" if n != 1 or name in gain["gems"] else name for name, n in {**gain["gems"], **gain["items"]}.items()]
    return ", ".join(parts) if parts else "nothing"


def _settle(gain: dict[str, Any], answer: str) -> None:
    """Replace the first open Favorable choice of `gain` with the draw the answer names."""
    first, second = gain["choices"].pop(0)
    _merge(gain, first if answer.startswith("First draw") else second)


def _empty() -> dict[str, Any]:
    return {"gp": 0, "gems": {}, "items": {}, "first": 0, "choices": []}


def _merge(into: dict[str, Any], other: dict[str, Any]) -> None:
    into["gp"] += other["gp"]
    into["choices"].extend(other["choices"])
    for key in ("gems", "items"):
        for name, count in other[key].items():
            into[key][name] = into[key].get(name, 0) + count


def _draw(data_dir, letter, ruleset, dice, events, notes, depth) -> dict[str, Any]:
    """Roll the treasure table until a result gives something, and return what it gives."""
    for _ in range(MAX_REROLLS):
        rolled = roll(data_dir, f"treasure-{letter}", dice)
        events.append(card("treasure", rolled, "Treasure"))
        low = rolled["result"].strip().lower()
        gain = _empty()
        gain["first"] = rolled["roll"]
        if low.startswith("contact poison"):
            notes.append("The treasure carries a contact poison.")
            continue
        if low.startswith("no treasure"):
            return gain
        if low.startswith(("additional treasure", "favorable treasure")):
            if depth >= MAX_DEPTH:
                continue
            first = _draw(data_dir, letter, ruleset, dice, events, notes, depth + 1)
            second = _draw(data_dir, letter, ruleset, dice, events, notes, depth + 1)
            if low.startswith("additional"):
                _merge(gain, first)
                _merge(gain, second)
            else:
                gain["choices"].append([first, second])
            return gain
        _resolve(low, rolled["result"], data_dir, letter, ruleset, dice, events, gain)
        return gain
    raise FlextaleDataError(f"table treasure-{letter} kept asking for a reroll")


def _resolve(low, text, data_dir, letter, ruleset, dice, events, gain) -> None:
    for level in LEVELS:
        if low.startswith(f"{level} coin"):
            rolled = roll(data_dir, f"treasure-{level}-coin-{letter}-{ruleset}", dice)
            events.append(card("treasure", rolled, "Coins"))
            gain["gp"] += _coins(rolled["result"], CONTEXTS.index(letter.upper()), dice, rolled["table"])
            return
        if low.startswith(f"{level} gem"):
            rolled = roll(data_dir, f"treasure-{level}-gem-{letter}-{ruleset}", dice)
            events.append(card("treasure", rolled, "Gems"))
            name = rolled["result"].split(":")[0].strip() or "Gem"
            gain["gems"][name] = _gem_count(rolled["result"], dice)
            return
    for prefix, table in ITEM_TABLES.items():
        if low.startswith(prefix):
            rolled = roll(data_dir, table.format(c=letter), dice)
            events.append(card("treasure", rolled, "Item"))
            gain["items"][_name(rolled["result"])] = 1
            return
    gain["items"][_name(text)] = 1


def _name(text: str) -> str:
    return re.split(r"[:(]", text.strip())[0].strip()[:60] or "Item"


def _coins(result: str, index: int, dice: DiceSource, table: str) -> int:
    slot = parse_coin_slot(result, index)
    if slot is None:
        raise FlextaleDataError(f"cannot read the coin amount for this difficulty context in table {table}")
    count, sides, factor = slot
    return sum(dice.roll(1, sides) for _ in range(count)) * factor


def _gem_count(result: str, dice: DiceSource) -> int:
    match = re.search(r"(\d+)d(\d+)\s*x", result)
    if match is None:
        return 1
    return sum(dice.roll(1, int(match.group(2))) for _ in range(int(match.group(1))))
