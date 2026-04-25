# solo-roll Core Library + Repo Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `solo-roll`, a Python CLI that owns all deterministic RNG, table lookup, Mythic fate-chart math, and quickset chain execution for the Solo RPG GM Assistant toolkit. Reorganize the repo into a src/tests/data/skills/reference layout. All downstream skills depend on this foundation.

**Architecture:** Single Python package (stdlib only), four modules (`rng`, `tables`, `charts`, `quicksets`) plus an `argparse` CLI. JSON tables in `data/tables/`, JSON charts in `data/charts/`, JSON quicksets in `data/quicksets/`. CLI outputs JSON to stdout, reads from a `DiceSource` that tests can substitute with scripted values.

**Tech Stack:** Python ≥ 3.10 (stdlib only — `argparse`, `json`, `random`, `pathlib`), `pytest` for tests, `hatchling` for packaging, `pipx` for install.

**Spec:** `docs/superpowers/specs/2026-04-19-solo-roll-core-design.md`

---

## File Structure

### Created

```
pyproject.toml
src/solo_roll/__init__.py
src/solo_roll/rng.py            # DiceSource protocol + RandomDice
src/solo_roll/tables.py         # JSON loader, roll_table
src/solo_roll/charts.py         # fate chart loader + threshold math + fate_check
src/solo_roll/quicksets.py      # quickset loader + run_quickset
src/solo_roll/cli.py            # argparse entry, subcommand dispatch
tests/conftest.py               # shared fixtures (scripted DiceSource)
tests/test_rng.py
tests/test_tables.py
tests/test_charts.py
tests/test_quicksets.py
tests/test_cli.py
scripts/convert_txt_tables.py   # one-shot converter (kept as utility, not re-run)
data/tables/action1.json
data/tables/action2.json
data/tables/descriptor1.json
data/tables/descriptor2.json
data/tables/elements/*.json     # 45 files
data/charts/mythic-fate.json
data/quicksets/npc_profile.json
data/quicksets/location_profile.json
data/quicksets/creature_profile.json
reference/                      # moved from pdfs/; gitignored
reference/mythic2e.md           # moved from data/mythic2e.md
```

### Modified

- `.gitignore` — already added in spec commit; verify `/reference/` entry active.
- `README.md` — add "Install the `solo-roll` CLI" section and a layout note.

### Deleted (after conversion)

- `data/action1.txt`, `data/action2.txt`, `data/descriptor1.txt`, `data/descriptor2.txt`
- `data/elements/` (entire directory, superseded by `data/tables/elements/`)
- `data/quicksets.json` (split into per-file directory)
- `pdfs/` (renamed to `reference/`)

---

## Task 1: Pre-flight — commit existing content, move reference material

**Rationale:** Before any restructuring, capture the current repo state as a baseline commit. Then move large binary reference material out of tracked paths.

**Files:**
- Move: `pdfs/` → `reference/`
- Move: `data/mythic2e.md` → `reference/mythic2e.md`

- [ ] **Step 1: Verify clean working tree with only spec commit**

Run: `git log --oneline`
Expected: One commit — the design-spec commit from brainstorming.

Run: `git status`
Expected: Untracked entries for `README.md`, `data/`, `example-campaign/`, `skills/`. `pdfs/` should NOT appear (already gitignored).

- [ ] **Step 2: Stage and commit existing content as initial import**

```bash
git add README.md data/ example-campaign/ skills/
git status
```

Expected: staged files include `README.md`, all of `data/*` (except `data/mythic2e.md` if the `.gitignore` rule catches it — check), `example-campaign/*`, `skills/*`. `data/mythic2e.md` should NOT be staged (gitignored via `.gitignore`).

```bash
git commit -m "$(cat <<'EOF'
chore: initial import of existing toolkit content

Captures README, current skills (ironsworn, mythic-gme, solo-journaler),
example-campaign template, and raw Mythic/element tables in data/. Baseline
before repo-cleanup sub-project rearranges files.
EOF
)"
```

- [ ] **Step 3: Move reference material**

```bash
mkdir -p reference
mv pdfs/mythic reference/mythic
rmdir pdfs
mv data/mythic2e.md reference/mythic2e.md
ls reference/
```

Expected: `reference/mythic/` contains three PDFs. `reference/mythic2e.md` exists. `pdfs/` no longer exists. `data/mythic2e.md` no longer exists.

- [ ] **Step 4: Verify gitignore catches the moves**

Run: `git status --ignored`
Expected: `reference/` listed under ignored. No staged changes (only the previous commit exists).

Run: `git ls-files data/mythic2e.md`
Expected: empty — the file was never tracked (was gitignored from the start), so the move is a plain filesystem rename with no git tracking implications.

- [ ] **Step 5: Commit the removal of `pdfs/` from tracking (none — it was never tracked)**

`pdfs/` was added to `.gitignore` in the design-spec commit before any content was tracked, so there is nothing to commit here. Skip this step if `git status` is clean.

If `git status` shows `pdfs/` as "deleted" (possible if git was tracking it from an earlier state), run:

```bash
git add -A pdfs/
git commit -m "chore: remove pdfs/ from tracking (moved to gitignored reference/)"
```

---

## Task 2: Scaffold Python package + editable install

**Files:**
- Create: `pyproject.toml`
- Create: `src/solo_roll/__init__.py`
- Create: `src/solo_roll/cli.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "solo-roll"
version = "0.1.0"
description = "Deterministic dice, table lookup, and Mythic chart math for the Solo RPG GM Assistant toolkit"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
solo-roll = "solo_roll.cli:main"

[project.optional-dependencies]
dev = ["pytest>=7"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/solo_roll"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Write `src/solo_roll/__init__.py`**

```python
from pathlib import Path

__version__ = "0.1.0"

_PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = _PACKAGE_DIR.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data"
```

- [ ] **Step 3: Write minimal `src/solo_roll/cli.py`**

```python
import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="solo-roll")
    parser.add_argument("--version", action="version", version=f"solo-roll {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False  # will become True once subcommands land

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Write empty `tests/conftest.py` placeholder**

```python
# Shared pytest fixtures land here as later tasks add them.
```

- [ ] **Step 5: Install editable + verify**

```bash
pipx install --editable .
which solo-roll
solo-roll --version
```

Expected:
- `pipx` confirms install with `installed package solo-roll 0.1.0`.
- `which solo-roll` prints a path under `~/.local/bin/` (or equivalent).
- `solo-roll --version` prints `solo-roll 0.1.0`.

If `pipx install --editable .` errors that editable installs need a different option in your pipx version, use `pipx install -e .`.

- [ ] **Step 6: Run the (empty) test suite**

```bash
pip install pytest   # if not already available in an environment you can run pytest in
pytest
```

Expected: pytest reports no tests collected and exits 0 (or 5 — "no tests ran"; both are acceptable while the suite is empty).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "$(cat <<'EOF'
feat(solo-roll): scaffold package, CLI entry, pyproject

Minimal editable install — `pipx install -e .` produces a working `solo-roll`
binary that only understands `--version`. Subcommands added in later tasks.
EOF
)"
```

---

## Task 3: DiceSource abstraction + `rng.py` (TDD)

**Rationale:** All modules take a `DiceSource` rather than calling `random` directly. Tests inject a `ScriptedDice` that yields a controlled sequence; production wraps `random.Random`.

**Files:**
- Create: `src/solo_roll/rng.py`
- Create: `tests/test_rng.py`
- Modify: `tests/conftest.py` (add `scripted_dice` fixture)

- [ ] **Step 1: Write the failing tests**

Write `tests/test_rng.py`:

```python
import pytest

from solo_roll.rng import RandomDice, ScriptedDice


