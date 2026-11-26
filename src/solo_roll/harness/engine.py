"""The engine: the only owner of mechanical state and dice in a campaign.

UI clicks, Referee tools and triggers all call `act`. Plugins supply the
command handlers and the available action providers through the registry.
"""
import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..rng import DiceSource
from .campaign import CampaignPaths, load_json, write_json
from .errors import PluginError, UnknownCommandError
from .registry import Action, CommandContext, Event, PluginFactory, Registry, build_registry
from .vault import append_raw_log, write_character_notes, write_state_note

__all__ = ["Engine", "open_campaign"]

MAX_TRIGGER_DEPTH = 8


class Engine:
    def __init__(
        self,
        paths: CampaignPaths,
        state: dict[str, Any],
        registry: Registry,
        dice: DiceSource,
    ):
        self._paths = paths
        for key, factory in registry.state_defaults.items():
            if key not in state:
                state[key] = factory(state)
        self._state = state
        self._registry = registry
        self._context = CommandContext(dice=dice)

    def act(self, command: dict[str, Any]) -> list[Event]:
        """Run one command and return its events in order.

        The state, the raw log, `State.md` and the character notes' mechanical blocks
        change only if the command succeeds.
        """
        working = copy.deepcopy(self._state)
        events = self._with_triggers(self._run(working, command), working)
        self._state = working
        write_json(self._paths.state, self._state)
        append_raw_log(self._paths, self._state["session"], events)
        write_state_note(self._paths, self._state)
        write_character_notes(self._paths, self._state)
        return events

    def _run(self, working: dict[str, Any], command: dict[str, Any]) -> list[Event]:
        if command.get("type") == "procedure":
            procedure = self._registry.procedures.get(command.get("name", ""))
            if procedure is None:
                raise UnknownCommandError(f"no plugin registers procedure '{command.get('name')}'")
            return procedure.handler(working, command, self._context)
        handler = self._registry.commands.get(command.get("type", ""))
        if handler is None:
            raise UnknownCommandError(f"no plugin handles command '{command.get('type')}'")
        return handler(working, command, self._context)

    def _with_triggers(self, events: list[Event], working: dict[str, Any], depth: int = 0) -> list[Event]:
        """Insert the events of each trigger right after the event that fired it."""
        if depth > MAX_TRIGGER_DEPTH:
            raise PluginError("triggers keep firing each other")
        out: list[Event] = []
        for event in events:
            out.append(event)
            for trigger in self._registry.triggers.get(event["type"], []):
                out.extend(self._with_triggers(trigger(working, event, self._context), working, depth + 1))
        return out

    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def referee_guides(self) -> list[str]:
        return list(self._registry.referee_guides)

    def available_actions(self) -> list[Action]:
        snapshot = self.state()
        return [a for provider in self._registry.action_providers for a in provider(snapshot)]


def open_campaign(
    root: Path, dice: DiceSource, factories: Mapping[str, PluginFactory]
) -> Engine:
    """Load a campaign folder and register the plugins its `campaign.json` names."""
    paths = CampaignPaths(Path(root))
    settings = load_json(paths.settings)
    registry = build_registry(list(settings.get("plugins", [])), factories)
    return Engine(paths, load_json(paths.state), registry, dice)
