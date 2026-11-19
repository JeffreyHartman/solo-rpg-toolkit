#!/usr/bin/env python3
"""PreToolUse guard: only the referee subagent may touch dungeon/ and the map key.

Claude Code puts agent_type in the hook payload for subagent tool calls and
omits the key for the main session. That is the only reliable discriminator.
Absolute paths in settings.json permission rules do not match, so this hook,
not a deny rule, is what enforces the split.

Paths are resolved against the payload cwd and compared with the campaign root,
which is two levels above this file. Bash is checked token by token; it is a
best-effort guard against accidents, not a sandbox.
"""
import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD_DIRS = (ROOT / "dungeon", ROOT / "map")
ALLOWED_FILES = (ROOT / "map" / "index.html",)

# Substrings checked in the raw tool input, for payloads whose paths belong to
# a different root than this hook.
GUARDED = (
    "dungeon/level-", "dungeon/monsters/", "dungeon/index.json", "dungeon/00-",
    "dungeon/map/",
    # The fog viewer's assets. Its index.html is generic and stays readable.
    "map/map.png", "map/masks/", "map/patches/", "map/areas.",
)

REASON = (
    "The dungeon key is hidden from this session on purpose. Use the referee "
    'subagent: Agent(subagent_type="referee", prompt="Party enters room N from '
    'the <direction> with <light>. They are <doing what>."). It returns only '
    "what the party perceives. Searching rules/, state/, playervault/ or "
    "module.md by explicit path is allowed."
)

RECURSIVE_COMMANDS = {"rg", "ag", "ack", "fd", "find", "tree", "du"}
GREP_COMMANDS = {"grep", "egrep", "fgrep", "zgrep"}
SEARCH_TOOLS = {"rg", "ag", "ack"}
ARCHIVE_COMMANDS = {"tar", "zip", "rsync"}
INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "php", "awk",
                "gawk", "sed", "bash", "sh", "zsh", "eval", "xargs", "env"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "|&"}
GLOB_CHARS = set("*?[{")


def resolve(raw: str, cwd: Path) -> Path:
    path = Path(os.path.expanduser(raw))
    if not path.is_absolute():
        path = cwd / path
    return Path(os.path.normpath(path))


def resolve_or_cwd(raw: str, cwd: Path) -> Path:
    return resolve(raw, cwd) if raw else cwd


def forms(path: Path) -> list[Path]:
    return [path, Path(os.path.realpath(path))]


def inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def hits_guard(path: Path) -> bool:
    """True when path is a guarded directory, or lies under one, apart from
    the viewer's index.html."""
    for candidate in forms(path):
        if candidate in ALLOWED_FILES:
            continue
        if any(inside(candidate, guard) for guard in GUARD_DIRS):
            return True
    return False


def covers_guard(path: Path) -> bool:
    """True when a recursive search rooted at path would reach a guarded dir."""
    for candidate in forms(path):
        if any(inside(guard, candidate) for guard in GUARD_DIRS):
            return True
    return False


def expand_braces(text: str) -> list[str]:
    match = re.search(r"\{([^{}]*)\}", text)
    if not match:
        return [text]
    out: list[str] = []
    for option in match.group(1).split(","):
        out += expand_braces(text[:match.start()] + option + text[match.end():])
    return out


def pattern_reaches(pattern: str, cwd: Path, exact: bool) -> bool:
    """True when a glob could match a path under a guarded directory. With
    exact set, matching the guarded directory itself counts too (a shell
    expands the glob to it, and ls or grep -r then reads inside)."""
    for variant in expand_braces(pattern):
        parts = resolve(variant, cwd).parts
        for guard in GUARD_DIRS:
            if _parts_reach(parts, guard.parts, exact):
                return True
    return False


def _parts_reach(pattern: tuple, guard: tuple, exact: bool) -> bool:
    for i, part in enumerate(pattern):
        if i >= len(guard):
            return True
        if part == "**":
            return True
        if not fnmatch.fnmatchcase(guard[i], part):
            return False
    return exact and len(pattern) == len(guard)


