"""One-shot converter: legacy .txt tables -> JSON format used by solo-roll.

Run manually:
    python scripts/convert_txt_tables.py

Idempotent — rerunning overwrites existing JSON files.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
TOPLEVEL = [
    ("action1",     "Action (Meaning Table 1)",      "Mythic GME 2e, Actions Table 1"),
    ("action2",     "Action (Meaning Table 2)",      "Mythic GME 2e, Actions Table 2"),
    ("descriptor1", "Descriptor (Meaning Table 1)",  "Mythic GME 2e, Descriptors Table 1"),
    ("descriptor2", "Descriptor (Meaning Table 2)",  "Mythic GME 2e, Descriptors Table 2"),
]


def read_lines(path: Path) -> list[str]:
    lines = [line.rstrip() for line in path.read_text().splitlines()]
    return [line for line in lines if line != ""]


def convert_flat(name: str, display_name: str, source: str) -> None:
    src = DATA / f"{name}.txt"
    entries = read_lines(src)
    if len(entries) != 100:
        raise SystemExit(f"{src}: expected 100 entries, got {len(entries)}")
    out = DATA / "tables" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "name": name,
        "display_name": display_name,
        "dice": "d100",
        "source": source,
        "entries": entries,
    }, indent=2) + "\n")
    print(f"wrote {out.relative_to(REPO_ROOT)}")


def convert_element(src: Path) -> None:
    name = src.stem
    lines = [line.rstrip() for line in src.read_text().splitlines() if line.rstrip() != ""]
    if not lines:
        raise SystemExit(f"{src}: empty")
    header = lines[0]
    if not header.startswith("#"):
        raise SystemExit(f"{src}: expected first line to start with '#', got {header!r}")
    display_name = header.lstrip("# ").strip()
    entries = lines[1:]
    if len(entries) != 100:
        raise SystemExit(f"{src}: expected 100 entries after header, got {len(entries)}")
    out = DATA / "tables" / "elements" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "name": name,
        "display_name": display_name,
        "dice": "d100",
        "source": "solo-rpg-toolkit elements",
        "entries": entries,
    }, indent=2) + "\n")
    print(f"wrote {out.relative_to(REPO_ROOT)}")


def main() -> None:
    for name, display, source in TOPLEVEL:
        convert_flat(name, display, source)
    elements_src = DATA / "elements"
    if elements_src.is_dir():
        for txt in sorted(elements_src.glob("*.txt")):
            convert_element(txt)


if __name__ == "__main__":
    main()
