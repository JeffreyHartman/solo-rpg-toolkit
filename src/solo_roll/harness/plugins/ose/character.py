"""The OSE `create_character` procedure: 3d6 in order, a class hit die, and a name from the player."""
from typing import Any

from ....character import CLASS_HIT_DICE, roll_character
from ...errors import IllegalActionError
from ...registry import CommandContext, Event

__all__ = ["CREATE_CHARACTER_INPUTS", "create_character"]

CREATE_CHARACTER_INPUTS: dict[str, dict[str, Any]] = {
    "class": {"type": "string", "label": "Class"},
    "character_name": {"type": "string", "label": "Name"},
    "description": {"type": "string", "label": "Description", "default": ""},
}


def create_character(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """Roll a character with `roll_character` and add it to the party.

    The command inputs are `class`, `character_name` and an optional `description`.
    """
    inputs = command["inputs"]
    name = str(inputs.get("character_name") or "").strip()
    character_class = inputs.get("class")
    members = state["party"]["members"]
    if not name:
        raise IllegalActionError("a character needs a name")
    if any(m["name"] == name for m in members):
        raise IllegalActionError(f"the party already has a character named '{name}'")
    if character_class not in CLASS_HIT_DICE:
        raise IllegalActionError(f"unknown class '{character_class}' (one of {', '.join(sorted(CLASS_HIT_DICE))})")

    rolled = roll_character(ctx.dice, character_class)
    if not rolled["eligible"]:
        raise IllegalActionError(f"cannot be a {character_class}: needs {', '.join(rolled['unmet_requirements'])}")

    abilities = rolled["abilities"]
    members.append(
        {
            "name": name,
            "class": character_class,
            "level": 1,
            "description": str(inputs.get("description") or "").strip(),
            "abilities": abilities,
            "hit_die": rolled["hit_die"],
            "hp": rolled["hit_points"],
            "max_hp": rolled["hit_points"],
        }
    )
    for light in state.get("dungeon", {}).get("light", []):
        light["bearer"] = light["bearer"] or name
    scores = ", ".join(f"{a} {v}" for a, v in abilities.items())
    return [
        {
            "type": "mechanics",
            "text": f"Rolled {name} the {character_class}: {scores}; {rolled['hit_die']} hit die gave {rolled['hit_points']} HP.",
            "procedure": "create_character",
            "dice": "3d6 x6",
            "rolls": list(abilities.values()),
            "total": rolled["hit_points"],
            "result": f"{character_class} with {rolled['hit_points']} HP",
            "source": "OSE Classic Fantasy: Characters",
        },
        {"type": "character_created", "member": name, "text": f"{name} the {character_class} joins the party."},
    ]
