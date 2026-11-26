"""The OSE ruleset plugin. This version supplies movement between connected areas."""
from typing import Any

from ...errors import IllegalActionError
from ...mapstate import area, exits
from ...registry import Action, CommandContext, Event, Registry

__all__ = ["OsePlugin"]


class OsePlugin:
    name = "ose"
    kind = "ruleset"

    def register(self, registry: Registry) -> None:
        registry.add_command("move", _move)
        registry.add_action_provider(_move_actions)


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
