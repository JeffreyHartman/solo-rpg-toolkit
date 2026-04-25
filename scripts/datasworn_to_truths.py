"""One-shot converter: datasworn JSON -> truths.md skill reference.

Reads the @datasworn/ironsworn-classic JSON file and emits a markdown
reference with one section per truth (3 weighted options + quest seed each).

Run manually:
    python scripts/datasworn_to_truths.py

Idempotent — rerunning produces identical output.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_truths(path: Path) -> dict[str, dict]:
    """Load datasworn JSON, return the `truths` mapping. Raise on missing/empty."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    truths = raw.get("truths")
    if truths is None:
        raise ValueError(f"{path}: missing top-level 'truths' key")
    if not truths:
        raise ValueError(f"{path}: 'truths' is empty")
    return truths


EN_DASH = "\u2013"


def format_option(option: dict, letter: str) -> str:
    """Format one weighted option as a `### Option X (min–max)` block."""
    header = f"### Option {letter} ({option['min']}{EN_DASH}{option['max']})\n"
    body = f"\n{option['description']}\n"
    quest = option.get("quest_starter")
    if quest:
        body += f"\n**Quest seed:** {quest}\n"
    return header + body