def test_scripted_dice_yields_in_order():
    dice = ScriptedDice([3, 7, 1])
    assert dice.roll(1, 10) == 3
    assert dice.roll(1, 10) == 7
    assert dice.roll(1, 10) == 1


def test_scripted_dice_raises_when_exhausted():
    dice = ScriptedDice([5])
    dice.roll(1, 10)
    with pytest.raises(RuntimeError):
        dice.roll(1, 10)


def test_scripted_dice_validates_against_bounds():
    # A scripted value outside [low, high] is a test-authoring bug and must fail loudly.
    dice = ScriptedDice([11])
    with pytest.raises(ValueError):
        dice.roll(1, 10)


def test_random_dice_stays_in_bounds():
    dice = RandomDice(seed=0)
    for _ in range(100):
        value = dice.roll(1, 10)
        assert 1 <= value <= 10


def test_random_dice_reproducible_with_same_seed():
    a = RandomDice(seed=42)
    b = RandomDice(seed=42)
    for _ in range(20):
        assert a.roll(1, 100) == b.roll(1, 100)
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_rng.py -v`
Expected: All tests fail with `ModuleNotFoundError: No module named 'solo_roll.rng'`.

- [ ] **Step 3: Implement `src/solo_roll/rng.py`**

```python
import random
from typing import Protocol


class DiceSource(Protocol):
    def roll(self, low: int, high: int) -> int: ...


class RandomDice:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def roll(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)


class ScriptedDice:
    def __init__(self, values: list[int]):
        self._values = list(values)
        self._index = 0

    def roll(self, low: int, high: int) -> int:
        if self._index >= len(self._values):
            raise RuntimeError(
                f"ScriptedDice exhausted after {self._index} rolls"
            )
        value = self._values[self._index]
        self._index += 1
        if not (low <= value <= high):
            raise ValueError(
                f"ScriptedDice value {value} out of bounds [{low}, {high}]"
            )
        return value
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_rng.py -v`
Expected: 5 passed.

- [ ] **Step 5: Add shared fixture to `tests/conftest.py`**

Replace `tests/conftest.py` with:

```python
import pytest

from solo_roll.rng import ScriptedDice


@pytest.fixture
def scripted_dice():
    def _make(values: list[int]) -> ScriptedDice:
        return ScriptedDice(values)
    return _make
```

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/rng.py tests/test_rng.py tests/conftest.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add DiceSource abstraction with scripted + random impls

ScriptedDice yields a fixed sequence for tests and raises on bound violations
or exhaustion (both are test bugs). RandomDice wraps random.Random with
optional seed. All downstream modules take a DiceSource rather than touching
random directly, which keeps tests deterministic without coupling assertions
to stdlib call order.
EOF
)"
```

---

## Task 4: `tables.py` loader + `roll_table` (TDD)

**Rationale:** Generic JSON table loader with schema validation. Supports flat (`entries: [...]`) and ranged (`ranges: [...]`) shapes (the latter is schema-ready for future event-focus tables; not rolled by any v1 subcommand directly but validated on load). Rolls use an injected `DiceSource`.

**Files:**
- Create: `src/solo_roll/tables.py`
- Create: `tests/test_tables.py`

- [ ] **Step 1: Write the failing tests**

Write `tests/test_tables.py`:

```python
import json
from pathlib import Path

import pytest

from solo_roll.tables import (
    TableDataError,
    TableNotFoundError,
    load_table,
    roll_table,
)


DICE_MAP = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "tables").mkdir(parents=True)
    return root


def test_load_flat_table(data_dir: Path):
    _write_json(
        data_dir / "tables" / "sample.json",
        {
            "name": "sample",
            "display_name": "Sample",
            "dice": "d4",
            "source": "test",
            "entries": ["a", "b", "c", "d"],
        },
    )
    table = load_table("sample", data_dir)
    assert table["name"] == "sample"
    assert table["entries"] == ["a", "b", "c", "d"]
    assert table["dice"] == "d4"


def test_load_nested_table(data_dir: Path):
    _write_json(
        data_dir / "tables" / "nested" / "child.json",
        {"name": "child", "dice": "d4", "entries": ["w", "x", "y", "z"]},
    )
    table = load_table("nested/child", data_dir)
    assert table["name"] == "child"


def test_flat_table_entry_count_mismatch_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "bad.json",
        {"name": "bad", "dice": "d6", "entries": ["only", "three", "entries"]},
    )
    with pytest.raises(TableDataError):
        load_table("bad", data_dir)


def test_ranged_table_loads_and_validates_coverage(data_dir: Path):
    _write_json(
        data_dir / "tables" / "ranged.json",
        {
            "name": "ranged",
            "dice": "d10",
            "ranges": [
                {"min": 1, "max": 3, "result": "low"},
                {"min": 4, "max": 7, "result": "mid"},
                {"min": 8, "max": 10, "result": "high"},
            ],
        },
    )
    table = load_table("ranged", data_dir)
    assert len(table["ranges"]) == 3


def test_ranged_table_gap_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "gap.json",
        {
            "name": "gap",
            "dice": "d10",
            "ranges": [
                {"min": 1, "max": 3, "result": "low"},
                {"min": 5, "max": 10, "result": "high"},  # missing 4
            ],
        },
    )
    with pytest.raises(TableDataError):
        load_table("gap", data_dir)


def test_ranged_table_overlap_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "overlap.json",
        {
            "name": "overlap",
            "dice": "d10",
            "ranges": [
                {"min": 1, "max": 5, "result": "low"},
                {"min": 5, "max": 10, "result": "high"},  # 5 in both
            ],
        },
    )
    with pytest.raises(TableDataError):
        load_table("overlap", data_dir)


def test_table_with_both_entries_and_ranges_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "both.json",
        {
            "name": "both",
            "dice": "d4",
            "entries": ["a", "b", "c", "d"],
            "ranges": [{"min": 1, "max": 4, "result": "x"}],
        },
    )
    with pytest.raises(TableDataError):
        load_table("both", data_dir)


def test_unknown_table_raises(data_dir: Path):
    with pytest.raises(TableNotFoundError):
        load_table("missing", data_dir)


def test_roll_table_flat_returns_index_and_result(data_dir: Path, scripted_dice):
    _write_json(
        data_dir / "tables" / "sample.json",
        {"name": "sample", "dice": "d4", "entries": ["a", "b", "c", "d"]},
    )
    result = roll_table("sample", data_dir, scripted_dice([3]))
    assert result["table"] == "sample"
    assert result["dice"] == "d4"
    assert result["roll"] == 3
    assert result["result"] == "c"


def test_roll_table_flat_edge_positions(data_dir: Path, scripted_dice):
    _write_json(
        data_dir / "tables" / "sample.json",
        {"name": "sample", "dice": "d4", "entries": ["a", "b", "c", "d"]},
    )
    assert roll_table("sample", data_dir, scripted_dice([1]))["result"] == "a"
    assert roll_table("sample", data_dir, scripted_dice([4]))["result"] == "d"


def test_dice_map_is_complete():
    for key, faces in DICE_MAP.items():
        assert int(key[1:]) == faces
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_tables.py -v`
Expected: Import errors — `tables` module and its symbols do not exist.

- [ ] **Step 3: Implement `src/solo_roll/tables.py`**

