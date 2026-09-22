#!/usr/bin/env bash
# Party and clock state for the Claude Code status bar. Reads the same JSON the
# referee writes, so the bar cannot drift from the game.
set -euo pipefail
root="$(dirname "$(dirname "$(readlink -f "$0")")")"
clock="$root/state/clock.json"
party="$root/state/party.json"
[ -f "$clock" ] || exit 0

read -r turn level room light < <(python3 -c '
import json, sys
s = json.load(open(sys.argv[1]))
lights = s.get("light") or []
low = min((l.get("turns_left", 0) for l in lights), default=0)
print(s.get("turn", 0), s.get("level", "?"), s.get("room") or "-", low)
' "$clock")

pcs=""
if [ -f "$party" ]; then
  pcs="$(python3 -c '
import json, sys
p = json.load(open(sys.argv[1]))
order = p.get("marching_order") or []
by = {c["name"]: c for c in p.get("characters", [])}
out = []
for name in order or list(by):
    c = by.get(name, {})
    hp, mx = c.get("hp", "?"), c.get("hp_max", "?")
    mark = "!" if isinstance(hp, int) and isinstance(mx, int) and hp * 2 <= mx else ""
    out.append(f"{name[:4]} {hp}/{mx}{mark}")
print(" · ".join(out))
' "$party")"
fi

if [ "$light" -le 0 ]; then
  lightbit=$'\033[31mDARK\033[0m'
elif [ "$light" -le 2 ]; then
  lightbit=$'\033[33mlight '"$light"$'\033[0m'
else
  lightbit="light $light"
fi

printf '\033[36mL%s r%s\033[0m · turn %s · %s · %s' "$level" "$room" "$turn" "$lightbit" "$pcs"
