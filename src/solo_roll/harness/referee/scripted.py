"""`ScriptedReferee`: a Referee fake that plays scripted turns for tests.

It runs each scripted tool call through the same path guard and engine tools
as the Agent SDK adapter. Allowed `Read`, `Write` and `Edit` calls touch the real
file; `Glob` and `Grep` succeed with no effect.
"""
import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

from ..campaign import CampaignPaths
from ..engine import Engine
from ..errors import HarnessError
from ..settings import REFEREE_DEFAULTS
from . import events
from .base import ContextPart, TurnInput, context_part, prompt_parts, session_opening, turn_prompt
from .guard import ENGINE_TOOL_PREFIX
from .tools import RefereeTools

__all__ = ["Call", "Say", "ScriptedReferee", "turns_from_json"]


@dataclass(frozen=True)
class Say:
    text: str


@dataclass(frozen=True)
class Call:
    tool: str
    input: dict[str, Any] = field(default_factory=dict)


Step = Union[Say, Call]


def turns_from_json(turns: Sequence[Sequence[dict[str, Any]]]) -> list[list[Step]]:
    """Build turns from JSON: each step is `{"say": text}` or `{"call": {"tool": name, "input": {...}}}`."""
    return [
        [Say(s["say"]) if "say" in s else Call(s["call"]["tool"], s["call"].get("input", {})) for s in turn]
        for turn in turns
    ]


class ScriptedReferee:
    def __init__(self, engine: Engine, paths: CampaignPaths, turns: Sequence[Sequence[Step]] = ()):
        """Each item of `turns` is the steps of one turn. Turns past the script only end."""
        paths.vault.mkdir(parents=True, exist_ok=True)
        paths.referee.mkdir(parents=True, exist_ok=True)
        self._tools = RefereeTools(engine, paths)
        self._turns = [list(t) for t in turns]
        self._calls = 0
        self._conversation = 1
        self._fresh = True
        self.turns_seen: list[TurnInput] = []
        self.closed = False
        self.model = REFEREE_DEFAULTS["model"]
        self.effort = REFEREE_DEFAULTS["effort"]
        self.compacts = 0
        self.context_tokens: int | None = None
        """What `context_usage` returns; a test sets it."""
        self._turn_context: list[ContextPart] = []

    async def turn(self, player_input: str) -> AsyncIterator[events.RefereeEvent]:
        snapshot = self._tools.engine.state()
        opening = session_opening(self._tools.paths, snapshot["session"]) if self._fresh else None
        self._fresh = False
        prompt = turn_prompt(player_input, snapshot, opening)
        self.turns_seen.append(TurnInput(player_input, snapshot, prompt, self._conversation, self.model, self.effort))
        self._turn_context = prompt_parts(player_input, snapshot, opening)
        steps = self._turns.pop(0) if self._turns else []
        for step in steps:
            if isinstance(step, Say):
                yield events.text(step.text)
            else:
                self._calls += 1
                call_id = f"scripted-{self._calls}"
                label = self._tools.label(step.tool, step.input)
                yield events.tool_start(call_id, step.tool, step.input, label)
                result = self._run(call_id, step)
                got = result.get("error") if "error" in result else result.get("output", "")
                self._turn_context.append(context_part(label, got if isinstance(got, str) else json.dumps(got)))
                yield result
        yield events.done()

    async def close(self) -> None:
        self.closed = True

    async def new_session(self) -> None:
        self._conversation += 1
        self._fresh = True

    async def set_model(self, model: str) -> None:
        self.model = model

    async def set_effort(self, effort: str) -> None:
        self.effort = effort

    async def compact(self) -> None:
        self.compacts += 1

    async def context_usage(self) -> int | None:
        return self.context_tokens

    def turn_context(self) -> list[ContextPart]:
        return list(self._turn_context)

    def _run(self, call_id: str, call: Call) -> events.RefereeEvent:
        reason = self._tools.guard.check(call.tool, call.input)
        if reason:
            return events.tool_result(call_id, call.tool, ok=False, denied=True, error=reason)
        if call.tool.startswith(ENGINE_TOOL_PREFIX):
            try:
                outcome = self._tools.run_engine(call.tool, call.input)
            except HarnessError as exc:
                return events.tool_result(call_id, call.tool, ok=False, error=str(exc))
            return events.tool_result(call_id, call.tool, ok=True, output=outcome.output, events=outcome.events)
        target = self._path(call.input.get("file_path", ""))
        if call.tool == "Read":
            return events.tool_result(call_id, call.tool, ok=True, output=target.read_text())
        if call.tool == "Write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(call.input.get("content", ""))
        if call.tool == "Edit":
            old, new = call.input["old_string"], call.input["new_string"]
            count = -1 if call.input.get("replace_all") else 1
            target.write_text(target.read_text().replace(old, new, count))
        return events.tool_result(call_id, call.tool, ok=True, output="ok")

    def _path(self, raw: str) -> Path:
        path = Path(raw)
        return path if path.is_absolute() else self._tools.paths.vault / path
