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
from .errors import IllegalActionError, PluginError, SettingError, UnknownCommandError
from .proposals import ANSWER_VERBS, ANSWERS, empty_proposals, prepare, proposal_text
from .registry import (
    AUTO,
    CONFIRM_LEVELS,
    Action,
    CommandContext,
    Event,
    PluginFactory,
    Procedure,
    Registry,
    Target,
    build_registry,
)
from .settings import REFEREE_DEFAULTS, REFEREE_EFFORTS, REFEREE_MODELS, CampaignSettings
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
        state.setdefault("proposals", empty_proposals())
        self._state = state
        self._registry = registry
        self._context = CommandContext(dice=dice)
        self._settings = CampaignSettings(paths.campaign_settings)

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
        kind = command.get("type")
        if kind == "procedure":
            procedure = self._procedure(command.get("name"))
            inputs, target = prepare(self._registry, procedure, working, command.get("inputs") or {}, "player")
            return self._run_procedure(working, procedure, inputs, target)
        if kind == "propose":
            return self._propose(working, command)
        if kind == "answer_proposal":
            return self._answer(working, command)
        handler = self._registry.commands.get(command.get("type", ""))
        if handler is None:
            raise UnknownCommandError(f"no plugin handles command '{command.get('type')}'")
        return handler(working, command, self._context)

    def _procedure(self, name: Any) -> Procedure:
        procedure = self._registry.procedures.get(name or "")
        if procedure is None:
            raise UnknownCommandError(f"no plugin registers procedure '{name}'")
        return procedure

    def _run_procedure(
        self, working: dict[str, Any], procedure: Procedure, inputs: dict[str, Any], target: Target | None
    ) -> list[Event]:
        """Run a procedure. Each of its mechanics cards names its target number and the source."""
        command: dict[str, Any] = {"type": "procedure", "name": procedure.name, "inputs": inputs}
        if target is not None:
            command["target"] = {"value": target["value"], "source": target["source"]}
        events = procedure.handler(working, command, self._context)
        if target is not None:
            for event in events:
                if event["type"] == "mechanics":
                    event.setdefault("target", dict(command["target"]))
        return events

    def _propose(self, working: dict[str, Any], command: dict[str, Any]) -> list[Event]:
        """Run an Auto procedure at once, or keep a Confirm one as a pending proposal."""
        procedure = self._procedure(command.get("procedure"))
        inputs, target = prepare(self._registry, procedure, working, command.get("inputs") or {}, "referee")
        if self.confirm_level(procedure.name) == AUTO:
            return self._run_procedure(working, procedure, inputs, target)
        proposals = working["proposals"]
        proposal = {
            "id": f"p{proposals['next_id']}",
            "procedure": procedure.name,
            "label": procedure.label,
            "inputs": inputs,
            "target": target,
            "reason": str(command.get("reason") or ""),
        }
        proposals["next_id"] += 1
        proposals["pending"].append(proposal)
        return [{"type": "proposal", "proposal": proposal, "text": proposal_text(proposal)}]

    def _answer(self, working: dict[str, Any], command: dict[str, Any]) -> list[Event]:
        pending = working["proposals"]["pending"]
        proposal = next((p for p in pending if p["id"] == command.get("id")), None)
        if proposal is None:
            raise IllegalActionError(f"no pending proposal '{command.get('id')}'")
        reply = command.get("answer")
        if reply not in ANSWERS:
            raise IllegalActionError(f"answer must be one of {', '.join(ANSWERS)}, got {reply!r}")
        pending.remove(proposal)
        procedure = self._procedure(proposal["procedure"])
        answered: Event = {
            "type": "proposal_answered",
            "id": proposal["id"],
            "answer": reply,
            "text": f"The player {ANSWER_VERBS[reply]} the proposal: {proposal['label']}.",
        }
        if reply == "reject":
            return [answered]
        inputs, target = proposal["inputs"], proposal["target"]
        if reply == "change":
            changes = dict(command.get("inputs") or {})
            fallback = target if target and target["editable"] else None
            # The card sends every field back, so an unchanged target keeps its source.
            if fallback and str(changes.get("target")) == str(fallback["value"]):
                del changes["target"]
            inputs, target = prepare(
                self._registry, procedure, working, {**inputs, **changes}, "player", fallback
            )
        return [answered, *self._run_procedure(working, procedure, inputs, target)]

    def confirm_level(self, procedure: str) -> str:
        """The confirm level from the campaign settings, or the procedure's default."""
        return self._settings.get("confirm", procedure, self._procedure(procedure).confirm)

    def procedures(self) -> list[dict[str, Any]]:
        """Each procedure with its label, inputs, whether it needs a target, and its current confirm level."""
        return [
            {
                "name": p.name,
                "label": p.label,
                "inputs": p.inputs,
                "target": p.target,
                "confirm": self.confirm_level(p.name),
            }
            for p in self._registry.procedures.values()
        ]

    def settings(self) -> dict[str, Any]:
        """The campaign settings the engine owns, one list of rows per section, for the settings menu."""
        return {
            "confirm": [
                {"procedure": p.name, "label": p.label, "default": p.confirm, "level": self.confirm_level(p.name)}
                for p in self._registry.procedures.values()
            ],
            "referee": {key: self._settings.get("referee", key, default) for key, default in REFEREE_DEFAULTS.items()},
        }

    def change_setting(self, section: str, key: str, value: Any) -> None:
        """Check and save one campaign setting. Raises `SettingError` and saves nothing for a bad one."""
        if section == "referee":
            _check_referee_setting(key, value)
            self._settings.set(section, key, value)
            return
        if section != "confirm":
            raise SettingError(f"no campaign setting section '{section}'")
        if key not in self._registry.procedures:
            raise SettingError(f"no procedure '{key}'")
        if value not in CONFIRM_LEVELS:
            raise SettingError(f"confirm level must be one of {', '.join(CONFIRM_LEVELS)}, got {value!r}")
        self._settings.set(section, key, value)

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

    @property
    def paths(self) -> CampaignPaths:
        return self._paths

    def new_session(self) -> list[Event]:
        """End the current session and start the next one, if the current session has a raw log.

        A session with no raw log has had no play, so it keeps its number and this returns no events.
        """
        session = self._state["session"]
        if not self._paths.raw_log(session).exists():
            return []
        events: list[Event] = [{"type": "session_ended", "session": session, "text": f"Session {session} ends."}]
        append_raw_log(self._paths, session, events)
        self._state["session"] = session + 1
        write_json(self._paths.state, self._state)
        write_state_note(self._paths, self._state)
        return events

    def referee_guides(self) -> list[str]:
        return list(self._registry.referee_guides)

    def available_actions(self) -> list[Action]:
        snapshot = self.state()
        return [a for provider in self._registry.action_providers for a in provider(snapshot)]


def _check_referee_setting(key: str, value: Any) -> None:
    if key == "model" and value not in REFEREE_MODELS:
        raise SettingError(f"model must be one of {', '.join(REFEREE_MODELS)}, got {value!r}")
    if key == "effort" and value not in REFEREE_EFFORTS:
        raise SettingError(f"effort must be one of {', '.join(REFEREE_EFFORTS)}, got {value!r}")
    if key == "budget" and (type(value) is not int or value <= 0):
        raise SettingError(f"budget must be a positive whole number of tokens, got {value!r}")
    if key not in REFEREE_DEFAULTS:
        raise SettingError(f"no Referee setting '{key}'")


def open_campaign(
    root: Path, dice: DiceSource, factories: Mapping[str, PluginFactory]
) -> Engine:
    """Load a campaign folder and register the plugins its `campaign.json` names."""
    paths = CampaignPaths(Path(root))
    settings = load_json(paths.settings)
    registry = build_registry(list(settings.get("plugins", [])), factories)
    return Engine(paths, load_json(paths.state), registry, dice)