```python
import json
from pathlib import Path
from typing import Any

from .rng import DiceSource


DICE_FACES: dict[str, int] = {
    "d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100,
}


class TableError(Exception):
    """Base error for table module."""


class TableNotFoundError(TableError):
    """Raised when a table name cannot be resolved to a file."""


class TableDataError(TableError):
    """Raised when a table file's contents violate the schema."""


def _table_path(name: str, data_dir: Path) -> Path:
    return data_dir / "tables" / f"{name}.json"


def load_table(name: str, data_dir: Path) -> dict[str, Any]:
    path = _table_path(name, data_dir)
    if not path.exists():
        raise TableNotFoundError(f"Table not found: {name} (looked in {path})")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise TableDataError(f"Invalid JSON in {path}: {exc}") from exc

    _validate(payload, path)
    return payload


def _validate(payload: dict[str, Any], path: Path) -> None:
    dice = payload.get("dice")
    if dice not in DICE_FACES:
        raise TableDataError(f"{path}: unknown dice '{dice}'")
    faces = DICE_FACES[dice]

    has_entries = "entries" in payload
    has_ranges = "ranges" in payload
    if has_entries and has_ranges:
        raise TableDataError(f"{path}: both 'entries' and 'ranges' present")
    if not has_entries and not has_ranges:
        raise TableDataError(f"{path}: neither 'entries' nor 'ranges' present")

    if has_entries:
        entries = payload["entries"]
        if not isinstance(entries, list) or len(entries) != faces:
            raise TableDataError(
                f"{path}: expected {faces} entries for {dice}, got {len(entries) if isinstance(entries, list) else type(entries).__name__}"
            )
        return

    # Ranged — validate coverage.
    ranges = payload["ranges"]
    if not isinstance(ranges, list) or not ranges:
        raise TableDataError(f"{path}: ranges must be a non-empty list")
    covered: set[int] = set()
    for band in ranges:
        low = band.get("min")
        high = band.get("max")
        if not isinstance(low, int) or not isinstance(high, int):
            raise TableDataError(f"{path}: range min/max must be ints")
        if low > high or low < 1 or high > faces:
            raise TableDataError(f"{path}: range {low}-{high} invalid for {dice}")
        for value in range(low, high + 1):
            if value in covered:
                raise TableDataError(f"{path}: range value {value} overlaps")
            covered.add(value)
    missing = set(range(1, faces + 1)) - covered
    if missing:
        raise TableDataError(f"{path}: ranges do not cover {sorted(missing)}")


def roll_table(name: str, data_dir: Path, dice: DiceSource) -> dict[str, Any]:
    table = load_table(name, data_dir)
    faces = DICE_FACES[table["dice"]]
    roll = dice.roll(1, faces)

    if "entries" in table:
        result = table["entries"][roll - 1]
    else:
        result = _lookup_range(table["ranges"], roll)

    return {
        "table": name,
        "display_name": table.get("display_name", table["name"]),
        "dice": table["dice"],
        "roll": roll,
        "result": result,
    }


def _lookup_range(ranges: list[dict[str, Any]], roll: int) -> str:
    for band in ranges:
        if band["min"] <= roll <= band["max"]:
            return band["result"]
    raise TableDataError(f"roll {roll} not covered by ranges (loader should have rejected)")
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_tables.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/tables.py tests/test_tables.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add tables module with flat + ranged schema support

load_table validates: dice name, entry count matches faces, ranges cover
1..N with no gaps or overlaps, entries/ranges mutually exclusive. roll_table
returns roll index and result using an injected DiceSource. Ranged schema
isn't rolled by any v1 subcommand directly but is accepted so future
event-focus JSON drops in with no code change.
EOF
)"
```

---

## Task 5: Convert top-level action/descriptor .txt → JSON

