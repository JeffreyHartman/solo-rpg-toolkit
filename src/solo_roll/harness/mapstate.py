"""Reads and changes on the map part of the engine state, shared by plugins."""
from typing import Any

__all__ = ["area", "exits"]


def area(state: dict[str, Any], area_id: str) -> dict[str, Any] | None:
    return state["map"]["areas"].get(area_id)


def exits(state: dict[str, Any], area_id: str) -> list[tuple[dict[str, Any], str]]:
    """Return each connection that touches `area_id`, with the area on its far side."""
    found = []
    for connection in state["map"]["connections"]:
        if connection["a"] == area_id:
            found.append((connection, connection["b"]))
        elif connection["b"] == area_id:
            found.append((connection, connection["a"]))
    return found
