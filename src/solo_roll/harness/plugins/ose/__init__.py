"""The OSE ruleset plugin: movement between areas and the dungeon turn."""
from pathlib import Path
from typing import Any

from ...errors import IllegalActionError
from ...mapstate import area, exits
from ...registry import Action, CommandContext, Event, Registry
from . import dungeon_turn

__all__ = ["OsePlugin"]

REFEREE_GUIDE = """## Ruleset: Old-School Essentials (OSE)

- Play in the spirit of OSE: a dangerous dungeon, scarce light, and choices with consequences.
- Move the party between areas only with the `move` engine tool, by area id.
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
        registry.add_state_default("dungeon", dungeon_turn.initial_dungeon(self._wandering))
        registry.add_procedure("search", dungeon_turn.search(self._data_dir))
        registry.add_procedure("listen", dungeon_turn.listen(self._data_dir))
        registry.add_procedure("rest", dungeon_turn.rest)
        registry.add_action_provider(dungeon_turn.dungeon_actions)
        registry.add_trigger("turn", dungeon_turn.wandering_trigger(self._data_dir))


def _move(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
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
