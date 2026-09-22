#!/usr/bin/env bash
# UserPromptSubmit: restate the clock in front of every message. A referee that
# is shown the turn and the light every turn cannot lose track of either.
set -euo pipefail
root="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
python3 - "$root" <<'PY'
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
lines = []
clock = root / "state/clock.json"
if clock.exists():
    s = json.loads(clock.read_text())
    lights = s.get("light") or []
    if lights:
        lit = ", ".join(f"{l.get('kind')} ({l.get('bearer')}) {l.get('turns_left')} turns"
                        for l in lights)
    else:
        lit = "NONE — the party is in darkness"
    lines.append(f"Dungeon turn {s.get('turn', 0)}, level {s.get('level')}, "
                 f"room {s.get('room') or 'between rooms'}.")
    lines.append(f"Light: {lit}.")
    since = s.get("turns_since_rest", 0)
    if since >= 6:
        lines.append(f"Rest is overdue ({since} turns). -1 to attack and damage until they rest one turn.")

party = root / "state/party.json"
if party.exists():
    p = json.loads(party.read_text())
    by = {c["name"]: c for c in p.get("characters", [])}
    order = p.get("marching_order") or list(by)
    who = ", ".join(f"{n} {by.get(n, {}).get('hp', '?')}/{by.get(n, {}).get('hp_max', '?')}"
                    for n in order)
    lines.append(f"Marching order and HP: {who}.")
    if p.get("light_bearer"):
        lines.append(f"Light is carried by {p['light_bearer']}.")

if lines:
    print("<game-state>")
    print("\n".join(lines))
    print("These numbers are authoritative. Do not restate them from memory.")
    print("</game-state>")
PY
