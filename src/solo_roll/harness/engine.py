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
from .errors import IllegalActionError, PluginError, UnknownCommandError
from .proposals import ANSWER_VERBS, ANSWERS, empty_proposals, prepare, proposal_text
from .registry import AUTO, Action, CommandContext, Event, PluginFactory, Procedure, Registry, Target, build_registry
from .settings import CampaignSettings
from .vault import append_raw_log, write_state_note

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

        The state, the raw log and `State.md` change only if the command succeeds.
        """
        working = copy.deepcopy(self._state)
        events = self._with_triggers(self._run(working, command), working)
        self._state = working
        write_json(self._paths.state, self._state)
        append_raw_log(self._paths, self._state["session"], events)
        write_state_note(self._paths, self._state)
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
