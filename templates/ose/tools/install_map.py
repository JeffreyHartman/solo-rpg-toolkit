"""Install a built fog-of-war map into this campaign.

The stage directory holds `viewer/` (copied to `map/`) and `referee/` (merged
into `dungeon/map/`). Run it instead of copying by hand: the guard hook blocks
any main-session command that names those paths. It prints file counts only.
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS = (("viewer", ROOT / "map"), ("referee", ROOT / "dungeon" / "map"))
EMPTY_REVEAL = "window.REVEALED = [];\n"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("stage", type=Path, help="directory holding viewer/ and referee/")
args = ap.parse_args()

for name, _ in DESTINATIONS:
    if not (args.stage / name).is_dir():
        raise SystemExit(f"error: {args.stage / name} not found")

for name, dest in DESTINATIONS:
    shutil.copytree(args.stage / name, dest, dirs_exist_ok=True)
    count = sum(1 for p in (args.stage / name).rglob("*") if p.is_file())
    print(f"{name}: {count} files installed")

reveal = ROOT / "state" / "revealed.js"
if not reveal.exists():
    reveal.write_text(EMPTY_REVEAL)
    print("state/revealed.js created, nothing revealed")
