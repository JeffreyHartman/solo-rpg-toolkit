"""Lookups on `state["party"]["members"]` and the fight's monsters, shared by every plugin."""
from typing import Any

from .errors import IllegalActionError

__all__ = ["member", "monster_label", "standing"]


def member(state: dict[str, Any], name: str) -> dict[str, Any]:
    """The party member called `name`, or `IllegalActionError`."""
    for candidate in state["party"]["members"]:
        if candidate["name"] == name:
            return candidate
    raise IllegalActionError(f"no party member named '{name}'")


def standing(state: dict[str, Any]) -> list[dict[str, Any]]:
    """The party members with hit points left."""
    return [m for m in state["party"]["members"] if m.get("hp", 1) > 0]


def monster_label(monster: dict[str, Any]) -> str:
    """How the log names a monster: its name and id, such as "goblin m1"."""
    return f"{monster['name']} {monster['id']}"
