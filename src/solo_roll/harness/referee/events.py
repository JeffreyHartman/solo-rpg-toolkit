"""The Referee event stream that every adapter yields from `Referee.turn`.

Each event is a JSON-ready dict with a `type`:
  text         {text}                                  a chunk of streamed prose
  tool_start   {id, tool, input, label}                the Referee starts a tool call
  tool_result  {id, tool, ok, denied, output?, error?, events}
                                                       `events` are engine events the call caused
  done         {error?}                                the turn is over
Text that comes before a `tool_start` in the same turn is a status line, not narration.
"""
from typing import Any

from ..registry import Event

__all__ = ["RefereeEvent", "done", "text", "tool_result", "tool_start"]

RefereeEvent = dict[str, Any]


def text(chunk: str) -> RefereeEvent:
    return {"type": "text", "text": chunk}


def tool_start(tool_use_id: str, tool: str, tool_input: dict[str, Any], label: str) -> RefereeEvent:
    return {"type": "tool_start", "id": tool_use_id, "tool": tool, "input": tool_input, "label": label}


def tool_result(
    tool_use_id: str,
    tool: str,
    *,
    ok: bool,
    output: Any = None,
    error: str | None = None,
    denied: bool = False,
    events: list[Event] | None = None,
) -> RefereeEvent:
    result: RefereeEvent = {
        "type": "tool_result",
        "id": tool_use_id,
        "tool": tool,
        "ok": ok,
        "denied": denied,
        "events": list(events or []),
    }
    if output is not None:
        result["output"] = output
    if error is not None:
        result["error"] = error
    return result


def done(error: str | None = None) -> RefereeEvent:
    return {"type": "done", **({"error": error} if error else {})}
