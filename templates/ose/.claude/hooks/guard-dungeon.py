#!/usr/bin/env python3
"""PreToolUse guard: only the referee subagent may touch dungeon/.

Claude Code puts agent_type in the hook payload for subagent tool calls and
omits the key for the main session. That is the only reliable discriminator.
Absolute paths in settings.json permission rules do not match, so this hook,
not a deny rule, is what enforces the split.
"""
import json
import sys

GUARDED = ("dungeon/level-", "dungeon/monsters/", "dungeon/index.json", "dungeon/00-")

REASON = (
    "The dungeon key is hidden from this session on purpose. Use the referee "
    'subagent: Agent(subagent_type="referee", prompt="Party enters room N from '
    'the <direction> with <light>. They are <doing what>."). It returns only '
    "what the party perceives."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("agent_type") == "referee":
        return 0

    tool_input = payload.get("tool_input") or {}
    if payload.get("tool_name") == "Bash":
        target = str(tool_input.get("command", ""))
    else:
        target = " ".join(
            str(tool_input.get(key, ""))
            for key in ("file_path", "path", "pattern", "glob")
        )

    if not any(marker in target for marker in GUARDED):
        return 0

    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": REASON,
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