**Rationale:** Existing `data/action1.txt`, `action2.txt`, `descriptor1.txt`, `descriptor2.txt` are 100 lines each (no header). Convert to JSON via a one-shot script kept in `scripts/` as a utility (not a build step — it's never re-run automatically).

**Files:**
- Create: `scripts/convert_txt_tables.py`
- Create: `data/tables/action1.json`, `action2.json`, `descriptor1.json`, `descriptor2.json`
- Delete: `data/action1.txt`, `action2.txt`, `descriptor1.txt`, `descriptor2.txt`

- [ ] **Step 1: Write `scripts/convert_txt_tables.py`**

```python
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
```

- [ ] **Step 2: Run the converter for the four top-level files**

The script's `main()` handles both top-level and elements conversion. For this task we only exercise the top-level pass (elements directory is handled in Task 6). Running it now produces element JSON as well — that is fine; we'll just defer committing those files until Task 6 so the commits stay thematic.

Run:
```bash
python scripts/convert_txt_tables.py
```

Expected output (order may vary):
```
wrote data/tables/action1.json
wrote data/tables/action2.json
wrote data/tables/descriptor1.json
wrote data/tables/descriptor2.json
wrote data/tables/elements/adventuretone.json
...
```

- [ ] **Step 3: Verify the four top-level JSON files load cleanly**

```bash
python -c "from solo_roll.tables import load_table; from pathlib import Path; d=Path('data'); [print(load_table(n, d)['name'], len(load_table(n, d)['entries'])) for n in ['action1','action2','descriptor1','descriptor2']]"
```

Expected:
```
action1 100
action2 100
descriptor1 100
descriptor2 100
```

- [ ] **Step 4: Delete the four top-level .txt files**

```bash
rm data/action1.txt data/action2.txt data/descriptor1.txt data/descriptor2.txt
```

- [ ] **Step 5: Re-run existing tests — should still pass**

Run: `pytest -v`
Expected: all tests in `test_rng.py` and `test_tables.py` pass.

- [ ] **Step 6: Stage only the top-level files for this commit**

```bash
git add scripts/convert_txt_tables.py
git add data/tables/action1.json data/tables/action2.json data/tables/descriptor1.json data/tables/descriptor2.json
git rm data/action1.txt data/action2.txt data/descriptor1.txt data/descriptor2.txt
git status
```

Expected: staged — new script, four new JSON tables, four deleted .txt files. Element JSON files (if produced in Step 2) remain unstaged for Task 6.

- [ ] **Step 7: Commit**

```bash
git commit -m "$(cat <<'EOF'
data: convert top-level action/descriptor tables from .txt to JSON

action1, action2, descriptor1, descriptor2 each had 100 plain-text lines with
no header. Converted to self-describing JSON (name, display_name, dice,
source, entries) so the loader can validate and future tables follow the same
format. Converter kept in scripts/ as a utility for future element tables;
it is not a build step.
EOF
)"
```

---

## Task 6: Convert `data/elements/*.txt` → JSON

**Rationale:** 45 files with `# Header` + 100 entries each. Same converter script handles them.

**Files:**
- Create: `data/tables/elements/*.json` (45 files)
- Delete: `data/elements/` (entire directory)

- [ ] **Step 1: Run converter (no-op if Task 5 already wrote the element JSON)**

```bash
python scripts/convert_txt_tables.py
ls data/tables/elements/ | wc -l
```

Expected: `45`.

- [ ] **Step 2: Verify every element file loads as a valid d100 table**

```bash
python <<'PY'
from pathlib import Path
from solo_roll.tables import load_table

root = Path("data/tables/elements")
names = sorted(p.stem for p in root.glob("*.json"))
for name in names:
    table = load_table(f"elements/{name}", Path("data"))
    assert len(table["entries"]) == 100, name
print(f"ok: {len(names)} element tables")
PY
```

Expected: `ok: 45 element tables`.

- [ ] **Step 3: Delete the legacy `data/elements/` directory**

```bash
rm -rf data/elements
ls data/
```

Expected: `data/` now contains only `tables/`, `charts/` (if created yet), `quicksets.json`. No `elements/` subdir.

- [ ] **Step 4: Add integrity test that scans real data**

Append to `tests/test_tables.py`:

```python
def test_all_shipped_tables_load_from_real_data():
    from solo_roll import DEFAULT_DATA_DIR
    tables_root = DEFAULT_DATA_DIR / "tables"
    json_files = sorted(tables_root.rglob("*.json"))
    assert len(json_files) >= 49, f"expected at least 49 shipped tables, found {len(json_files)}"
    for path in json_files:
        rel_name = path.relative_to(tables_root).with_suffix("").as_posix()
        table = load_table(rel_name, DEFAULT_DATA_DIR)
        assert "entries" in table or "ranges" in table
```

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all prior tests plus the new integrity test pass.

- [ ] **Step 6: Commit**

```bash
git add data/tables/elements/ tests/test_tables.py
git rm -r data/elements/
git commit -m "$(cat <<'EOF'
data: convert elements/*.txt to data/tables/elements/*.json

45 element tables (character/location/creature/etc.), each d100 with a header
line converted to display_name and 100 entries. Added an integrity test that
scans every shipped table and validates it loads under the full schema.
EOF
)"
```

---

## Task 7: `solo-roll table <name>` subcommand (TDD)

**Files:**
- Modify: `src/solo_roll/cli.py`
- Modify: `tests/test_cli.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
import json
import subprocess


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["solo-roll", *args],
        capture_output=True,
        text=True,
    )


def test_table_subcommand_returns_required_keys():
    result = _run("table", "action1", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["table"] == "action1"
    assert payload["dice"] == "d100"
    assert 1 <= payload["roll"] <= 100
    assert isinstance(payload["result"], str) and payload["result"]


def test_table_subcommand_nested_path():
    result = _run("table", "elements/plottwist", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["table"] == "elements/plottwist"


def test_table_subcommand_unknown_table_exits_1():
    result = _run("table", "does_not_exist", "--seed", "0")
    assert result.returncode == 1
    assert "not found" in result.stderr.lower() or "does_not_exist" in result.stderr


def test_table_subcommand_same_seed_is_reproducible():
    a = _run("table", "action1", "--seed", "42")
    b = _run("table", "action1", "--seed", "42")
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_cli.py -v`
Expected: tests fail — `table` subcommand does not exist yet (argparse rejects it).

- [ ] **Step 3: Extend `src/solo_roll/cli.py`**

Replace the contents of `src/solo_roll/cli.py` with:

```python
import argparse
import json
import os
import sys
from pathlib import Path

from . import DEFAULT_DATA_DIR, __version__
from .rng import DiceSource, RandomDice
from .tables import TableDataError, TableNotFoundError, roll_table


def _resolve_data_dir(cli_arg: str | None) -> Path:
    if cli_arg:
        return Path(cli_arg)
    env = os.environ.get("SOLO_ROLL_DATA")
    if env:
        return Path(env)
    user_override = Path.home() / ".config" / "solo-roll" / "data"
    if user_override.exists():
        return user_override
    return DEFAULT_DATA_DIR


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--data", type=str, default=None)


def _dice(args: argparse.Namespace) -> DiceSource:
    return RandomDice(seed=args.seed)


def _cmd_table(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    try:
        payload = roll_table(args.name, data_dir, _dice(args))
    except TableNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except TableDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="solo-roll")
    parser.add_argument("--version", action="version", version=f"solo-roll {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = False

    p_table = subparsers.add_parser("table", help="Roll a single table by name")
    p_table.add_argument("name", help="Table name, e.g. action1 or elements/plottwist")
    _add_common_args(p_table)
    p_table.set_defaults(func=_cmd_table)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Reinstall is not needed (editable install picks up edits automatically)**

Verify:
```bash
solo-roll table action1 --seed 0
```

Expected: JSON with keys `table`, `display_name`, `dice`, `roll`, `result`.

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_cli.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/cli.py tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add `solo-roll table <name>` subcommand

Rolls any shipped table by name (flat path or nested like elements/plottwist).
--seed flag threads through for reproducibility; --data overrides the data
directory (env var SOLO_ROLL_DATA or ~/.config/solo-roll/data/ also honored,
in that precedence). Unknown table -> exit 1; corrupt data -> exit 2. Output
is pretty-printed JSON on stdout.
EOF
)"
```

---

## Task 8: `charts.py` threshold math + d100 reading (TDD, pure functions)

**Files:**
- Create: `src/solo_roll/charts.py`
- Create: `tests/test_charts.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_charts.py`:

```python
import pytest

from solo_roll.charts import (
    classify_outcome,
    is_random_event,
    read_d100,
    thresholds,
)


def test_thresholds_formula_mid():
    result = thresholds(yes_threshold=75)
    assert result.yes_threshold == 75
    assert result.exceptional_yes_cap == 15  # 75 // 5
    assert result.exceptional_no_floor == 95  # 100 - ((100 - 75) // 5) = 100 - 5


def test_thresholds_formula_low():
    result = thresholds(yes_threshold=5)
    assert result.exceptional_yes_cap == 1   # 5 // 5
    assert result.exceptional_no_floor == 81 # 100 - ((100 - 5) // 5) = 100 - 19


def test_thresholds_formula_high():
    result = thresholds(yes_threshold=95)
    assert result.exceptional_yes_cap == 19  # 95 // 5
    assert result.exceptional_no_floor == 99 # 100 - ((100 - 95) // 5) = 100 - 1


def test_read_d100_double_zero_is_100():
    assert read_d100(0, 0) == 100


def test_read_d100_standard_pairs():
    assert read_d100(4, 3) == 43
    assert read_d100(9, 0) == 90
    assert read_d100(0, 7) == 7
    assert read_d100(1, 1) == 11


def test_read_d100_rejects_out_of_range():
    with pytest.raises(ValueError):
        read_d100(10, 0)
    with pytest.raises(ValueError):
        read_d100(-1, 0)


def test_classify_outcome_exceptional_yes():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(10, t) == ("exceptional_yes", True)


def test_classify_outcome_yes():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(43, t) == ("yes", False)


def test_classify_outcome_no():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(80, t) == ("no", False)


def test_classify_outcome_exceptional_no():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(97, t) == ("exceptional_no", True)


def test_classify_outcome_boundary_exact_yes_threshold_is_yes():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(75, t) == ("yes", False)


def test_classify_outcome_boundary_exact_exceptional_yes_cap_is_exceptional():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(15, t) == ("exceptional_yes", True)


def test_classify_outcome_boundary_exact_exceptional_no_floor_is_exceptional():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(95, t) == ("exceptional_no", True)


def test_is_random_event_doubles_under_cf_fires():
    assert is_random_event(4, 4, cf=5) is True


def test_is_random_event_doubles_above_cf_does_not_fire():
    assert is_random_event(4, 4, cf=3) is False


def test_is_random_event_doubles_equal_cf_fires():
    assert is_random_event(5, 5, cf=5) is True


def test_is_random_event_non_doubles_never_fires():
    assert is_random_event(4, 3, cf=9) is False
    assert is_random_event(0, 1, cf=9) is False


def test_is_random_event_double_zero_does_not_fire_unless_cf_allows():
    # d1 is 0 in the dice sense; per Mythic, "both dice equal" rule applies on raw d10 face.
    # 0 == 0 is doubles. 0 <= any CF (>=1) so it fires at any CF.
    assert is_random_event(0, 0, cf=1) is True
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_charts.py -v`
Expected: import error — `charts` module does not exist.

- [ ] **Step 3: Implement `src/solo_roll/charts.py`** (math only; chart loading added in Task 9)

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    yes_threshold: int
    exceptional_yes_cap: int
    exceptional_no_floor: int


def thresholds(yes_threshold: int) -> Thresholds:
    if not (1 <= yes_threshold <= 99):
        raise ValueError(f"yes_threshold out of range: {yes_threshold}")
    exc_yes = yes_threshold // 5
    exc_no = 100 - ((100 - yes_threshold) // 5)
    return Thresholds(
        yes_threshold=yes_threshold,
        exceptional_yes_cap=exc_yes,
        exceptional_no_floor=exc_no,
    )


def read_d100(d1: int, d2: int) -> int:
    for d in (d1, d2):
        if not (0 <= d <= 9):
            raise ValueError(f"d10 face out of range [0,9]: {d}")
    if d1 == 0 and d2 == 0:
        return 100
    return d1 * 10 + d2


def classify_outcome(roll: int, t: Thresholds) -> tuple[str, bool]:
    """Returns (outcome, is_exceptional)."""
    if roll <= t.exceptional_yes_cap:
        return "exceptional_yes", True
    if roll <= t.yes_threshold:
        return "yes", False
    if roll >= t.exceptional_no_floor:
        return "exceptional_no", True
    return "no", False


def is_random_event(d1: int, d2: int, cf: int) -> bool:
    return d1 == d2 and d1 <= cf
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_charts.py -v`
Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/charts.py tests/test_charts.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add charts math — thresholds, d100 read, classification

Pure functions, no RNG and no file I/O:
- thresholds(yes) -> Thresholds(yes, exc_yes_cap, exc_no_floor)
- read_d100(d1, d2) with (0,0) -> 100 per Mythic convention
- classify_outcome(roll, t) -> (outcome, is_exceptional)
- is_random_event(d1, d2, cf) -> doubles under CF

Boundary cases covered: exact yes_threshold -> yes, exact exc_no_floor -> exc_no,
(0,0) doubles fire at any CF >= 1.
EOF
)"
```

---

## Task 9: Mythic fate chart JSON + `fate_check` (TDD)

**Files:**
- Create: `data/charts/mythic-fate.json`
- Modify: `src/solo_roll/charts.py` (add loader + `fate_check`)
- Modify: `tests/test_charts.py` (add loader + `fate_check` tests)

- [ ] **Step 1: Write the failing tests**

In `tests/test_charts.py`, merge these imports into the existing top-of-file import block (next to the existing `from solo_roll.charts import ...` block), then append the test functions at the bottom of the file:

```python
from pathlib import Path

from solo_roll import DEFAULT_DATA_DIR
from solo_roll.charts import (
    FateChartError,
    KnownLikelihood,
    fate_check,
    load_fate_chart,
)


def test_fate_chart_loads_with_nine_likelihoods_and_nine_cfs():
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    assert len(chart.likelihoods) == 9
    for key in chart.likelihoods:
        assert len(chart.thresholds[key]) == 9
        for value in chart.thresholds[key]:
            assert 1 <= value <= 99


def test_fate_chart_likelihoods_match_known_set():
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    expected = {
        "has_to_be", "near_sure_thing", "very_likely", "likely",
        "50_50", "unlikely", "very_unlikely", "near_impossible", "no_way",
    }
    assert set(chart.likelihoods) == expected


def test_fate_chart_thresholds_monotonic_in_cf():
    # Each likelihood row should be weakly non-decreasing from CF 1 -> 9
    # (you can't get LESS likely to say yes as chaos rises, per Mythic design).
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    for key, row in chart.thresholds.items():
        for i in range(1, len(row)):
            assert row[i] >= row[i - 1], f"{key} not monotonic at CF {i+1}: {row}"


def test_fate_check_returns_complete_payload(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([4, 3])  # 43 -> yes at likely/CF5 (threshold 75)
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["likelihood"] == "likely"
    assert payload["cf"] == 5
    assert payload["yes_threshold"] == 75
    assert payload["exceptional_yes_cap"] == 15
    assert payload["exceptional_no_floor"] == 95
    assert payload["dice"] == [4, 3]
    assert payload["roll"] == 43
    assert payload["outcome"] == "yes"
    assert payload["exceptional"] is False
    assert payload["random_event_triggered"] is False


def test_fate_check_doubles_under_cf_triggers_event(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([4, 4])  # doubles, 4 <= CF 5
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["random_event_triggered"] is True


def test_fate_check_doubles_above_cf_does_not_trigger_event(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([7, 7])
    payload = fate_check("likely", cf=3, chart=chart, dice=dice)
    assert payload["random_event_triggered"] is False


def test_fate_check_exceptional_yes(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([0, 5])  # roll 5, <= exc_yes_cap 15 at likely/CF5
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["outcome"] == "exceptional_yes"
    assert payload["exceptional"] is True


def test_fate_check_exceptional_no(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([9, 7])  # roll 97, >= exc_no_floor 95 at likely/CF5
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["outcome"] == "exceptional_no"
    assert payload["exceptional"] is True


def test_fate_check_double_zero_rolls_100(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([0, 0])  # rolls 100 -> no or exceptional_no
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["roll"] == 100
    assert payload["outcome"] in ("no", "exceptional_no")


def test_fate_check_unknown_likelihood_raises(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    with pytest.raises(FateChartError):
        fate_check("definitely_not_a_key", cf=5, chart=chart, dice=scripted_dice([4, 3]))


def test_fate_check_cf_out_of_range_raises(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    with pytest.raises(FateChartError):
        fate_check("likely", cf=0, chart=chart, dice=scripted_dice([4, 3]))
    with pytest.raises(FateChartError):
        fate_check("likely", cf=10, chart=chart, dice=scripted_dice([4, 3]))


def test_known_likelihoods_is_frozen_set():
    assert isinstance(KnownLikelihood, frozenset)
    assert "likely" in KnownLikelihood
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_charts.py -v`
Expected: import errors — `load_fate_chart`, `fate_check`, `FateChartError`, `KnownLikelihood` not defined; `data/charts/mythic-fate.json` not present.

- [ ] **Step 3: Write `data/charts/mythic-fate.json`**

Create the file:

```json
{
  "name": "mythic-fate",
  "source": "Mythic GME 2e",
  "likelihoods": [
    "has_to_be",
    "near_sure_thing",
    "very_likely",
    "likely",
    "50_50",
    "unlikely",
    "very_unlikely",
    "near_impossible",
    "no_way"
  ],
  "thresholds": {
    "has_to_be":       [85, 90, 92, 94, 95, 96, 97, 98, 99],
    "near_sure_thing": [75, 82, 85, 88, 90, 92, 94, 96, 98],
    "very_likely":     [65, 72, 76, 80, 85, 88, 92, 94, 96],
    "likely":          [50, 58, 65, 72, 75, 82, 85, 88, 92],
    "50_50":           [25, 35, 45, 50, 50, 55, 65, 75, 85],
    "unlikely":        [10, 15, 20, 25, 25, 32, 40, 45, 50],
    "very_unlikely":   [ 5,  8, 12, 15, 15, 18, 25, 30, 35],
    "near_impossible": [ 3,  5,  7, 10, 10, 12, 15, 20, 25],
    "no_way":          [ 1,  2,  3,  5,  5,  7, 10, 15, 20]
  }
}
```

- [ ] **Step 4: Extend `src/solo_roll/charts.py`**

Append to `src/solo_roll/charts.py`:

```python
import json
from pathlib import Path
from typing import Any

from .rng import DiceSource


KnownLikelihood = frozenset({
    "has_to_be", "near_sure_thing", "very_likely", "likely",
    "50_50", "unlikely", "very_unlikely", "near_impossible", "no_way",
})


class FateChartError(Exception):
    """Raised when fate-chart loading or lookup fails."""


@dataclass(frozen=True)
class FateChart:
    likelihoods: tuple[str, ...]
    thresholds: dict[str, tuple[int, ...]]


def load_fate_chart(data_dir: Path) -> FateChart:
    path = data_dir / "charts" / "mythic-fate.json"
    if not path.exists():
        raise FateChartError(f"Fate chart not found: {path}")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise FateChartError(f"Invalid JSON in {path}: {exc}") from exc

    likelihoods = tuple(payload.get("likelihoods", []))
    if set(likelihoods) != KnownLikelihood:
        raise FateChartError(f"{path}: likelihoods do not match known set")

    raw_thresholds = payload.get("thresholds", {})
    thresholds_out: dict[str, tuple[int, ...]] = {}
    for key in likelihoods:
        row = raw_thresholds.get(key)
        if not isinstance(row, list) or len(row) != 9:
            raise FateChartError(f"{path}: thresholds[{key}] must be list of 9 ints")
        for value in row:
            if not isinstance(value, int) or not (1 <= value <= 99):
                raise FateChartError(f"{path}: threshold {value} out of range for {key}")
        thresholds_out[key] = tuple(row)

    return FateChart(likelihoods=likelihoods, thresholds=thresholds_out)


def fate_check(
    likelihood: str,
    cf: int,
    chart: FateChart,
    dice: DiceSource,
) -> dict[str, Any]:
    if likelihood not in chart.thresholds:
        raise FateChartError(f"Unknown likelihood: {likelihood}")
    if not (1 <= cf <= 9):
        raise FateChartError(f"CF out of range [1,9]: {cf}")

    yes_threshold = chart.thresholds[likelihood][cf - 1]
    t = thresholds(yes_threshold)

    d1 = dice.roll(0, 9)
    d2 = dice.roll(0, 9)
    roll = read_d100(d1, d2)
    outcome, is_exc = classify_outcome(roll, t)
    event = is_random_event(d1, d2, cf)

    return {
        "likelihood": likelihood,
        "cf": cf,
        "yes_threshold": t.yes_threshold,
        "exceptional_yes_cap": t.exceptional_yes_cap,
        "exceptional_no_floor": t.exceptional_no_floor,
        "dice": [d1, d2],
        "roll": roll,
        "outcome": outcome,
        "exceptional": is_exc,
        "random_event_triggered": event,
    }
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_charts.py -v`
Expected: all prior chart tests still pass plus the new ones (roughly 16 + 12 = 28 passed).

- [ ] **Step 6: Commit**

```bash
git add data/charts/mythic-fate.json src/solo_roll/charts.py tests/test_charts.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add fate chart JSON + fate_check

Chart lives in data/charts/mythic-fate.json (same drop-in philosophy as
tables). Loader validates: all 9 known likelihoods present, each row is 9
ints in [1,99]. fate_check pulls the yes threshold for (likelihood, cf),
derives exceptional caps via the pure math from the earlier commit, rolls
2d10 through the injected DiceSource, classifies, and reports random-event
firing. Unknown likelihood or CF out of [1,9] raises FateChartError.

Chart values copied from the current skills/mythic-gme/fate-check.md
placeholder; flagged in the design spec for cross-check against the Mythic
2e PDF during the Mythic sub-project (not blocking here).
EOF
)"
```

---

## Task 10: `solo-roll fate-check` subcommand (TDD)

**Files:**
- Modify: `src/solo_roll/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
FATE_REQUIRED_KEYS = {
    "likelihood", "cf", "yes_threshold", "exceptional_yes_cap",
    "exceptional_no_floor", "dice", "roll", "outcome", "exceptional",
    "random_event_triggered",
}


def test_fate_check_returns_required_keys():
    result = _run("fate-check", "--likelihood", "likely", "--cf", "5", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) >= FATE_REQUIRED_KEYS
    assert payload["likelihood"] == "likely"
    assert payload["cf"] == 5
    assert payload["outcome"] in {"yes", "no", "exceptional_yes", "exceptional_no"}
    assert isinstance(payload["exceptional"], bool)
    assert isinstance(payload["random_event_triggered"], bool)
    assert len(payload["dice"]) == 2


def test_fate_check_unknown_likelihood_exits_1():
    result = _run("fate-check", "--likelihood", "bogus", "--cf", "5")
    assert result.returncode == 1


def test_fate_check_cf_out_of_range_exits_1():
    result = _run("fate-check", "--likelihood", "likely", "--cf", "99")
    assert result.returncode == 1


def test_fate_check_reproducible_with_seed():
    a = _run("fate-check", "--likelihood", "likely", "--cf", "5", "--seed", "123")
    b = _run("fate-check", "--likelihood", "likely", "--cf", "5", "--seed", "123")
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_cli.py -v`
Expected: tests fail — `fate-check` subcommand does not exist.

- [ ] **Step 3: Extend `src/solo_roll/cli.py`**

Add imports and a handler. In `src/solo_roll/cli.py`:

Replace the imports block with:
```python
import argparse
import json
import os
import sys
from pathlib import Path

from . import DEFAULT_DATA_DIR, __version__
from .charts import FateChartError, fate_check, load_fate_chart
from .rng import DiceSource, RandomDice
from .tables import TableDataError, TableNotFoundError, roll_table
```

Add the handler (place after `_cmd_table`):
```python
def _cmd_fate_check(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    try:
        chart = load_fate_chart(data_dir)
        payload = fate_check(args.likelihood, args.cf, chart, _dice(args))
    except FateChartError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0
```

Register the subparser (inside `main`, after the `table` parser block):
```python
    p_fate = subparsers.add_parser("fate-check", help="Mythic fate check")
    p_fate.add_argument("--likelihood", required=True)
    p_fate.add_argument("--cf", type=int, required=True)
    _add_common_args(p_fate)
    p_fate.set_defaults(func=_cmd_fate_check)
```

- [ ] **Step 4: Smoke test manually**

```bash
solo-roll fate-check --likelihood likely --cf 5 --seed 0
```

Expected: JSON with all required keys.

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_cli.py -v`
Expected: table tests plus four new fate-check tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/cli.py tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add `solo-roll fate-check --likelihood --cf` subcommand

Invokes charts.fate_check and emits the full payload as JSON. Bad likelihood
or CF out of [1,9] -> exit 1 with message on stderr.
EOF
)"
```

---

## Task 11: `solo-roll meaning-pair` subcommand (TDD)

**Files:**
- Modify: `src/solo_roll/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py`:

```python
def test_meaning_pair_defaults_action1_descriptor1():
    result = _run("meaning-pair", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"action", "description"}
    assert payload["action"]["table"] == "action1"
    assert payload["description"]["table"] == "descriptor1"
    for side in ("action", "description"):
        assert set(payload[side].keys()) >= {"table", "roll", "result"}


def test_meaning_pair_custom_tables_flag():
    result = _run("meaning-pair", "--tables", "action2,descriptor2", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"]["table"] == "action2"
    assert payload["description"]["table"] == "descriptor2"


def test_meaning_pair_bad_tables_flag_exits_1():
    result = _run("meaning-pair", "--tables", "only_one")
    assert result.returncode == 1
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_cli.py::test_meaning_pair_defaults_action1_descriptor1 -v`
Expected: fail — subcommand not registered.

- [ ] **Step 3: Extend `src/solo_roll/cli.py`**

Add the handler (after `_cmd_fate_check`):
```python
def _cmd_meaning_pair(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    tables_arg = args.tables
    parts = [t.strip() for t in tables_arg.split(",") if t.strip()]
    if len(parts) != 2:
        print(f"error: --tables expects two comma-separated names, got {tables_arg!r}", file=sys.stderr)
        return 1
    action_name, desc_name = parts
    dice = _dice(args)
    try:
        action = roll_table(action_name, data_dir, dice)
        description = roll_table(desc_name, data_dir, dice)
    except TableNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except TableDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = {
        "action":      {"table": action["table"],      "roll": action["roll"],      "result": action["result"]},
        "description": {"table": description["table"], "roll": description["roll"], "result": description["result"]},
    }
    print(json.dumps(payload, indent=2))
    return 0
```

Register the subparser (in `main`, after `p_fate` block):
```python
    p_pair = subparsers.add_parser("meaning-pair", help="Roll Mythic Meaning Tables (action + descriptor)")
    p_pair.add_argument("--tables", default="action1,descriptor1",
                        help="Comma-separated pair of table names (default action1,descriptor1)")
    _add_common_args(p_pair)
    p_pair.set_defaults(func=_cmd_meaning_pair)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_cli.py -v`
Expected: all prior tests plus three new pass.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/cli.py tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add `solo-roll meaning-pair` subcommand

Rolls an action + descriptor pair in one call. Defaults to action1/descriptor1
(Mythic 2e Meaning Tables); --tables override allows action2/descriptor2 or
future specialized tables. Malformed --tables -> exit 1.
EOF
)"
```

---

## Task 12: Split `data/quicksets.json` + add `quicksets.py` (TDD)

**Files:**
- Create: `data/quicksets/npc_profile.json`, `location_profile.json`, `creature_profile.json`
- Delete: `data/quicksets.json`
- Create: `src/solo_roll/quicksets.py`
- Create: `tests/test_quicksets.py`

- [ ] **Step 1: Split the legacy quicksets file**

Write `data/quicksets/npc_profile.json`:

```json
{
  "id": "npc_profile",
  "name": "NPC Profile",
  "description": "Complete NPC dossier with identity, personality, and background",
  "steps": [
    {"label": "Identity",    "table": "elements/characteridentity"},
    {"label": "Description", "table": "elements/characterdescription"},
    {"label": "Appearance",  "table": "elements/characterappearance"},
    {"label": "Background",  "table": "elements/characterbackground"},
    {"label": "Personality", "table": "elements/characterpersonality"},
    {"label": "Motivation",  "table": "elements/charactermotivation"},
    {"label": "Skills",      "table": "elements/characterskills"},
    {"label": "Trait",       "table": "elements/charactertrait"}
  ]
}
```

Write `data/quicksets/location_profile.json`:

```json
{
  "id": "location_profile",
  "name": "Location Profile",
  "description": "Generates details for a location or place of interest",
  "steps": [
    {"label": "Type",        "table": "elements/location"},
    {"label": "Description", "table": "descriptor1"},
    {"label": "Atmosphere",  "table": "elements/adventuretone"},
    {"label": "Feature",     "table": "descriptor1"},
    {"label": "Detail",      "table": "descriptor2"}
  ]
}
```

Write `data/quicksets/creature_profile.json`:

```json
{
  "id": "creature_profile",
  "name": "Creature Profile",
  "description": "Generates details for a creature or monster",
  "steps": [
    {"label": "Type",        "table": "elements/creature"},
    {"label": "Abilities",   "table": "elements/creatureabilities"},
    {"label": "Description", "table": "elements/characterdescription"},
    {"label": "Behavior",    "table": "elements/animalaction"}
  ]
}
```

Then:
```bash
rm data/quicksets.json
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_quicksets.py`:

```python
from pathlib import Path

import pytest

from solo_roll import DEFAULT_DATA_DIR
from solo_roll.quicksets import (
    QuicksetDataError,
    QuicksetNotFoundError,
    load_quickset,
    run_quickset,
)


def test_load_npc_profile():
    qs = load_quickset("npc_profile", DEFAULT_DATA_DIR)
    assert qs["id"] == "npc_profile"
    assert len(qs["steps"]) == 8


def test_load_unknown_quickset_raises():
    with pytest.raises(QuicksetNotFoundError):
        load_quickset("bogus_profile", DEFAULT_DATA_DIR)


def test_every_shipped_quickset_loads_and_tables_resolve():
    root = DEFAULT_DATA_DIR / "quicksets"
    ids = sorted(p.stem for p in root.glob("*.json"))
    assert len(ids) >= 3
    from solo_roll.tables import load_table
    for qs_id in ids:
        qs = load_quickset(qs_id, DEFAULT_DATA_DIR)
        for step in qs["steps"]:
            # Raises if the referenced table doesn't resolve.
            load_table(step["table"], DEFAULT_DATA_DIR)


def test_run_quickset_emits_one_result_per_step(scripted_dice):
    qs = load_quickset("npc_profile", DEFAULT_DATA_DIR)
    dice = scripted_dice([1] * len(qs["steps"]))
    payload = run_quickset("npc_profile", DEFAULT_DATA_DIR, dice)
    assert payload["id"] == "npc_profile"
    assert payload["name"] == "NPC Profile"
    assert len(payload["steps"]) == len(qs["steps"])
    for result_step, spec_step in zip(payload["steps"], qs["steps"]):
        assert result_step["label"] == spec_step["label"]
        assert result_step["table"] == spec_step["table"]
        assert "roll" in result_step and "result" in result_step


def test_run_quickset_missing_table_raises(tmp_path):
    # Build a throwaway quickset that points at a table that doesn't exist.
    import json
    data = tmp_path / "data"
    (data / "quicksets").mkdir(parents=True)
    (data / "tables").mkdir(parents=True)
    (data / "quicksets" / "broken.json").write_text(json.dumps({
        "id": "broken",
        "name": "Broken",
        "description": "",
        "steps": [{"label": "X", "table": "does_not_exist"}],
    }))
    from solo_roll.rng import ScriptedDice
    with pytest.raises(QuicksetDataError):
        run_quickset("broken", data, ScriptedDice([1]))
```

- [ ] **Step 3: Run tests — expect failure**

Run: `pytest tests/test_quicksets.py -v`
Expected: import error — `solo_roll.quicksets` doesn't exist.

- [ ] **Step 4: Implement `src/solo_roll/quicksets.py`**

```python
import json
from pathlib import Path
from typing import Any

from .rng import DiceSource
from .tables import TableError, roll_table


class QuicksetError(Exception):
    """Base error for quicksets module."""


class QuicksetNotFoundError(QuicksetError):
    pass


class QuicksetDataError(QuicksetError):
    pass


def _quickset_path(qs_id: str, data_dir: Path) -> Path:
    return data_dir / "quicksets" / f"{qs_id}.json"


def load_quickset(qs_id: str, data_dir: Path) -> dict[str, Any]:
    path = _quickset_path(qs_id, data_dir)
    if not path.exists():
        raise QuicksetNotFoundError(f"Quickset not found: {qs_id} (looked in {path})")
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise QuicksetDataError(f"Invalid JSON in {path}: {exc}") from exc
    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        raise QuicksetDataError(f"{path}: 'steps' must be a non-empty list")
    for idx, step in enumerate(steps):
        if not isinstance(step, dict) or "label" not in step or "table" not in step:
            raise QuicksetDataError(f"{path}: step {idx} missing label/table")
    return payload


def run_quickset(qs_id: str, data_dir: Path, dice: DiceSource) -> dict[str, Any]:
    qs = load_quickset(qs_id, data_dir)
    results = []
    for step in qs["steps"]:
        try:
            rolled = roll_table(step["table"], data_dir, dice)
        except TableError as exc:
            raise QuicksetDataError(f"quickset {qs_id}: {exc}") from exc
        results.append({
            "label": step["label"],
            "table": step["table"],
            "roll": rolled["roll"],
            "result": rolled["result"],
        })
    return {
        "id": qs["id"],
        "name": qs["name"],
        "steps": results,
    }
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/test_quicksets.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add data/quicksets/ src/solo_roll/quicksets.py tests/test_quicksets.py
git rm data/quicksets.json
git commit -m "$(cat <<'EOF'
feat(solo-roll): split quicksets into per-file JSON + add loader/runner

One file per chain under data/quicksets/ (npc_profile, location_profile,
creature_profile). run_quickset resolves each step's table through the
existing loader, rolls it with the injected DiceSource, and returns a struct
mirroring the CLI contract. Missing step table surfaces as QuicksetDataError
so the CLI can translate to exit code 2.
EOF
)"
```

---

## Task 13: `solo-roll quickset <id>` subcommand (TDD)

**Files:**
- Modify: `src/solo_roll/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py`:

```python
def test_quickset_npc_profile_runs_end_to_end():
    result = _run("quickset", "npc_profile", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == "npc_profile"
    assert payload["name"] == "NPC Profile"
    assert len(payload["steps"]) == 8
    for step in payload["steps"]:
        assert {"label", "table", "roll", "result"} <= step.keys()
        assert 1 <= step["roll"] <= 100


def test_quickset_unknown_id_exits_1():
    result = _run("quickset", "not_a_real_quickset")
    assert result.returncode == 1
```

- [ ] **Step 2: Run tests — expect failure**

Run: `pytest tests/test_cli.py::test_quickset_npc_profile_runs_end_to_end -v`
Expected: fail — `quickset` subcommand not registered.

- [ ] **Step 3: Extend `src/solo_roll/cli.py`**

Add to imports:
```python
from .quicksets import QuicksetDataError, QuicksetNotFoundError, run_quickset
```

Add handler (after `_cmd_meaning_pair`):
```python
def _cmd_quickset(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    try:
        payload = run_quickset(args.id, data_dir, _dice(args))
    except QuicksetNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except QuicksetDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2))
    return 0
