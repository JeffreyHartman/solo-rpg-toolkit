#!/usr/bin/env bash
# PreToolUse on Read: the main session may not read the dungeon key. Information
# hiding stops being a convention and becomes a wall. Ask the referee subagent.
set -euo pipefail
payload="$(cat)"
path="$(python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
except Exception:
    print(""); raise SystemExit
print(d.get("tool_input", {}).get("file_path", "") or "")
' <<<"$payload")"

case "$path" in
  */dungeon/level-*|*/dungeon/monsters/*|*/dungeon/index.json|*/dungeon/00-*)
    cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The dungeon key is hidden from this session on purpose. Use the referee subagent: Agent(subagent_type=\"referee\", prompt=\"Party enters room N from the <direction> with <light>. They are <doing what>.\"). It returns only what the party perceives."}}
JSON
    ;;
esac
