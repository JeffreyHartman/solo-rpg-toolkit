"""Referee edits: a direct change to a party member or a monster when no procedure fits (ADR 0004).

An edit command is `{"type": "edit", "who", "change", "value", "reason"}`. `who` is a party
member's name or a monster id in the current fight. `change` is one of `CHANGES`:

  add_item, remove_item   one of the item `value` in `items`, a list of `{name, quantity}`
  light                   a party member lights the light source `value`; a ruleset plugin answers the
                          `light_requested` event and keeps the light. Refused for a monster.
  hp                      a change to `hp` such as "-3", "+2" or "-1d6"; the engine rolls any dice
  condition               add the condition `value` to `conditions`, a list of names
  clear_condition         remove the condition `value`

Each edit returns a mechanics card with the change and the reason, then one event that names the
change, for plugin triggers: `item_added`, `item_removed`, `light_requested`, `hp_changed`,
`condition_set` or `condition_cleared`.
"""
import re
from typing import Any

from ..dice import DiceError, parse_dice, roll_dice
from . import party
from .errors import IllegalActionError
from .registry import CommandContext, Event

__all__ = ["CHANGES", "LIGHT_REQUESTED", "edit", "edit_card", "remove_item"]

CHANGES = ("add_item", "remove_item", "light", "hp", "condition", "clear_condition")
EDIT_SOURCE = "Referee edit"
LIGHT_REQUESTED = "light_requested"
HP_CHANGE = re.compile(r"^([+-])\s*(\S+)$")


def edit(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    reason = str(command.get("reason") or "").strip()
    if not reason:
        raise IllegalActionError("an edit needs a reason")
    change = command.get("change")
    if change not in CHANGES:
        raise IllegalActionError(f"change must be one of {', '.join(CHANGES)}, got {change!r}")
    value = str(command.get("value") or "").strip()
    if not value:
        raise IllegalActionError("an edit needs a value")
    who, side, label = _subject(state, str(command.get("who") or ""))
    base = {"who": command["who"], "side": side}
    if change == "hp":
        return _hp(who, label, value, reason, base, ctx)
    if change == "light":
        if side != "member":
            raise IllegalActionError(f"only a party member can light a light source, not {label}")
        did = f"{label} lights a {value}"
        return [edit_card(did, reason), {"type": LIGHT_REQUESTED, **base, "item": value, "text": f"{did}."}]
    if change == "add_item":
        _add_item(who, value)
        did = f"{label} gains {value}"
        return [edit_card(did, reason), {"type": "item_added", **base, "item": value, "text": f"{did}."}]
    if change == "remove_item":
        remove_item(who, label, value)
        did = f"{label} loses {value}"
        return [edit_card(did, reason), {"type": "item_removed", **base, "item": value, "text": f"{did}."}]
    conditions = who.setdefault("conditions", [])
    if change == "condition":
        if value not in conditions:
            conditions.append(value)
        did = f"{label} is {value}"
        return [edit_card(did, reason), {"type": "condition_set", **base, "condition": value, "text": f"{did}."}]
    if value not in conditions:
        raise IllegalActionError(f"{label} is not {value}")
    conditions.remove(value)
    did = f"{label} is no longer {value}"
    return [edit_card(did, reason), {"type": "condition_cleared", **base, "condition": value, "text": f"{did}."}]


def _subject(state: dict[str, Any], who: str) -> tuple[dict[str, Any], str, str]:
    for member in state["party"]["members"]:
        if member["name"] == who:
            return member, "member", who
    for monster in (state.get("combat") or {}).get("monsters", []):
        if monster["id"] == who:
            return monster, "monster", party.monster_label(monster)
    raise IllegalActionError(f"no party member or monster '{who}'")


def _add_item(who: dict[str, Any], name: str) -> None:
    items = who.setdefault("items", [])
    held = next((i for i in items if i["name"] == name), None)
    if held:
        held["quantity"] += 1
    else:
        items.append({"name": name, "quantity": 1})


def remove_item(who: dict[str, Any], label: str, name: str) -> None:
    """Take one `name` from `who["items"]`, dropping the entry at 0. `label` names `who` in the error when none is held."""
    items = who.get("items", [])
    held = next((i for i in items if i["name"] == name), None)
    if held is None:
        raise IllegalActionError(f"{label} has no {name}")
    held["quantity"] -= 1
    if held["quantity"] <= 0:
        items.remove(held)


def _hp(who: dict[str, Any], label: str, value: str, reason: str, base: Event, ctx: CommandContext) -> list[Event]:
    match = HP_CHANGE.match(value)
    if not match:
        raise IllegalActionError(f"an hp change is a signed number or dice, such as -3 or +1d6, got {value!r}")
    sign = -1 if match.group(1) == "-" else 1
    amount_text = match.group(2)
    card: Event
    if amount_text.isdigit():
        amount = int(amount_text)
        card = edit_card(f"{label} {'loses' if sign < 0 else 'gains'} {amount} HP", reason)
    else:
        try:
            rolled = roll_dice(parse_dice(amount_text), ctx.dice)
        except DiceError as exc:
            raise IllegalActionError(str(exc)) from exc
        amount = rolled["total"]
        card = edit_card(f"{label} {'loses' if sign < 0 else 'gains'} {amount} HP", reason)
        card.update(dice=rolled["dice"], rolls=rolled["rolls"], total=amount)
    hp = who.get("hp", 0) + sign * amount
    top = who.get("max_hp")
    who["hp"] = max(0, min(hp, top) if top is not None else hp)
    return [card, {"type": "hp_changed", **base, "change": sign * amount, "hp": who["hp"],
                   "text": f"{label} has {who['hp']} HP."}]


def edit_card(did: str, reason: str) -> Event:
    """The mechanics card of a Referee edit with no roll: what changed and why."""
    return {"type": "mechanics", "procedure": "edit", "dice": "", "rolls": [], "total": None,
            "result": did, "source": EDIT_SOURCE, "reason": reason, "text": f"{did}. Reason: {reason}"}