```

Register in `main` (after `p_pair`):
```python
    p_qs = subparsers.add_parser("quickset", help="Run a quickset chain")
    p_qs.add_argument("id", help="Quickset id, e.g. npc_profile")
    _add_common_args(p_qs)
    p_qs.set_defaults(func=_cmd_quickset)
```

- [ ] **Step 4: Smoke test**

```bash
solo-roll quickset npc_profile --seed 0
solo-roll quickset location_profile --seed 0
solo-roll quickset creature_profile --seed 0
```

Expected: three JSON outputs, each with steps matching the chain length (8, 5, 4).

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: all tests across rng, tables, charts, quicksets, cli pass. Count should be roughly 50+ tests.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/cli.py tests/test_cli.py
git commit -m "$(cat <<'EOF'
feat(solo-roll): add `solo-roll quickset <id>` subcommand

Runs a chain end-to-end with one DiceSource threaded through every step.
Unknown id -> exit 1; malformed quickset or missing step table -> exit 2.
EOF
)"
```

---

## Task 14: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README to preserve existing sections**

Run: `cat README.md`

The existing README documents skill install + per-campaign setup. Leave those sections intact (skill rewrites belong to a later sub-project). Add a new section near the top that covers the `solo-roll` CLI and the repo layout.

- [ ] **Step 2: Insert the new section**

