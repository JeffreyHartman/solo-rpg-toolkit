"""The plugin registry: what each plugin of a campaign adds to the engine."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..rng import DiceSource
from .errors import PluginError

__all__ = [
    "Action",
    "ActionProvider",
    "CommandContext",
    "CommandHandler",
    "Event",
    "Plugin",
    "PluginFactory",
    "Registry",
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

    def add_command(self, command_type: str, handler: CommandHandler) -> None:
        if command_type in self.commands:
            raise PluginError(f"command '{command_type}' is already registered")
        self.commands[command_type] = handler

    def add_action_provider(self, provider: ActionProvider) -> None:
        self.action_providers.append(provider)


def build_registry(names: list[str], factories: Mapping[str, PluginFactory]) -> Registry:
    """Register the named plugins in order. Discovery is explicit: unknown names fail."""
    registry = Registry()
    for name in names:
        if name not in factories:
            raise PluginError(f"unknown plugin '{name}' (known: {', '.join(sorted(factories))})")
        factories[name]().register(registry)
        registry.plugins.append(name)
    return registry
