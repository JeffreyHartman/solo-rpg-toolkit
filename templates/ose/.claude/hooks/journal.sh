#!/usr/bin/env bash
# Stop: append the turn's state to the running session log so notes write
# themselves. The narration itself is written at session end; this is the
# mechanical spine the player can check a ruling against.
set -euo pipefail
root="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
python3 - "$root" <<'PY'
import json, sys
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])
clock = root / "state/clock.json"
if not clock.exists():
    raise SystemExit
s = json.loads(clock.read_text())

log_dir = root / "playervault/Session Log"
log_dir.mkdir(parents=True, exist_ok=True)
existing = sorted(log_dir.glob("Session [0-9][0-9][0-9].md"))
path = existing[-1] if existing else log_dir / "Session 001.md"
if not path.exists():
    path.write_text(f"---\nplayed: {date.today().isoformat()}\n---\n\n# Session 001\n\n## Turn log\n\n")

line = (f"- Turn {s.get('turn', 0)}: level {s.get('level')}, room {s.get('room') or '-'}, "
        f"light {sum(l.get('turns_left', 0) for l in (s.get('light') or []))} turns remaining\n")
text = path.read_text()
if line not in text.splitlines(keepends=True)[-1:]:
    with path.open("a") as fh:
        fh.write(line)
PY
