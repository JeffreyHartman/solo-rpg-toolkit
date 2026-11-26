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
from .judgment import ASK, JUDGMENT_OWNERS, OWNER_LABELS, REFEREE, empty_judgments, judgment_text
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
from .settings import CampaignSettings
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
        state.setdefault("judgments", empty_judgments())
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
        if kind == "judgment":
            return self._raise_judgment(working, command, None)
        if kind == "answer_judgment":
            return self._answer_judgment(working, command)
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
        self,
        working: dict[str, Any],
        procedure: Procedure,
        inputs: dict[str, Any],
        target: Target | None,
        judgment: dict[str, Any] | None = None,
    ) -> list[Event]:
        """Run a procedure. Each of its mechanics cards names its target number and the source.

        A handler that ends with a `judgment_request` event raises a judgment call, which
        this method turns into a pending card or a Referee decision. `judgment` is the
        answer when the handler continues from one.
        """
        command: dict[str, Any] = {"type": "procedure", "name": procedure.name, "inputs": inputs}
        if target is not None:
            command["target"] = {"value": target["value"], "source": target["source"]}
        if judgment is not None:
            command["judgment"] = judgment
        events = procedure.handler(working, command, self._context)
        if target is not None:
            for event in events:
                if event["type"] == "mechanics":
                    event.setdefault("target", dict(command["target"]))
        if events and events[-1]["type"] == "judgment_request":
            request = events.pop()
            resume = {"procedure": procedure.name, "inputs": inputs, "target": target, "data": request["data"]}
            events.extend(self._raise_judgment(working, request, resume))
        return events

    def _raise_judgment(
        self, working: dict[str, Any], request: dict[str, Any], resume: dict[str, Any] | None
    ) -> list[Event]:
        """Keep a pending card when the player owns the category, or log the Referee's decision and go on."""
        category = str(request.get("category") or "")
        if category not in self._registry.judgment_categories:
            known = ", ".join(self._registry.judgment_categories) or "none registered"
            raise IllegalActionError(f"no judgment call category '{category}' (known: {known})")
        options = [str(o) for o in request.get("options") or []]
        suggestion = str(request.get("suggestion") or "")
        if not suggestion:
            raise IllegalActionError("a judgment call needs a suggestion")
        if options and suggestion not in options:
            raise IllegalActionError(f"the suggestion must be one of {', '.join(options)}, got {suggestion!r}")
        question = str(request.get("question") or "")
        reason = str(request.get("reason") or "")
        if self.judgment_owner(category) == REFEREE:
            decided: Event = {
                "type": "judgment_decided",
                "category": category,
                "question": question,
                "answer": suggestion,
                "reason": reason,
                "text": f"The Referee decided ({category}): {question} Answer: {suggestion}. Reason: {reason}",
            }
            return [decided, *self._resume(working, resume, category, suggestion)]
        judgments = working["judgments"]
        card = {
            "id": f"j{judgments['next_id']}",
            "category": category,
            "question": question,
            "suggestion": suggestion,
            "reason": reason,
            "options": options,
            "resume": resume,
        }
        judgments["next_id"] += 1
        judgments["pending"].append(card)
        return [{"type": "judgment_call", "judgment": card, "text": judgment_text(card)}]

    def _resume(
        self, working: dict[str, Any], resume: dict[str, Any] | None, category: str, answer: str
    ) -> list[Event]:
        if resume is None:
            return []
        return self._run_procedure(
            working,
            self._procedure(resume["procedure"]),
            resume["inputs"],
            resume["target"],
            {"category": category, "answer": answer, "data": resume["data"]},
        )

    def _answer_judgment(self, working: dict[str, Any], command: dict[str, Any]) -> list[Event]:
        pending = working["judgments"]["pending"]
        card = next((c for c in pending if c["id"] == command.get("id")), None)
        if card is None:
            raise IllegalActionError(f"no pending judgment call '{command.get('id')}'")
        answer = str(command.get("answer") or "").strip()
        if not answer:
            raise IllegalActionError("a judgment call needs an answer")
        if card["options"] and answer not in card["options"]:
            raise IllegalActionError(f"the answer must be one of {', '.join(card['options'])}, got {answer!r}")
        pending.remove(card)
        answered: Event = {
            "type": "judgment_answered",
            "id": card["id"],
            "category": card["category"],
            "answer": answer,
            "text": f"The player answered ({card['category']}): {card['question']} Answer: {answer}.",
        }
        return [answered, *self._resume(working, card["resume"], card["category"], answer)]

    def judgment_owner(self, category: str) -> str:
        """Who decides a category, from the campaign settings: "ask" (the player, the default) or "referee"."""
        return self._settings.get("judgment", category, ASK)

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
            "judgment": [
                {"category": name, "label": label, "owner": self.judgment_owner(name)}
                for name, label in self._registry.judgment_categories.items()
            ],
        }

    def change_setting(self, section: str, key: str, value: Any) -> None:
        """Check and save one campaign setting. Raises `SettingError` and saves nothing for a bad one."""
        if section == "judgment":
            self._change_judgment_owner(key, value)
            return
        if section != "confirm":
            raise SettingError(f"no campaign setting section '{section}'")
        if key not in self._registry.procedures:
            raise SettingError(f"no procedure '{key}'")
        if value not in CONFIRM_LEVELS:
            raise SettingError(f"confirm level must be one of {', '.join(CONFIRM_LEVELS)}, got {value!r}")
        self._settings.set(section, key, value)

    def _change_judgment_owner(self, category: str, owner: Any) -> None:
        if category not in self._registry.judgment_categories:
            raise SettingError(f"no judgment call category '{category}'")
        if owner not in JUDGMENT_OWNERS:
            options = ", ".join(f"{o} ({OWNER_LABELS[o]})" for o in JUDGMENT_OWNERS)
            raise SettingError(f"a judgment call owner must be one of {options}, got {owner!r}")
        self._settings.set("judgment", category, owner)

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