Edit `README.md` — after the opening paragraph (under `# Solo RPG Toolkit for Claude Code`), insert:

```markdown
## Install the `solo-roll` CLI

`solo-roll` is the Python CLI that backs the dice-and-tables layer used by every skill in this repo. Install it once via `pipx`:

\`\`\`bash
cd ~/git/solo-rpg-toolkit   # or wherever you cloned this
pipx install --editable .
solo-roll table action1
\`\`\`

If the last command prints JSON, you're set. Editable install means edits to `src/solo_roll/` take effect immediately — no reinstall while iterating.

### Subcommands

- `solo-roll table <name>` — roll a single table (flat or nested, e.g. `elements/plottwist`)
- `solo-roll meaning-pair` — roll Mythic Meaning Tables (action + descriptor) in one call
- `solo-roll fate-check --likelihood <key> --cf <1..9>` — full Mythic fate check
- `solo-roll quickset <id>` — run a quickset chain (`npc_profile`, `location_profile`, `creature_profile`)

Every subcommand accepts `--seed N` (reproducibility) and `--data DIR` (override data directory).

### Data layout

\`\`\`
data/tables/<name>.json               # flat d-tables (action1, descriptor1, ...)
data/tables/elements/<name>.json      # specialized tables (plot twist, creature, etc.)
data/charts/mythic-fate.json          # Mythic 2e fate chart
data/quicksets/<id>.json              # multi-step chains
\`\`\`

Add new tables by dropping a JSON file into `data/tables/` — no rebuild, no reinstall. See any existing file for the schema.
```