def pattern_denied(pattern: str, cwd: Path, exact: bool = False) -> bool:
    if not pattern:
        return False
    if not GLOB_CHARS & set(pattern):
        path = resolve(pattern, cwd)
        return hits_guard(path)
    return pattern_reaches(pattern, cwd, exact)


def tool_denied(payload: dict, cwd: Path) -> bool:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}

    if tool == "Bash":
        return bash_denied(str(tool_input.get("command", "")), cwd)

    file_path = str(tool_input.get("file_path") or "")
    path = str(tool_input.get("path") or "")
    if file_path and hits_guard(resolve(file_path, cwd)):
        return True

    if tool == "Grep":
        root = resolve_or_cwd(path, cwd)
        return hits_guard(root) or covers_guard(root)

    if tool == "Glob":
        base = resolve_or_cwd(path, cwd)
        if hits_guard(base):
            return True
        return pattern_denied(str(tool_input.get("pattern") or ""), base)

    return bool(path) and hits_guard(resolve(path, cwd))


def strip_heredocs(command: str) -> str:
    lines, out, end = command.split("\n"), [], None
    for line in lines:
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        out.append(line)
        match = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line)
        if match:
            end = match.group(1)
    return "\n".join(out)


def tokens_of(line: str) -> list[str]:
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return line.split()


def bash_denied(command: str, cwd: Path) -> bool:
    for line in strip_heredocs(command).split("\n"):
        here = cwd
        segment: list[str] = []
        for token in tokens_of(line) + [";"]:
            if token not in SEPARATORS:
                segment.append(token)
                continue
            if segment and segment_denied(segment, here):
                return True
            if segment and segment[0] in ("cd", "pushd"):
                target = next((t for t in segment[1:] if not t.startswith("-")), "~")
                here = resolve(target, here)
            segment = []
    return False


def segment_denied(words: list[str], cwd: Path) -> bool:
    name = os.path.basename(words[0])
    args = words[1:]

    if name in INTERPRETERS:
        for arg in args:
            if re.search(r"(?<![\w-])dungeon(?![\w-])|(?<![\w-])map/(?!index\.html)", arg):
                return True

    flags = [a for a in args if a.startswith("-") and not a.startswith("--") and len(a) > 1]
    long_flags = [a for a in args if a.startswith("--")]
    positional = [a for a in args if not a.startswith("-")]

    recursive = name in RECURSIVE_COMMANDS
    if name in GREP_COMMANDS:
        recursive = any(set(f[1:]) & set("rR") for f in flags) or any(
            f in ("--recursive", "--dereference-recursive") for f in long_flags)
        positional = positional[1:]
    elif name in SEARCH_TOOLS:
        positional = positional[1:]
    elif name == "ls":
        recursive = any("R" in f[1:] for f in flags) or "--recursive" in long_flags
    elif name == "find":
        cut = next((i for i, a in enumerate(args) if a[:1] in "-(!"), len(args))
        positional = args[:cut]
    elif name in ARCHIVE_COMMANDS:
        recursive = True
    elif name == "cp":
        recursive = any(set(f[1:]) & set("rRa") for f in flags) or any(
            f in ("--recursive", "--archive") for f in long_flags)
    elif name == "git":
        recursive = bool(args) and args[0] in ("grep", "ls-files", "show", "log")

    if recursive and not positional:
        positional = ["."]
    if recursive and any(covers_guard(resolve(p, cwd)) for p in positional
                         if not GLOB_CHARS & set(p)):
        return True

    for word in args + words[:1]:
        for piece in re.split(r"[=:,]", word) if word.startswith("-") else [word]:
            if piece and pattern_denied(piece, cwd, exact=True):
                return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("agent_type") == "referee":
        return 0

    tool_input = payload.get("tool_input") or {}
    cwd = resolve(str(payload.get("cwd") or ROOT), ROOT)

    if payload.get("tool_name") == "Bash":
        raw = str(tool_input.get("command", ""))
    else:
        raw = " ".join(
            str(tool_input.get(key, ""))
            for key in ("file_path", "path", "pattern", "glob")
        )

    if not (any(marker in raw for marker in GUARDED) or tool_denied(payload, cwd)):
        return 0

    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": REASON,
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
