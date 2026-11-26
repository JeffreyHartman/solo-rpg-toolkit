"""The OSE ruleset plugin: movement between areas, the dungeon turn, ability checks and saving throws."""
from pathlib import Path
from typing import Any

from ...errors import IllegalActionError
from ...mapstate import area, exits
from ...registry import Action, CommandContext, Event, Registry
from . import checks, combat, dungeon_turn
from .character import CREATE_CHARACTER_INPUTS, create_character

__all__ = ["OsePlugin"]

REFEREE_GUIDE = """## Ruleset: Old-School Essentials (OSE)

- Play in the spirit of OSE: a dangerous dungeon, scarce light, and choices with consequences.
- Move the party between areas only with the `move` engine tool, by area id.
- In combat, propose the owner's `attack` and `special_action` for the character the player describes. The engine rolls initiative and attacks, applies all damage, and runs the monsters. Read `combat` in the state and narrate its events; never invent damage, hit points or monster actions.
- When the party is empty, help the player pick a class, a name and a short description. Then call `create_character`; the engine rolls the 3d6 abilities in order.
"""


class OsePlugin:
    name = "ose"
    kind = "ruleset"

    def __init__(
        self,
        data_dir: Path = dungeon_turn.DEFAULT_DATA_DIR,
        wandering: dict[str, Any] | None = dungeon_turn.DEFAULT_WANDERING,
    ):
        """`data_dir` holds `tables/ose/`. `wandering` is the starting wandering config, or None for no checks."""
        self._data_dir = Path(data_dir)
        self._wandering = wandering

    def register(self, registry: Registry) -> None:
        registry.add_command("move", _move)
        registry.add_action_provider(_move_actions)
        registry.add_referee_guide(REFEREE_GUIDE)
        registry.add_judgment_category("ruling", "Rulings the OSE rules leave open")
        registry.add_state_default("dungeon", dungeon_turn.initial_dungeon(self._wandering))
        registry.add_procedure(
            "create_character", create_character, label="Create a character", inputs=CREATE_CHARACTER_INPUTS
        )
        registry.add_procedure("search", dungeon_turn.search(self._data_dir), label=dungeon_turn.PROCEDURE_LABELS["search"])
        registry.add_procedure("listen", dungeon_turn.listen(self._data_dir), label=dungeon_turn.PROCEDURE_LABELS["listen"])
        registry.add_procedure("rest", dungeon_turn.rest, label=dungeon_turn.PROCEDURE_LABELS["rest"])
        registry.add_action_provider(dungeon_turn.dungeon_actions)
        registry.add_trigger("turn", dungeon_turn.wandering_trigger(self._data_dir))
        checks.register(registry)
        combat.register(registry, self._data_dir)


def _move(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    if state.get("combat"):
        raise IllegalActionError("the party cannot move during combat")
    here = state["party"]["area"]
    target = command.get("to")
    if target not in {far for _, far in exits(state, here)}:
        raise IllegalActionError(f"no connection from '{here}' to '{target}'")
    destination = area(state, target)
    state["party"]["area"] = target
    events: list[Event] = [
        {
            "type": "moved",
            "from": here,
            "to": target,
            "text": f"The party moves from {area(state, here)['name']} to {destination['name']}.",
        }
    ]
    if not destination.get("known"):
        destination["known"] = True
        events.append(
            {"type": "area_revealed", "area": target, "text": f"New area: {destination['name']}."}
        )
    return events


def _move_actions(state: dict[str, Any]) -> list[Action]:
    actions = []
    for connection, far in exits(state, state["party"]["area"]):
        far_area = area(state, far)
        if far_area.get("known"):
            label = f"Go to {far_area['name']}"
        else:
            label = f"Take the {connection.get('label', 'unexplored exit')}"
        actions.append({"id": f"move:{far}", "label": label, "command": {"type": "move", "to": far}})
    return actions
