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
from .edits import LIGHT_REQUESTED, edit
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
from .settings import REFEREE_DEFAULTS, REFEREE_EFFORTS, REFEREE_MODELS, CampaignSettings
from .vault import append_raw_log, append_raw_text, write_character_notes, write_state_note

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
        self._settings = CampaignSettings(paths.campaign_settings)
        self._context = CommandContext(dice=dice, settings=self._settings)

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
            inputs, target = prepare(self._registry, procedure, working, command.get("inputs") or {}, "player", self._context)
            return self._run_procedure(working, procedure, inputs, target)
        if kind == "propose":
            return self._propose(working, command)
        if kind == "answer_proposal":
            return self._answer(working, command)
        if kind == "judgment":
            return self._raise_judgment(working, command, None)
        if kind == "answer_judgment":
            return self._answer_judgment(working, command)
        if kind == "edit":
            if command.get("change") == "light" and not self._registry.triggers.get(LIGHT_REQUESTED):
                raise IllegalActionError("no plugin in this campaign keeps track of light")
            return edit(working, command, self._context)
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
        """Run a procedure. Its own mechanics card names the target number and the source.

        Only a mechanics card whose `procedure` is the name of this procedure gets the
        target. Other cards from the same handler get no target, and a card that sets its
        own target keeps it.

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
                if event["type"] == "mechanics" and event.get("procedure") == procedure.name:
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
        inputs, target = prepare(self._registry, procedure, working, command.get("inputs") or {}, "referee", self._context)
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
                self._registry, procedure, working, {**inputs, **changes}, "player", self._context, fallback
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
                "judgment_categories": list(p.judgment_categories),
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
            "options": [
                {
                    "section": section, "key": key, "label": spec["label"], "choices": spec["choices"],
                    "default": spec["default"], "value": self._settings.get(section, key, spec["default"]),
                }
                for (section, key), spec in self._registry.settings.items()
            ],
            "judgment": [
                {"category": name, "label": label, "owner": self.judgment_owner(name)}
                for name, label in self._registry.judgment_categories.items()
            ],
            "referee": {key: self._settings.get("referee", key, default) for key, default in REFEREE_DEFAULTS.items()},
        }

    def change_setting(self, section: str, key: str, value: Any) -> None:
        """Check and save one campaign setting. Raises `SettingError` and saves nothing for a bad one."""
        spec = self._registry.settings.get((section, key))
        if spec is not None:
            if value not in spec["choices"]:
                raise SettingError(f"{section}.{key} must be one of {', '.join(spec['choices'])}, got {value!r}")
            self._settings.set(section, key, value)
            return
        if section == "judgment":
            self._change_judgment_owner(key, value)
            return
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

    def log_chat(self, speaker: str, text: str) -> None:
        """Add a chat message, the player's text or the Referee's narration, to the current session's raw log."""
        append_raw_text(self._paths, self._state["session"], speaker, text)

    def log_note(self, text: str) -> Event:
        """Log an out-of-character Referee note to the raw log and return its `ooc_note` event."""
        append_raw_text(self._paths, self._state["session"], "Referee (out of character)", text)
        return {"type": "ooc_note", "text": text}

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
