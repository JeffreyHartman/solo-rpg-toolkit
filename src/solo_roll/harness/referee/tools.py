"""The engine tools the Referee can call, and the labels the UI shows for every tool.

To add an engine tool, define an `EngineTool` and add it to `ENGINE_TOOLS`. Both
adapters pick it up: the Agent SDK adapter serves it as `mcp__engine__<name>`.
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..campaign import CampaignPaths
from ..engine import Engine
from ..errors import HarnessError
from ..registry import Event
from .guard import ENGINE_TOOL_PREFIX, PathGuard

__all__ = ["END_SESSION_TOOL", "ENGINE_TOOLS", "EngineTool", "RefereeTools", "ToolOutcome"]


@dataclass(frozen=True)
class ToolOutcome:
    output: Any
    """What the model gets back, JSON-ready. Keep it to what changed."""
    events: list[Event] = field(default_factory=list)


@dataclass(frozen=True)
class EngineTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    """Argument name to Python type, the simple schema form that the SDK `tool` decorator takes."""
    label: Callable[[Engine, dict[str, Any]], str]
    run: Callable[[Engine, dict[str, Any]], ToolOutcome]
    """Raise a `HarnessError` to refuse; the Referee gets the message as a failed result."""


def _area_name(engine: Engine, area_id: Any) -> str:
    area = engine.state()["map"]["areas"].get(area_id)
    return area["name"] if area else str(area_id)


def _move(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    events = engine.act({"type": "move", "to": args.get("to")})
    return ToolOutcome(output={"events": events, "area": engine.state()["party"]["area"]}, events=events)


def _propose(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    events = engine.act(
        {
            "type": "propose",
            "procedure": args.get("procedure"),
            "inputs": args.get("inputs") or {},
            "reason": args.get("reason", ""),
        }
    )
    if events and events[0]["type"] == "proposal":
        output = {"status": "waiting for the player", "proposal": events[0]["proposal"]}
    else:
        output = {"status": "ran", "events": events}
    return ToolOutcome(output=output, events=events)


def _judgment_call(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    events = engine.act(
        {
            "type": "judgment",
            "category": args.get("category"),
            "question": args.get("question", ""),
            "suggestion": args.get("suggestion", ""),
            "reason": args.get("reason", ""),
            "options": args.get("options") or [],
        }
    )
    if events[0]["type"] == "judgment_decided":
        output = {"status": "decided", "answer": events[0]["answer"], "reason": events[0]["reason"]}
    else:
        output = {"status": "waiting for the player", "judgment": events[0]["judgment"]}
    return ToolOutcome(output=output, events=events)


def _procedure_label(engine: Engine, name: Any) -> str:
    return next((p["label"] for p in engine.procedures() if p["name"] == name), str(name))


def _create_character(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    events = engine.act({"type": "procedure", "name": "create_character", "inputs": dict(args)})
    return ToolOutcome(output={
            "events": events,
            "party": engine.state()["party"]["members"],
            "kept_roll": engine.state().get("kept_roll"),
        }, events=events)


def _edit(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    command = {"type": "edit", **{key: args.get(key) for key in ("who", "change", "value", "reason")}}
    events = engine.act(command)
    return ToolOutcome(output={"events": events}, events=events)


def _monster_action(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    command = {"type": "monster_action", **{k: args.get(k) for k in ("monster", "kind", "action", "target", "reason")}}
    events = engine.act(command)
    return ToolOutcome(output={"events": events, "combat": engine.state().get("combat")}, events=events)


def _out_of_character_note(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    text = str(args.get("text") or "").strip()
    if not text:
        raise HarnessError("The note is empty.")
    return ToolOutcome(output={"status": "noted"}, events=[engine.log_note(text)])


END_SESSION_TOOL = ENGINE_TOOL_PREFIX + "end_session"


def _end_session(engine: Engine, args: dict[str, Any]) -> ToolOutcome:
    session = engine.state()["session"]
    if not engine.paths.raw_log(session).exists():
        raise HarnessError(f"Session {session} has no play to write up yet.")
    return ToolOutcome(
        output={"status": "The session ends after this turn. Say goodbye and end your turn; "
                "the harness then asks you to write the session note."}
    )


ENGINE_TOOLS: tuple[EngineTool, ...] = (
    EngineTool(
        name="state",
        description="Return the engine state snapshot, the available actions, and the procedures you can propose.",
        input_schema={},
        label=lambda engine, args: "Checking the state",
        run=lambda engine, args: ToolOutcome(
            output={
                "state": engine.state(),
                "actions": engine.available_actions(),
                "procedures": engine.procedures(),
                "judgment_categories": engine.settings()["judgment"],
            }
        ),
    ),
    EngineTool(
        name="propose",
        description=(
            "Propose a procedure for the player's action, by procedure name, with its inputs and a short reason. "
            "An Auto procedure runs at once and returns its events. A Confirm procedure becomes a proposal "
            "card that waits for the player to confirm, change, or reject it."
        ),
        input_schema={"procedure": str, "inputs": dict, "reason": str},
        label=lambda engine, args: f"Proposing {_procedure_label(engine, args.get('procedure'))}",
        run=_propose,
    ),
    EngineTool(
        name="judgment_call",
        description=(
            "Raise a judgment call for a decision the rules leave open, with your suggested answer and the reason. "
            "When the player owns the category, a card waits for the player's answer. When the Referee "
            "owns it, your suggestion is the decision and the log records your reason. `options` lists the "
            "answers the player may pick from; pass [] to leave the answer free."
        ),
        input_schema={"category": str, "question": str, "suggestion": str, "reason": str, "options": list[str]},
        label=lambda engine, args: "Raising a judgment call",
        run=_judgment_call,
    ),
    EngineTool(
        name="move",
        description="Move the party to a connected area, by area id.",
        input_schema={"to": str},
        label=lambda engine, args: f"Moving to {_area_name(engine, args.get('to'))}",
        run=_move,
    ),
    EngineTool(
        name="create_character",
        description=(
            "Roll the player's character with the ruleset's creation procedure, once the player has agreed "
            "on a class, a name and a description. The engine rolls the abilities. If the scores miss the class "
            "minimums they are kept: kept_roll lists the classes they qualify for, and the next call uses those scores."
        ),
        input_schema={"class": str, "character_name": str, "description": str},
        label=lambda engine, args: f"Creating {args.get('character_name') or 'a character'}",
        run=_create_character,
    ),
    EngineTool(
        name="edit",
        description=(
            "Change a party member or a monster when no procedure fits, with a one-line reason the player sees. "
            "`who` is a member's name or a monster id. `change` is add_item, remove_item, light (a lit torch or "
            "lantern that joins the party's light), hp, condition, or clear_condition. `value` is the item, the "
            "condition, or for hp a signed change such as -3 or -1d6: the engine rolls any dice. Never pass a die result."
        ),
        input_schema={"who": str, "change": str, "value": str, "reason": str},
        label=lambda engine, args: f"Changing {args.get('who') or 'the state'}",
        run=_edit,
    ),
    EngineTool(
        name="monster_action",
        description=(
            "Take the turn of a monster listed in `combat.waiting`, when no plugin runs the monsters. `kind` is "
            "attack (name the party member in `target`), flee, or other (pass target \"\"). `action` says what it "
            "does, and `reason` why. The engine rolls any attack and damage with the campaign's rules."
        ),
        input_schema={"monster": str, "kind": str, "action": str, "target": str, "reason": str},
        label=lambda engine, args: f"Acting for monster {args.get('monster') or ''}".strip(),
        run=_monster_action,
    ),
    EngineTool(
        name="out_of_character_note",
        description=(
            "Tell the player something about the harness, not the story: a tool you lack or a rule the engine "
            "cannot run. The chat shows it collapsed and the raw log keeps it. Never put it in narration."
        ),
        input_schema={"text": str},
        label=lambda engine, args: "Noting a harness gap",
        run=_out_of_character_note,
    ),
    EngineTool(
        name="end_session",
        description=(
            "End the session when the player asks to stop. After this turn the harness runs End session: "
            "you write the clean session note and update the records, then the next session starts."
        ),
        input_schema={},
        label=lambda engine, args: "Ending the session",
        run=_end_session,
    ),
)


class RefereeTools:
    """What both adapters share: the path guard, the engine tools, and tool labels."""

    def __init__(self, engine: Engine, paths: CampaignPaths, tools: tuple[EngineTool, ...] = ENGINE_TOOLS):
        self.engine = engine
        self.paths = paths
        self.guard = PathGuard(paths)
        self.engine_tools = {t.name: t for t in tools}

    @property
    def engine_tool_names(self) -> list[str]:
        return [ENGINE_TOOL_PREFIX + name for name in self.engine_tools]

    def run_engine(self, tool: str, args: dict[str, Any]) -> ToolOutcome:
        """Run an engine tool by its full or short name. Raises `HarnessError` on refusal."""
        engine_tool = self.engine_tools.get(tool.removeprefix(ENGINE_TOOL_PREFIX))
        if engine_tool is None:
            raise HarnessError(f"no engine tool '{tool}'")
        return engine_tool.run(self.engine, args)

    def label(self, tool: str, tool_input: dict[str, Any]) -> str:
        short = tool.removeprefix(ENGINE_TOOL_PREFIX)
        if tool.startswith(ENGINE_TOOL_PREFIX) and short in self.engine_tools:
            return self.engine_tools[short].label(self.engine, tool_input)
        target = tool_input.get("file_path") or tool_input.get("path") or ""
        place = self._display(target) if target else "the notes"
        if tool == "Read":
            return f"Reading {place}"
        if tool == "Write":
            return f"Writing {place}"
        if tool == "Edit":
            return f"Editing {place}"
        if tool == "Glob":
            return f"Looking for {tool_input.get('pattern', 'notes')}"
        if tool == "Grep":
            return f"Searching {place} for '{tool_input.get('pattern', '')}'"
        return f"Using {tool}"

    def _display(self, raw: str) -> str:
        """Name a path for the player: vault-relative, and never a referee folder file name."""
        path = Path(raw)
        if not path.is_absolute():
            path = self.paths.vault / path
        path = path.resolve()
        if path.is_relative_to(self.paths.referee.resolve()):
            return "the Referee's secret notes"
        if path.is_relative_to(self.paths.vault.resolve()):
            relative = path.relative_to(self.paths.vault.resolve()).as_posix()
            return "the notes" if relative == "." else relative
        return raw
