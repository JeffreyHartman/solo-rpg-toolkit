# Ironsworn Truths Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a markdown-only Claude Code skill (`skills/ironsworn-truths/`) that walks the player through locking the 11 Ironsworn setting truths at session zero, plus the reusable converter script that generates the skill's reference content from the `@datasworn/ironsworn-classic` JSON dataset.

**Architecture:** Pure-stdlib Python converter at `scripts/datasworn_to_truths.py` (TDD'd via pytest, importable through the existing `pythonpath` config). Converter is run once to produce the committed `skills/ironsworn-truths/truths.md` reference file. Skill content is hand-written markdown (`SKILL.md`) that drives the multi-turn workflow. Existing `skills/ironsworn/SKILL.md` gains a small soft-hook section that suggests this skill when truths are not yet locked.

**Tech Stack:** Python 3.11+ (stdlib only — `json`, `argparse`, `pathlib`), pytest, plain markdown for skills.

**Spec:** `docs/superpowers/specs/2026-04-24-ironsworn-truths-skill-design.md` (commit `96a6cde`).

---

## File structure

**Create:**
- `scripts/datasworn_to_truths.py` — converter (CLI + importable functions)
- `tests/test_datasworn_to_truths.py` — pytest unit tests for the converter
- `skills/ironsworn-truths/SKILL.md` — workflow markdown (frontmatter + body)
- `skills/ironsworn-truths/truths.md` — generated reference (output of converter, committed)

**Modify:**
- `pyproject.toml` — add `"scripts"` to pytest `pythonpath` so converter is importable
- `skills/ironsworn/SKILL.md` — add a "When truths are not yet locked" suggestion section
- `docs/ROADMAP.md` — add new "Datasworn ingestion" sub-project, mark the truths skill checkbox

---

## Task 1: ROADMAP entry for the new sub-project

Add a new sub-project section so progress is trackable from the start.

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Edit ROADMAP**

Insert after the existing Sub-project 3 section (before Sub-project 4):

```markdown
## Sub-project 3.5: Datasworn Ingestion (Ironsworn Truths)
First feature in a multi-step ingestion of the `@datasworn/ironsworn-classic` JSON dataset (`reference/datasworn-ironsworn-classic/`, CC-BY-4.0). Future features (oracles, moves, assets) are separate specs.

- [ ] Reusable converter `scripts/datasworn_to_truths.py` (pure stdlib, pytest-tested)
- [ ] Generated `skills/ironsworn-truths/truths.md` reference file
- [ ] New skill `skills/ironsworn-truths/SKILL.md` — multi-turn truth-locking workflow
- [ ] Soft hook from `skills/ironsworn/SKILL.md` ("truths not locked — want to set them up?")
- [ ] Spec: `docs/superpowers/specs/2026-04-24-ironsworn-truths-skill-design.md`
- [ ] Plan: `docs/superpowers/plans/2026-04-25-ironsworn-truths-skill.md`

---
```

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs: add datasworn ingestion sub-project to ROADMAP"
```

---

## Task 2: pytest config — make `scripts/` importable

Tests need to `import datasworn_to_truths`. The pytest `pythonpath` already lists `src`; add `scripts`.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit pyproject.toml**

Find the existing block:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Replace with:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "scripts"]
```

- [ ] **Step 2: Verify pytest still collects tests**

Run: `pytest --collect-only -q | tail -5`
Expected: existing tests still listed, no errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: add scripts/ to pytest pythonpath for converter tests"
```

---

## Task 3: Converter — `load_truths` (TDD)

`load_truths(path)` reads a datasworn JSON file and returns the `truths` dict. Raises `ValueError` (with explanatory message) if the file is missing the `truths` key or it is empty.

**Files:**
- Create: `scripts/datasworn_to_truths.py`
- Create: `tests/test_datasworn_to_truths.py`

- [ ] **Step 1: Create the script stub**

`scripts/datasworn_to_truths.py`:
```python
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
```

- [ ] **Step 2: Write the failing test**

`tests/test_datasworn_to_truths.py`:
```python
import json
from pathlib import Path

import pytest

import datasworn_to_truths as dt


def _write_json(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "datasworn.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_truths_returns_mapping(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {"truths": {"iron": {"name": "Iron"}}})
    result = dt.load_truths(src)
    assert result == {"iron": {"name": "Iron"}}


def test_load_truths_raises_when_key_missing(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {"oracles": {}})
    with pytest.raises(ValueError, match="missing top-level 'truths'"):
        dt.load_truths(src)


def test_load_truths_raises_when_empty(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {"truths": {}})
    with pytest.raises(ValueError, match="'truths' is empty"):
        dt.load_truths(src)
```

- [ ] **Step 3: Run tests and verify they pass**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: 3 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/datasworn_to_truths.py tests/test_datasworn_to_truths.py
git commit -m "feat: datasworn converter — load_truths with empty/missing guards"
```

---

## Task 4: Converter — `format_option` (TDD)

`format_option(option, letter)` formats one option block: `### Option <letter> (<min>–<max>)` heading, description prose, and an optional `**Quest seed:** ...` line.

**Files:**
- Modify: `scripts/datasworn_to_truths.py`
- Modify: `tests/test_datasworn_to_truths.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_datasworn_to_truths.py`:
```python
def test_format_option_basic() -> None:
    opt = {"min": 1, "max": 33, "description": "The Old World fell."}
    assert dt.format_option(opt, "A") == (
        "### Option A (1\u201333)\n"
        "\n"
        "The Old World fell.\n"
    )


def test_format_option_includes_quest_seed() -> None:
    opt = {
        "min": 34,
        "max": 67,
        "description": "Iron is cursed.",
        "quest_starter": "Find the unbound forge.",
    }
    out = dt.format_option(opt, "B")
    assert out == (
        "### Option B (34\u201367)\n"
        "\n"
        "Iron is cursed.\n"
        "\n"
        "**Quest seed:** Find the unbound forge.\n"
    )


def test_format_option_omits_quest_seed_when_absent() -> None:
    opt = {"min": 68, "max": 100, "description": "No seed here."}
    out = dt.format_option(opt, "C")
    assert "Quest seed" not in out
    assert out.endswith("No seed here.\n")
```

The `\u2013` escapes are the en dash (`–`).

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest tests/test_datasworn_to_truths.py::test_format_option_basic -v`
Expected: FAIL with `AttributeError: module 'datasworn_to_truths' has no attribute 'format_option'`.

- [ ] **Step 3: Implement `format_option`**

Append to `scripts/datasworn_to_truths.py`:
```python
EN_DASH = "\u2013"


def format_option(option: dict, letter: str) -> str:
    """Format one weighted option as a `### Option X (min–max)` block."""
    header = f"### Option {letter} ({option['min']}{EN_DASH}{option['max']})\n"
    body = f"\n{option['description']}\n"
    quest = option.get("quest_starter")
    if quest:
        body += f"\n**Quest seed:** {quest}\n"
    return header + body
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/datasworn_to_truths.py tests/test_datasworn_to_truths.py
git commit -m "feat: datasworn converter — format_option with weighted ranges and quest seed"
```

---

## Task 5: Converter — `format_truth` (TDD)

`format_truth(truth_id, truth)` formats a full truth section: `## <name>` heading, attribution line referencing the datasworn id, then each option formatted in order with letters A, B, C... by index.

**Files:**
- Modify: `scripts/datasworn_to_truths.py`
- Modify: `tests/test_datasworn_to_truths.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_datasworn_to_truths.py`:
```python
def test_format_truth_emits_heading_and_attribution() -> None:
    truth = {
        "_id": "classic/truths/iron",
        "name": "Iron",
        "options": [
            {"min": 1, "max": 50, "description": "First."},
            {"min": 51, "max": 100, "description": "Second."},
        ],
    }
    out = dt.format_truth("iron", truth)
    assert out.startswith("## Iron\n")
    assert "Datasworn id `classic/truths/iron`" in out
    assert "### Option A (1\u201350)" in out
    assert "### Option B (51\u2013100)" in out


def test_format_truth_letters_increment_for_more_options() -> None:
    truth = {
        "_id": "classic/truths/example",
        "name": "Example",
        "options": [
            {"min": 1, "max": 25, "description": "One."},
            {"min": 26, "max": 50, "description": "Two."},
            {"min": 51, "max": 75, "description": "Three."},
            {"min": 76, "max": 100, "description": "Four."},
        ],
    }
    out = dt.format_truth("example", truth)
    assert "### Option A " in out
    assert "### Option B " in out
    assert "### Option C " in out
    assert "### Option D " in out
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: 2 new tests FAIL on missing `format_truth`.

- [ ] **Step 3: Implement `format_truth`**

Append to `scripts/datasworn_to_truths.py`:
```python
def _option_letter(index: int) -> str:
    """0 -> A, 1 -> B, ..., 25 -> Z. Errors past 26."""
    if index >= 26:
        raise ValueError(f"option index {index} exceeds A-Z labelling")
    return chr(ord("A") + index)


def format_truth(truth_id: str, truth: dict) -> str:
    """Format a full truth section with heading, attribution, and options."""
    name = truth["name"]
    datasworn_id = truth.get("_id", f"classic/truths/{truth_id}")
    parts = [
        f"## {name}\n",
        f"\n**Source:** Ironsworn Rulebook (Shawn Tomkin, CC-BY-4.0). "
        f"Datasworn id `{datasworn_id}`.\n",
        "\n",
    ]
    for i, option in enumerate(truth["options"]):
        parts.append(format_option(option, _option_letter(i)))
        parts.append("\n")
    return "".join(parts).rstrip() + "\n"
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/datasworn_to_truths.py tests/test_datasworn_to_truths.py
git commit -m "feat: datasworn converter — format_truth with attribution + lettered options"
```

---

## Task 6: Converter — `format_document` (TDD)

`format_document(truths)` assembles the full `truths.md` content: top-of-file attribution header, then each truth in fixed book order. Truths in the input dict not in the order list are appended at the end alphabetically (defensive — keeps the converter from silently dropping data if datasworn adds new truths).

**Files:**
- Modify: `scripts/datasworn_to_truths.py`
- Modify: `tests/test_datasworn_to_truths.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_datasworn_to_truths.py`:
```python
def _truth(name: str, idx: int) -> dict:
    return {
        "_id": f"classic/truths/{name.lower().replace(' ', '_')}",
        "name": name,
        "options": [
            {"min": 1, "max": 100, "description": f"Only option for {name}."},
        ],
    }


def test_format_document_book_order() -> None:
    truths = {
        "iron": _truth("Iron", 1),
        "old_world": _truth("The Old World", 0),
    }
    out = dt.format_document(truths)
    old_pos = out.index("## The Old World")
    iron_pos = out.index("## Iron")
    assert old_pos < iron_pos


def test_format_document_includes_attribution_header() -> None:
    out = dt.format_document({"iron": _truth("Iron", 0)})
    assert out.startswith("# Ironsworn Setting Truths")
    assert "CC-BY-4.0" in out
    assert "https://ironswornrpg.com" in out


def test_format_document_appends_unknown_truths_alphabetically() -> None:
    truths = {
        "zeta": _truth("Zeta", 99),
        "alpha": _truth("Alpha", 98),
        "iron": _truth("Iron", 1),
    }
    out = dt.format_document(truths)
    iron_pos = out.index("## Iron")
    alpha_pos = out.index("## Alpha")
    zeta_pos = out.index("## Zeta")
    assert iron_pos < alpha_pos < zeta_pos


def test_format_document_idempotent() -> None:
    truths = {"iron": _truth("Iron", 1), "old_world": _truth("The Old World", 0)}
    assert dt.format_document(truths) == dt.format_document(truths)
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: 4 new tests FAIL on missing `format_document`.

- [ ] **Step 3: Implement `format_document`**

Append to `scripts/datasworn_to_truths.py`:
```python
TRUTH_ORDER = (
    "old_world",
    "iron",
    "legacies",
    "communities",
    "leaders",
    "defense",
    "mysticism",
    "religion",
    "firstborn",
    "beasts",
    "horrors",
)

DOC_HEADER = """\
# Ironsworn Setting Truths

**Source:** Ironsworn Rulebook by Shawn Tomkin. Licensed under CC-BY-4.0
(<https://creativecommons.org/licenses/by/4.0>). Original text:
<https://ironswornrpg.com>. Structured data via `@datasworn/ironsworn-classic`
(<https://github.com/rsek/datasworn>).

This file is generated by `scripts/datasworn_to_truths.py`. Do not edit by hand
— rerun the converter against an updated `classic.json` instead.

---
"""


def _ordered_truth_ids(truths: dict[str, dict]) -> list[str]:
    """Return truth keys in TRUTH_ORDER first, then unknown keys alphabetically."""
    known = [tid for tid in TRUTH_ORDER if tid in truths]
    extra = sorted(tid for tid in truths if tid not in TRUTH_ORDER)
    return known + extra


def format_document(truths: dict[str, dict]) -> str:
    """Render the full truths.md content from a truths mapping."""
    sections = [DOC_HEADER]
    for tid in _ordered_truth_ids(truths):
        sections.append("\n")
        sections.append(format_truth(tid, truths[tid]))
    return "".join(sections)
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/datasworn_to_truths.py tests/test_datasworn_to_truths.py
git commit -m "feat: datasworn converter — format_document in book order with attribution"
```

---

## Task 7: Converter — CLI entry point (TDD)

The script should be runnable directly with sane defaults (datasworn JSON at the known reference path, output at the known skill path). Both paths are overridable via flags. Exits non-zero with a clear message if the input file is missing.

**Files:**
- Modify: `scripts/datasworn_to_truths.py`
- Modify: `tests/test_datasworn_to_truths.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_datasworn_to_truths.py`:
```python
def test_main_writes_output_file(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {
        "truths": {"iron": {"_id": "classic/truths/iron", "name": "Iron",
                            "options": [{"min": 1, "max": 100, "description": "X"}]}}
    })
    out = tmp_path / "truths.md"
    rc = dt.main(["--datasworn", str(src), "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "## Iron" in text
    assert text.startswith("# Ironsworn Setting Truths")


def test_main_errors_on_missing_input(tmp_path: Path, capsys) -> None:
    out = tmp_path / "truths.md"
    rc = dt.main(["--datasworn", str(tmp_path / "nope.json"), "--out", str(out)])
    assert rc != 0
    err = capsys.readouterr().err
    assert "nope.json" in err


def test_main_creates_output_parent_dir(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {
        "truths": {"iron": {"_id": "classic/truths/iron", "name": "Iron",
                            "options": [{"min": 1, "max": 100, "description": "X"}]}}
    })
    out = tmp_path / "nested" / "truths.md"
    rc = dt.main(["--datasworn", str(src), "--out", str(out)])
    assert rc == 0
    assert out.exists()
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: 3 new tests FAIL on missing `main`.

- [ ] **Step 3: Implement `main`**

Append to `scripts/datasworn_to_truths.py`:
```python
import argparse
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASWORN = REPO_ROOT / "reference" / "datasworn-ironsworn-classic" / "json" / "classic.json"
DEFAULT_OUT = REPO_ROOT / "skills" / "ironsworn-truths" / "truths.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate skills/ironsworn-truths/truths.md from datasworn JSON."
    )
    parser.add_argument("--datasworn", type=Path, default=DEFAULT_DATASWORN,
                        help=f"Input datasworn JSON path (default: {DEFAULT_DATASWORN})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Output markdown path (default: {DEFAULT_OUT})")
    args = parser.parse_args(argv)

    if not args.datasworn.exists():
        print(f"error: input file not found: {args.datasworn}", file=sys.stderr)
        return 2

    try:
        truths = load_truths(args.datasworn)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(format_document(truths), encoding="utf-8")
    print(f"wrote {args.out} ({len(truths)} truths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest tests/test_datasworn_to_truths.py -v`
Expected: all 15 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/datasworn_to_truths.py tests/test_datasworn_to_truths.py
git commit -m "feat: datasworn converter — argparse CLI with defaults and error handling"
```

---

## Task 8: Generate the committed `truths.md`

Run the converter against the real datasworn JSON, sanity-check the output, commit it.

**Files:**
- Create: `skills/ironsworn-truths/truths.md` (generated)

- [ ] **Step 1: Run the converter**

```bash
python scripts/datasworn_to_truths.py
```
Expected stdout: `wrote /home/jeff/git/solo-rpg-toolkit/skills/ironsworn-truths/truths.md (11 truths)`.

- [ ] **Step 2: Sanity-check the output**

```bash
grep -c "^## " skills/ironsworn-truths/truths.md
grep -c "^### Option " skills/ironsworn-truths/truths.md
```
Expected: `11` and `33` (11 truths × 3 options).

- [ ] **Step 3: Spot-check the first truth**

Run: `head -40 skills/ironsworn-truths/truths.md`
Expected: doc-level attribution header, then `## The Old World` with three lettered options that include narrative description and a `**Quest seed:**` line each.

- [ ] **Step 4: Verify idempotence**

```bash
python scripts/datasworn_to_truths.py
git diff skills/ironsworn-truths/truths.md
```
Expected: no diff after the second run.

- [ ] **Step 5: Commit**

```bash
git add skills/ironsworn-truths/truths.md
git commit -m "feat: generate skills/ironsworn-truths/truths.md from datasworn"
```

---

## Task 9: Write `skills/ironsworn-truths/SKILL.md`

The workflow document the LLM follows when running the truths-locking skill.

**Files:**
- Create: `skills/ironsworn-truths/SKILL.md`

- [ ] **Step 1: Write the file**

```markdown
---
name: ironsworn-truths
description: Use when starting a new Ironsworn campaign and the player wants to lock in the 11 setting truths (Old World, Iron, Legacies, Communities, Leaders, Defense, Mysticism, Religion, Firstborn, Beasts, Horrors). Activates on phrases like "set up truths", "session zero", "establish my Ironsworn world", or when the ironsworn skill notices truths are not yet locked. Walks the player through each truth one at a time, supports picking a stock option, rolling d100, generating fresh options, or shaping the player's own world idea, and saves locked answers to the player's Obsidian vault plus a summary block in the campaign CLAUDE.md.
---

# Ironsworn Truths Skill

You walk the player through locking in the 11 Ironsworn setting truths. Each truth becomes a load-bearing fact for the rest of the campaign — take the time to make answers feel right.

## Reference data

`truths.md` (alongside this file) holds all 11 truths with their three weighted stock options and quest seeds. Read it on demand for the truth currently being decided. Do **not** dump the whole file into chat.

## Path resolution

1. Read `<campaign>/CLAUDE.md` (current working directory). Find the `PLAYER_VAULT_PATH:` line in the Configuration block.
2. If `PLAYER_VAULT_PATH` is missing or still set to the placeholder (`/CHANGE/ME/...`), stop. Tell the player to set it first, then re-run this skill.
3. Truth files live at `<PLAYER_VAULT_PATH>/Lore/Truths/<slug>.md`. Slugs use lowercase hyphenated names: `old-world.md`, `iron.md`, `legacies.md`, `communities.md`, `leaders.md`, `defense.md`, `mysticism.md`, `religion.md`, `firstborn.md`, `beasts.md`, `horrors.md`.
4. Create `<PLAYER_VAULT_PATH>/Lore/Truths/` on the first lock if it does not exist. If the vault root itself is missing, stop and ask the player to fix the path.

## Activation guard (always run first)

When the skill is invoked:

1. List the 11 truth slugs and check which files exist with frontmatter `locked: true`.
2. Report progress to the player: `"X of 11 truths locked."` Name the locked ones.
3. Offer choices:
   - Continue with the first unlocked truth.
   - Jump to a specific truth by name.
   - Revisit a locked truth (edit / replace / view).
   - Exit.

## Per-truth loop

For each truth the player wants to work on:

1. Read the matching `## <Truth Name>` section from `truths.md`. Present the player with:
   - The truth's name and a one-line summary of what this truth shapes (from your own knowledge of Ironsworn).
   - The three stock options labelled A / B / C with their d100 ranges and one-paragraph descriptions.
   - The quest seed for each option, kept brief at first — full text on request.

2. Offer five paths:
   - **A / B / C** — pick a stock option as written.
   - **Roll d100** — invoke `solo-roll roll 1d100` and announce which option the result lands in.
   - **Fresh options** — generate three new options grounded in Ironsworn's tone (low fantasy, iron-age, harsh, mythic). Show them with the same shape as the stock options.
   - **Riff on player idea** — the player offers a seed (e.g., "iron is alive and resentful"); you reflect it back as a polished one-paragraph option and an optional quest seed.
   - **Freeform** — the player writes their own answer in prose; you only help with phrasing.

3. **Iterate until lock.** Do not write to disk after one turn. The player may want several rounds of refinement, mixing fresh-options with riffs. Keep the conversation in this loop until they say something equivalent to "lock it."

4. Before locking, ask:
   - Whether the quest seed should be saved (some players opt out at session zero).
   - Whether they want to add freeform notes to the file (campaign-specific lore that does not fit the option text).

5. **Lock procedure** — when the player confirms:
   - Write `<PLAYER_VAULT_PATH>/Lore/Truths/<slug>.md` with the schema below. Overwrite if the file already exists.
   - Regenerate the campaign `CLAUDE.md` summary block (see "Summary block" below).
   - Confirm: `"Locked: <Truth Name>. Y of 11 truths locked."`

6. Ask whether to continue with the next unlocked truth or stop for now.

### Per-truth output schema

```markdown
---
locked: true
truth: <truth_id>
source: classic/truths/<truth_id>
chosen_option: <A|B|C|custom>
---

# <Truth Name>

<one-paragraph locked answer in the player's voice>

## Quest seed

<quest seed prose, or omit this entire section if the player opted out>

## Notes

<freeform notes, or omit this entire section if empty>
```

`chosen_option` is `A`, `B`, or `C` if the answer is the stock option text verbatim; `custom` otherwise (rolled-and-rewritten, riff, freeform, or fresh option).

## Summary block in campaign `CLAUDE.md`

Maintain a single fenced block at the end of `<campaign>/CLAUDE.md`. The block always lists all 11 truths in book order — unlocked ones render as `_(not yet locked)_`.

```markdown
<!-- BEGIN: ironsworn-truths-summary -->
## Setting Truths

- **The Old World**: <one-line locked summary>
- **Iron**: _(not yet locked)_
- **Legacies**: <one-line locked summary>
- **Communities**: _(not yet locked)_
- **Leaders**: _(not yet locked)_
- **Defense**: _(not yet locked)_
- **Mysticism**: _(not yet locked)_
- **Religion**: _(not yet locked)_
- **Firstborn**: _(not yet locked)_
- **Beasts**: _(not yet locked)_
- **Horrors**: _(not yet locked)_

(Full prose: `<vault>/Lore/Truths/`. Re-run `ironsworn-truths` skill to revise.)
<!-- END: ironsworn-truths-summary -->
```

**Update procedure** on every lock:
1. Re-read all 11 truth files in the vault. For each locked file, derive a one-line summary (≤ 100 chars) by taking the first sentence of the locked answer or asking the player if it doesn't fit.
2. Search `<campaign>/CLAUDE.md` for `<!-- BEGIN: ironsworn-truths-summary -->` ... `<!-- END: ironsworn-truths-summary -->`. Replace the entire block (including fences) with the regenerated version. If the start fence is absent, append the block at the end of the file.

The block's purpose: every future session loads campaign `CLAUDE.md`, so locked summaries are always in the LLM's context without re-reading the vault.

## Re-entry on a locked truth

If the player picks a truth that is already `locked: true`:

1. Show the current locked answer + quest seed + notes.
2. Offer three actions:
   - **Edit** — keep the lock, allow tweaking notes / quest seed / wording. Save back, regenerate summary block.
   - **Replace** — clear the file and restart the per-truth loop. Warn that downstream session notes may reference the previous answer.
   - **View** — read-only display, no changes.

## Mythic 2e graceful coupling

If `mythic-gme` skill is loaded (look for it in the skills list or any prior mention this session), include this option in the per-truth menu:

> **Mythic meaning pair** — invoke `solo-roll meaning-pair` for a two-word inspiration prompt; treat the pair as a seed and offer a riff.

If `mythic-gme` is not loaded, do **not** mention this option. Never auto-load it.

## Boundaries

- Never silently overwrite a locked truth. Always go through the re-entry flow.
- Never invent attribution or licensing language. The reference file already credits Shawn Tomkin and CC-BY-4.0.
- Do not generate quest seeds longer than ~3 sentences — they should hint, not script the campaign.
- Stay out of play. This skill runs at session zero (or revisits between sessions). Do not start scenes or invoke other Ironsworn moves while in the truth-locking loop.
```

- [ ] **Step 2: Sanity-check the file**

Run: `head -3 skills/ironsworn-truths/SKILL.md`
Expected: frontmatter starts with `---` and contains `name: ironsworn-truths`.

- [ ] **Step 3: Commit**

```bash
git add skills/ironsworn-truths/SKILL.md
git commit -m "feat: ironsworn-truths skill — workflow for locking 11 setting truths"
```

---

## Task 10: Soft hook in existing `skills/ironsworn/SKILL.md`

The existing Ironsworn skill should notice when truths are not yet locked and suggest loading `ironsworn-truths`. It must not auto-load any other skill — only suggest.

**Files:**
- Modify: `skills/ironsworn/SKILL.md`

- [ ] **Step 1: Add the suggestion section**

Open `skills/ironsworn/SKILL.md`. Find the existing `## When solo-journaler skill is also loaded` section. **Insert a new section immediately before it:**

```markdown
## Setting truths at session zero

Ironsworn campaigns are anchored by 11 setting truths (Old World, Iron, Legacies, Communities, Leaders, Defense, Mysticism, Religion, Firstborn, Beasts, Horrors). Before the first scene of a brand-new campaign, check whether truths are locked:

1. Resolve `PLAYER_VAULT_PATH` from `<campaign>/CLAUDE.md`.
2. List `<PLAYER_VAULT_PATH>/Lore/Truths/`. If the directory is missing or no files have frontmatter `locked: true`, the campaign has not been bootstrapped.
3. If unbootstrapped, ask the player once: "Setting truths are not yet locked. Want to set them up first? Load the `ironsworn-truths` skill and we'll walk through them. (Or skip if you already have a setting in mind — we can lock truths later.)"
4. Do **not** auto-load `ironsworn-truths`. The player decides.

If the campaign `CLAUDE.md` already contains a `## Setting Truths` summary block (between the `<!-- BEGIN: ironsworn-truths-summary -->` fences), the locked answers are loaded into your context at session start — refer to them when generating setting content. For deep references (a quest seed the player wants to adopt as a vow), read the full file from `<PLAYER_VAULT_PATH>/Lore/Truths/<slug>.md`.

```

- [ ] **Step 2: Verify the file is well-formed**

Run: `head -5 skills/ironsworn/SKILL.md`
Expected: existing frontmatter unchanged.

Run: `grep -n "Setting truths at session zero" skills/ironsworn/SKILL.md`
Expected: one match.

- [ ] **Step 3: Commit**

```bash
git add skills/ironsworn/SKILL.md
git commit -m "feat: ironsworn skill — suggest ironsworn-truths when truths not yet locked"
```

---

## Task 11: Final ROADMAP update

Tick the boxes for the items now shipped.

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Tick the completed items**

In the "Sub-project 3.5: Datasworn Ingestion (Ironsworn Truths)" section, change every `- [ ]` to `- [x]`.

- [ ] **Step 2: Verify**

Run: `grep -A 8 "Sub-project 3.5" docs/ROADMAP.md`
Expected: 6 ticked checkboxes.

- [ ] **Step 3: Final test sweep**

Run: `pytest --tb=short -q`
Expected: all tests pass (including the 13 new converter tests).

- [ ] **Step 4: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs: mark ironsworn-truths sub-project complete"
```

---

## Done criteria

- `pytest --tb=short -q` passes including 15 new tests in `tests/test_datasworn_to_truths.py`.
- `python scripts/datasworn_to_truths.py` runs cleanly against the real `classic.json` and produces zero diff against the committed `skills/ironsworn-truths/truths.md`.
- `skills/ironsworn-truths/` exists with `SKILL.md` and `truths.md`. `solo-campaign` discovers it automatically (via `_list_available_skills`) — no campaign-script change required.
- `skills/ironsworn/SKILL.md` includes the "Setting truths at session zero" section that suggests the new skill without auto-loading it.
- `docs/ROADMAP.md` shows the new sub-project with all checkboxes ticked.
