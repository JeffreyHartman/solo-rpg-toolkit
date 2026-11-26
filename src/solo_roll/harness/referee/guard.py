"""The Referee's path guard: which tool calls may run, and on which paths.

Both adapters call `PathGuard.check` before every tool call. In the Agent SDK
adapter it is the PreToolUse hook, which runs before the CLI's own permission
rules (ADR 0002).
"""
from pathlib import Path, PurePath
from typing import Any

from ..campaign import CampaignPaths

__all__ = ["ENGINE_TOOL_PREFIX", "FILE_TOOLS", "PathGuard"]

FILE_TOOLS = ("Read", "Write", "Edit", "Glob", "Grep")
ENGINE_TOOL_PREFIX = "mcp__engine__"
_WRITE_TOOLS = {"Write", "Edit"}
_GLOB_CHARS = set("*?[{")
_OUTSIDE = "The Referee can reach only the campaign vault and the referee folder."
_ENGINE_FILE = "The engine writes this file. Change mechanical state through the engine tools."


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
            return None
        searched = [tool_input.get("path")]
        pattern = tool_input.get("pattern" if tool == "Glob" else "glob")
        if isinstance(pattern, str):
            if ".." in PurePath(pattern).parts:
                return _OUTSIDE
            searched.append(_static_prefix(pattern))
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


def _static_prefix(pattern: str) -> str:
    """Return the leading parts of a glob pattern that hold no glob characters."""
    parts = []
    for part in PurePath(pattern).parts:
        if _GLOB_CHARS & set(part):
            break
        parts.append(part)
    return str(PurePath(*parts)) if parts else "."
