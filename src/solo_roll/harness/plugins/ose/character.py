"""The OSE `create_character` procedure: 3d6 in order, a class hit die, and a name from the player."""
from typing import Any

from ....character import (
    ABILITIES,
    CLASS_HIT_DICE,
    CLASS_SAVES,
    UNARMORED_AC,
    qualifying_classes,
    roll_abilities,
    roll_character,
    unmet_requirements,
)
from ...errors import IllegalActionError
from ...registry import CommandContext, Event

__all__ = ["CHARACTER_SCHEMA", "CREATE_CHARACTER_INPUTS", "create_character"]

CREATE_CHARACTER_INPUTS: dict[str, dict[str, Any]] = {
    "class": {"type": "string", "label": "Class"},
    "character_name": {"type": "string", "label": "Name"},
    "description": {"type": "string", "label": "Description", "default": ""},
}

CHARACTER_SCHEMA: dict[str, dict[str, Any]] = {
    "name": {"type": "string", "label": "Name"},
    "class": {"type": "string", "label": "Class"},
    "level": {"type": "integer", "label": "Level"},
    "description": {"type": "string", "label": "Description"},
    "abilities": {"type": "object", "label": "Ability scores"},
    "saves": {"type": "object", "label": "Saving throw targets"},
    "ac": {"type": "integer", "label": "Armor class"},
    "hp": {"type": "integer", "label": "Hit points"},
    "max_hp": {"type": "integer", "label": "Maximum hit points"},
}


def create_character(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """Roll a character with `roll_character` and add it to the party.

    The command inputs are `class`, `character_name` and an optional `description`.
    Scores that miss the class minimums are kept in `state["kept_roll"]` and reused by the next
    command, so a failed roll cannot be rerolled; a successful creation clears them.
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

    kept = state.get("kept_roll")
    scores = dict(kept["abilities"]) if kept else roll_abilities(ctx.dice)
    unmet = unmet_requirements(scores, character_class)
    if unmet:
        qualifies = qualifying_classes(scores)
        state["kept_roll"] = {"abilities": scores, "qualifies_for": qualifies}
        listed = ", ".join(f"{a} {v}" for a, v in scores.items())
        return [
            {
                "type": "mechanics",
                "text": (
                    f"Rolled {listed}. Cannot be a {character_class}: needs {', '.join(unmet)}. "
                    f"These scores are kept; choose one of: {', '.join(qualifies)}."
                ),
                "procedure": "create_character",
                "dice": "3d6 x6",
                "rolls": [scores[a] for a in ABILITIES],
                "result": f"kept; qualifies for {', '.join(qualifies)}",
                "source": "OSE Classic Fantasy: Characters",
            }
        ]
    rolled = roll_character(ctx.dice, character_class, abilities=scores)
    state["kept_roll"] = None

    abilities = rolled["abilities"]
    members.append(
        {
            "name": name,
            "class": character_class,
            "level": 1,
            "description": str(inputs.get("description") or "").strip(),
            "abilities": abilities,
            "saves": dict(CLASS_SAVES[character_class]),
            "ac": UNARMORED_AC,
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
