"""The plugin registry: what each plugin of a campaign adds to the engine."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..rng import DiceSource
from .errors import PluginError

__all__ = [
    "AUTO",
    "CONFIRM",
    "CONFIRM_LEVELS",
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
    "Target",
    "TargetSource",
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
    settings: Any = None
    """The campaign settings store (`CampaignSettings`), for plugin code that reads a setting it registered."""


CommandHandler = Callable[[dict[str, Any], dict[str, Any], CommandContext], list[Event]]
"""Takes a working copy of the state, the command and the context.

It changes the state in place and returns the events. The engine keeps the
changes only when the handler returns without raising.
"""

ActionProvider = Callable[[dict[str, Any]], list[Action]]

AUTO = "auto"
"""Confirm level of a procedure that runs without asking the player."""

CONFIRM = "confirm"
"""Confirm level of a procedure that the Referee must propose for the player to answer."""

CONFIRM_LEVELS = (AUTO, CONFIRM)

Target = dict[str, Any]
"""A target number: `{"value": int, "source": str}`, where `source` names where it came from."""

TargetSource = Callable[[dict[str, Any], dict[str, Any]], "Target | None"]
"""Takes the state and the checked inputs of a procedure, and returns a target from plugin data or None."""

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
    """The default confirm level. The campaign settings can change it."""
    label: str = ""
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Input name to spec: `type` ("string" or "integer"), `label`, and optional `choices` and `default`.

    An input with no `default` is required.
    """
    target: bool = False
    """True when the procedure rolls against a target number. The handler gets it as `command["target"]`."""
    judgment_categories: tuple[str, ...] = ()
    """The judgment call categories the procedure can raise."""


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
    referee_guides: list[str] = field(default_factory=list)
    procedures: dict[str, Procedure] = field(default_factory=dict)
    triggers: dict[str, list[Trigger]] = field(default_factory=dict)
    state_defaults: dict[str, StateDefault] = field(default_factory=dict)
    target_sources: dict[str, list[TargetSource]] = field(default_factory=dict)
    settings: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    judgment_categories: dict[str, str] = field(default_factory=dict)
    character_schema: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_command(self, command_type: str, handler: CommandHandler) -> None:
        if command_type in self.commands:
            raise PluginError(f"command '{command_type}' is already registered")
        self.commands[command_type] = handler

    def add_action_provider(self, provider: ActionProvider) -> None:
        self.action_providers.append(provider)

    def add_referee_guide(self, markdown: str) -> None:
        """Add markdown to the Referee's system prompt, in plugin order."""
        self.referee_guides.append(markdown)

    def add_procedure(
        self,
        name: str,
        handler: CommandHandler,
        confirm: str = AUTO,
        *,
        label: str = "",
        inputs: dict[str, dict[str, Any]] | None = None,
        target: bool = False,
        judgment_categories: tuple[str, ...] = (),
    ) -> None:
        """Register a procedure with its default confirm level, its inputs, whether it needs a target number, and the judgment call categories it can raise."""
        if name in self.procedures:
            raise PluginError(f"procedure '{name}' is already registered")
        if confirm not in CONFIRM_LEVELS:
            raise PluginError(f"procedure '{name}': confirm level '{confirm}' is not one of {CONFIRM_LEVELS}")
        self.procedures[name] = Procedure(
            name, handler, confirm, label or name, dict(inputs or {}), target, tuple(judgment_categories)
        )

    def add_target_source(self, procedure: str, source: TargetSource) -> None:
        """Supply target numbers for a procedure from plugin data.

        Any plugin can add one, for its own procedure or another plugin's. The
        engine asks the sources in registration order and takes the first target.
        When none gives one, the target number is a proposal input.
        """
        self.target_sources.setdefault(procedure, []).append(source)

    def add_setting(self, section: str, key: str, label: str, choices: list[str], default: str) -> None:
        """Register a campaign setting with a fixed list of choices. The player changes it in the settings menu."""
        if (section, key) in self.settings:
            raise PluginError(f"setting '{section}.{key}' is already registered")
        if default not in choices:
            raise PluginError(f"setting '{section}.{key}': default '{default}' is not one of its choices")
        self.settings[(section, key)] = {"label": label, "choices": list(choices), "default": default}

    def add_judgment_category(self, name: str, label: str) -> None:
        """Name a category of judgment call. The campaign settings give each category an owner."""
        if name in self.judgment_categories:
            raise PluginError(f"judgment category '{name}' is already registered")
        self.judgment_categories[name] = label

    def add_character_schema(self, fields: dict[str, dict[str, Any]]) -> None:
        """Describe the fields of a party member in this ruleset, each as a `type` and a `label`. One plugin sets it."""
        if self.character_schema:
            raise PluginError("a character schema is already registered")
        self.character_schema = dict(fields)

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