(When writing the file, do **not** escape the backticks with backslashes — they're only escaped in this plan document so the outer fence renders correctly. The actual README should contain bare triple-backtick fences.)

- [ ] **Step 3: Verify the new section renders sanely**

Run: `head -50 README.md`

Expected: the install section appears near the top, above the "What's in here" section.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: add solo-roll install + usage to README

Documents the pipx-editable install, the four v1 subcommands, and the data/
layout. Existing skill-install and per-campaign sections left intact; skill
rewrites land in a later sub-project.
EOF
)"
```

---

## Task 15: Final verification

**Files:** none modified — this is a green-light check.

- [ ] **Step 1: Run the full test suite from a clean state**

```bash
pytest -v
```

Expected: every test passes. Zero failures. Zero errors.

- [ ] **Step 2: Run the four subcommands end-to-end**

```bash
solo-roll table action1 --seed 0
solo-roll meaning-pair --seed 0
solo-roll fate-check --likelihood likely --cf 5 --seed 0
solo-roll quickset npc_profile --seed 0
```

Expected: four JSON outputs, each valid, each exits 0.

- [ ] **Step 3: Run reproducibility spot-checks**

```bash
solo-roll fate-check --likelihood likely --cf 5 --seed 777 > /tmp/a.json
solo-roll fate-check --likelihood likely --cf 5 --seed 777 > /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo OK
```

Expected: `OK` — same seed produces byte-equal JSON.

- [ ] **Step 4: Verify error paths**

```bash
solo-roll table no_such_table; echo "exit=$?"
solo-roll fate-check --likelihood bogus --cf 5; echo "exit=$?"
solo-roll fate-check --likelihood likely --cf 99; echo "exit=$?"
solo-roll quickset no_such_quickset; echo "exit=$?"
```

Expected: each command exits 1 and prints an error to stderr.

- [ ] **Step 5: Verify gitignore still keeps `reference/` out of tracking**

```bash
git status
git status --ignored | grep reference
```

Expected: `reference/` appears under ignored entries; `git status` shows clean working tree.

- [ ] **Step 6: Verify package metadata**

```bash
solo-roll --version
pipx list | grep solo-roll
```

Expected: `solo-roll 0.1.0` and pipx lists the editable install pointing at this repo.

- [ ] **Step 7: Tag the release (optional, no push)**

```bash
git tag v0.1.0
git log --oneline
```

Expected: the tag lands on the latest commit. Push is out of scope — this is a local v0.1.0 milestone.

---

## Closing notes

- **Not included (deferred to later sub-projects):** skill rewrites (Mythic 2e, solo-journaler), campaign-folder bootstrap/installer, PDF → markdown pipeline, additional tables beyond the ones already in `data/`.
- **Follow-up for the Mythic 2e sub-project:** cross-check `data/charts/mythic-fate.json` values against the Mythic GME 2e PDF and adjust if the current placeholder values (copied from `skills/mythic-gme/fate-check.md`) differ from the book.
- **Converter script future:** `scripts/convert_txt_tables.py` stays in the repo as a utility for adding future `.txt`-sourced tables (e.g., if you extract new tables from a PDF with a similar format). It is not part of the runtime or the test suite.
