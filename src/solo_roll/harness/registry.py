"""The plugin registry: what each plugin of a campaign adds to the engine."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..rng import DiceSource
from .errors import PluginError

__all__ = [
    "AUTO",
    "Action",
    "ActionProvider",
    "CommandContext",
    "CommandHandler",
    "Event",
    "Plugin",
    "PluginFactory",
    "Procedure",
    "Registry",
    "StateDefault",
    "Trigger",
    "build_registry",
]

Event = dict[str, Any]
"""One thing that happened: a `type`, a `text` line for the log, and data fields."""

Action = dict[str, Any]
"""An available action: an `id`, a `label`, and the `command` that runs it."""


@dataclass(frozen=True)
class CommandContext:
    dice: DiceSource


CommandHandler = Callable[[dict[str, Any], dict[str, Any], CommandContext], list[Event]]
"""Takes a working copy of the state, the command and the context.

It changes the state in place and returns the events. The engine keeps the
changes only when the handler returns without raising.
"""

ActionProvider = Callable[[dict[str, Any]], list[Action]]

AUTO = "auto"
"""Confirm level of a procedure that runs without asking the player."""

Trigger = Callable[[dict[str, Any], Event, CommandContext], list[Event]]
"""Runs after an engine event of the type it was registered for.

Takes the working state, the event and the context, and returns more events. It
runs inside the same transaction as the command that caused the event.
"""

StateDefault = Callable[[dict[str, Any]], Any]
"""Builds the value of a state key that is missing, from the state loaded so far."""


@dataclass(frozen=True)
class Procedure:
    """A named sequence of rule steps. Run it with `{"type": "procedure", "name": name}`."""

    name: str
    handler: CommandHandler
    confirm: str = AUTO


class Plugin(Protocol):
    name: str
    kind: str  # "ruleset", "generator" or "module"

    def register(self, registry: "Registry") -> None: ...


PluginFactory = Callable[[], Plugin]
"""Builds a plugin. Bind any paths the plugin needs (a data folder) when you make the factory."""


@dataclass
class Registry:
    plugins: list[str] = field(default_factory=list)
    commands: dict[str, CommandHandler] = field(default_factory=dict)
    action_providers: list[ActionProvider] = field(default_factory=list)
    procedures: dict[str, Procedure] = field(default_factory=dict)
    triggers: dict[str, list[Trigger]] = field(default_factory=dict)
    state_defaults: dict[str, StateDefault] = field(default_factory=dict)

    def add_command(self, command_type: str, handler: CommandHandler) -> None:
        if command_type in self.commands:
            raise PluginError(f"command '{command_type}' is already registered")
        self.commands[command_type] = handler

    def add_action_provider(self, provider: ActionProvider) -> None:
        self.action_providers.append(provider)

    def add_procedure(self, name: str, handler: CommandHandler, confirm: str = AUTO) -> None:
        """Register a procedure. Only the Auto confirm level exists so far."""
        if name in self.procedures:
            raise PluginError(f"procedure '{name}' is already registered")
        if confirm != AUTO:
            raise PluginError(f"procedure '{name}': confirm level '{confirm}' is not supported")
        self.procedures[name] = Procedure(name, handler, confirm)

    def add_trigger(self, event_type: str, trigger: Trigger) -> None:
        self.triggers.setdefault(event_type, []).append(trigger)

    def add_state_default(self, key: str, factory: StateDefault) -> None:
        if key in self.state_defaults:
            raise PluginError(f"state key '{key}' already has a default")
        self.state_defaults[key] = factory


def build_registry(names: list[str], factories: Mapping[str, PluginFactory]) -> Registry:
    """Register the named plugins in order. Discovery is explicit: unknown names fail."""
    registry = Registry()
    for name in names:
        if name not in factories:
            raise PluginError(f"unknown plugin '{name}' (known: {', '.join(sorted(factories))})")
        factories[name]().register(registry)
        registry.plugins.append(name)
    return registry
