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

__all__ = ["ENGINE_TOOLS", "EngineTool", "RefereeTools", "ToolOutcome"]


@dataclass(frozen=True)
class ToolOutcome:
    output: Any
    """What the model gets back, JSON-ready. Keep it to what changed."""
    events: list[Event] = field(default_factory=list)


@dataclass(frozen=True)
class EngineTool:
    name: str
    description: str
    input_schema: dict[str, type]
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


ENGINE_TOOLS: tuple[EngineTool, ...] = (
    EngineTool(
        name="state",
        description="Return the engine state snapshot and the available actions.",
        input_schema={},
        label=lambda engine, args: "Checking the state",
        run=lambda engine, args: ToolOutcome(
            output={"state": engine.state(), "actions": engine.available_actions()}
        ),
    ),
    EngineTool(
        name="move",
        description="Move the party to a connected area, by area id.",
        input_schema={"to": str},
        label=lambda engine, args: f"Moving to {_area_name(engine, args.get('to'))}",
        run=_move,
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
