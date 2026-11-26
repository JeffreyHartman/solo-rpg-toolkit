"""What the browser may see: the engine state and events without the secrets the Referee keeps.

An encounter outcome with `hidden: True` (an unfound trap or a secret) and an event with `hidden: True`
stay in engine state and in what the Referee reads. Areas with `known: False` are not shown.
"""
import copy
from typing import Any

from .registry import Event

__all__ = ["player_events", "player_state", "visible_outcomes"]


def visible_outcomes(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [o for o in outcomes if not o.get("hidden")]


def player_state(state: dict[str, Any]) -> dict[str, Any]:
    """A copy of `state` for the player."""
    shown = copy.deepcopy(state)
    current = shown.get("encounter", {}).get("current")
    if current:
        current["outcomes"] = visible_outcomes(current["outcomes"])
    if "map" in shown:
        areas = {k: a for k, a in shown["map"]["areas"].items() if a.get("known", True)}
        shown["map"]["areas"] = areas
        shown["map"]["connections"] = [
            c for c in shown["map"].get("connections", []) if c["a"] in areas and c["b"] in areas
        ]
        if "open_exits" in shown["map"]:
            shown["map"]["open_exits"] = [e for e in shown["map"]["open_exits"] if e["area"] in areas]
    return shown


def player_events(events: list[Event]) -> list[Event]:
    """`events` without the hidden ones, and without hidden outcomes inside the rest."""
    shown = []
    for event in events:
        if event.get("hidden"):
            continue
        if "outcomes" in event:
            event = {**event, "outcomes": visible_outcomes(event["outcomes"])}
        shown.append(event)
    return shown
