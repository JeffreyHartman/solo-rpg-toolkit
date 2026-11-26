"""The Referee's path guard: which tool calls may run, and on which paths.

Both adapters call `PathGuard.check` before every tool call. In the Agent SDK
adapter it is the PreToolUse hook, which runs before the CLI's own permission
rules (ADR 0002).
"""
from pathlib import Path, PurePath
from typing import Any

from ..campaign import CampaignPaths
from ..vault import BLOCK_BEGIN, BLOCK_END, find_block

__all__ = ["ENGINE_TOOL_PREFIX", "FILE_TOOLS", "PathGuard"]

FILE_TOOLS = ("Read", "Write", "Edit", "Glob", "Grep")
ENGINE_TOOL_PREFIX = "mcp__engine__"
_WRITE_TOOLS = {"Write", "Edit"}
_GLOB_CHARS = set("*?[{")
_MAX_ALTERNATIVES = 256
_OUTSIDE = "The Referee can reach only the campaign vault and the referee folder."
_ENGINE_FILE = "The engine writes this file. Change mechanical state through the engine tools."
_ENGINE_BLOCK = (
    "The engine writes the mechanical block between the engine markers. Leave it as it is, "
    "and change mechanical state through the engine tools."
)


class PathGuard:
    def __init__(self, paths: CampaignPaths):
        self._paths = paths
        self._roots = (paths.vault.resolve(), paths.referee.resolve())

    def check(self, tool: str, tool_input: dict[str, Any]) -> str | None:
        """Return the reason to deny this call, or None to allow it."""
        if tool.startswith(ENGINE_TOOL_PREFIX):
            return None
        if tool not in FILE_TOOLS:
            return f"The Referee has no {tool} tool."
        if tool in {"Read", "Write", "Edit"}:
            raw = tool_input.get("file_path")
            if not isinstance(raw, str) or not raw:
                return f"{tool} needs a file_path."
            resolved = self._resolve(raw)
            if resolved is None:
                return _OUTSIDE
            if tool in _WRITE_TOOLS and self._paths.is_engine_written(resolved):
                return _ENGINE_FILE
            if tool in _WRITE_TOOLS and _changes_block(tool, resolved, tool_input):
                return _ENGINE_BLOCK
            return None
        searched = [tool_input.get("path")]
        pattern = tool_input.get("pattern" if tool == "Glob" else "glob")
        if isinstance(pattern, str):
            alternatives = _expand_braces(pattern)
            if alternatives is None:
                return _OUTSIDE
            for alternative in alternatives:
                if ".." in PurePath(alternative).parts:
                    return _OUTSIDE
                searched.append(_static_prefix(alternative))
        for raw in searched:
            if raw is not None and (not isinstance(raw, str) or self._resolve(raw) is None):
                return _OUTSIDE
        return None

    def _resolve(self, raw: str) -> Path | None:
        """Resolve `raw` against the vault, or return None if it leaves the allowed roots.

        Resolving follows symlinks, so a link inside the vault that points out is outside.
        """
        pure = PurePath(raw)
        if raw.startswith("~") or ".." in pure.parts:
            return None
        resolved = (self._paths.vault / pure).resolve()
        if any(resolved.is_relative_to(root) for root in self._roots):
            return resolved
        return None


def _changes_block(tool: str, resolved: Path, tool_input: dict[str, Any]) -> bool:
    """True if this Write or Edit could change, remove, move out of place or forge a mechanical block."""
    current = resolved.read_text(errors="replace") if resolved.is_file() else ""
    span = find_block(current)
    if tool == "Write":
        content = tool_input.get("content")
        if not isinstance(content, str):
            return True
        if span is None:
            return BLOCK_BEGIN in content or BLOCK_END in content
        if content.count(BLOCK_BEGIN) != 1 or content.count(BLOCK_END) != 1:
            return True
        new_span = find_block(content)
        return new_span is None or content[slice(*new_span)] != current[slice(*span)]
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    if not isinstance(old, str) or not isinstance(new, str) or not old:
        return True
    if BLOCK_BEGIN in new or BLOCK_END in new:
        return True
    if span is None:
        return False
    start = current.find(old)
    while start >= 0:
        if start < span[1] and start + len(old) > span[0]:
            return True
        start = current.find(old, start + 1)
    return False


def _static_prefix(pattern: str) -> str:
    """Return the leading parts of a glob pattern that hold no glob characters."""
    parts = []
    for part in PurePath(pattern).parts:
        if _GLOB_CHARS & set(part):
            break
        parts.append(part)
    return str(PurePath(*parts)) if parts else "."


def _expand_braces(pattern: str) -> list[str] | None:
    """Return every pattern that `{a,b}` groups in `pattern` stand for, nested groups included.

    Returns None for unbalanced braces or more than `_MAX_ALTERNATIVES` patterns, which the guard denies.
    """
    open_at = pattern.find("{")
    if open_at < 0:
        return None if "}" in pattern else [pattern]
    depth, choices, start = 0, [], open_at + 1
    for i in range(open_at, len(pattern)):
        if pattern[i] == "{":
            depth += 1
        elif pattern[i] == "}":
            depth -= 1
            if depth == 0:
                choices.append(pattern[start:i])
                break
        elif pattern[i] == "," and depth == 1:
            choices.append(pattern[start:i])
            start = i + 1
    else:
        return None
    if "}" in pattern[:open_at]:
        return None
    head, tail = pattern[:open_at], pattern[i + 1:]
    expanded: list[str] = []
    for choice in choices:
        more = _expand_braces(head + choice + tail)
        if more is None:
            return None
        expanded.extend(more)
        if len(expanded) > _MAX_ALTERNATIVES:
            return None
    return expanded
