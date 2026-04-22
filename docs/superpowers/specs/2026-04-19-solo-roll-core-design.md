# solo-roll Core Library + Repo Cleanup — Design

**Date:** 2026-04-19
**Scope:** First sub-project of the Solo RPG GM Assistant toolkit. Foundation Python library (`solo-roll`) that provides deterministic dice rolling, JSON table lookup, Mythic fate-chart math, and quickset chain execution. All downstream skills (Mythic 2e rewrite, Adventure Crafter, Location Crafter, NPC generator, etc.) depend on this layer.

## Goals

1. Remove LLM from the random-number path. All dice and table indexing happen in Python. LLM interprets results; it does not generate them.
2. Ship a single CLI, `solo-roll`, with stable JSON output that Claude skills invoke via the Bash tool.
3. Store tables as drop-in JSON files. New tables = new file in `data/tables/`, no rebuild.
4. Clean up the current messy repo layout into a src/tests/data/skills/reference structure that supports future sub-projects.

## Non-goals

- Skill rewrites (Mythic 2e, solo-journaler, etc.) — separate sub-projects.
- Distribution/installer for fresh campaign folders (sub-project 8).
- CI/CD, packaging for PyPI, release process.
- PDF → markdown extraction pipeline (sub-project 7).
- Bootstrap of additional tables beyond those currently in `data/`.

## Architecture

```
Claude Code skill (markdown instructions)
        │  "run: solo-roll meaning-pair"
        ▼
  Bash tool invocation
        ▼
  solo-roll CLI  ──── reads ────▶  data/tables/*.json
        │                           data/charts/*.json
        │                           data/quicksets/*.json
        │  writes JSON to stdout
        ▼
  skill parses JSON, narrates to player
```

Deterministic mechanics (dice, chart lookups, chain execution) live in Python. Interpretation (narrative meaning of a word pair, NPC personality shading, etc.) stays in the LLM. The CLI never narrates; skills never roll.

Runtime: Python ≥ 3.10, stdlib only (`argparse`, `random`, `json`, `pathlib`). Zero runtime dependencies.

## Repo layout (target)

```
solo-rpg-toolkit/
├── src/solo_roll/
│   ├── __init__.py
│   ├── cli.py              # argparse entry, dispatches subcommands
│   ├── tables.py           # JSON loader, roll_table(name, dice_source)
│   ├── charts.py           # fate-chart loader + threshold math
│   ├── quicksets.py        # chain executor
│   └── rng.py              # seeded random helper + dice_source abstraction
├── tests/
│   ├── test_tables.py
│   ├── test_charts.py
│   ├── test_quicksets.py
│   └── test_cli.py
├── data/
│   ├── tables/
│   │   ├── action1.json
│   │   ├── action2.json
│   │   ├── descriptor1.json
│   │   ├── descriptor2.json
│   │   └── elements/       # 45 element tables (one file each)
│   ├── charts/
│   │   └── mythic-fate.json
│   └── quicksets/
│       ├── npc_profile.json
│       ├── location_profile.json
│       └── creature_profile.json
├── skills/                 # existing Claude skills, untouched in this sub-project
├── reference/              # gitignored — PDFs, mythic2e.md book dump
├── docs/superpowers/specs/
├── pyproject.toml
├── .gitignore              # includes /reference/
└── README.md
```

### Moves from current layout

- `pdfs/` → `reference/` (rename + add to `.gitignore`).
- `data/mythic2e.md` → `reference/mythic2e.md` (book dump, gitignored).
- `data/action1.txt`, `action2.txt`, `descriptor1.txt`, `descriptor2.txt` → `data/tables/{name}.json` (one-shot convert).
- `data/elements/*.txt` → `data/tables/elements/*.json` (one-shot convert).
- `data/quicksets.json` (single file) → split into `data/quicksets/npc_profile.json`, `data/quicksets/location_profile.json`, `data/quicksets/creature_profile.json` (one chain per file for easy extension).

Original `.txt` files are deleted after conversion; they remain in git history if ever needed.

## Data format

### Flat d-table

```json
{
  "name": "action1",
  "display_name": "Action (Meaning Table 1)",
  "dice": "d100",
  "source": "Mythic GME 2e, Actions Table 1",
  "entries": ["Abandon", "Accompany", "Activate", "...", "Waste"]
}
```

Invariant: `len(entries) == dice_faces` (d100 → 100, d20 → 20, etc.). The loader validates on read and errors loud on mismatch (exit code 2).

Roll: `roll = dice_source.roll(1, faces)`; `result = entries[roll - 1]`. Both `roll` (index) and `result` (word) are returned so the skill can narrate "rolled 42 → Betray".

### Ranged/weighted table

Schema-ready for later (event focus d100 bands, etc.). Not used by any v1 subcommand directly, but the loader accepts it so future tables drop in with no code change.

```json
{
  "name": "event-focus",
  "dice": "d100",
  "source": "Mythic GME 2e p.XX",
  "ranges": [
    {"min": 1,  "max": 7,  "result": "Remote Event"},
    {"min": 8,  "max": 28, "result": "NPC Action"}
  ]
}
```

Loader decides flat vs. ranged by which key is present. Having both is a validation error.

### Quickset

`data/quicksets/npc_profile.json`:

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

`table` is a path relative to `data/tables/` without extension. `count` (optional, default 1) reserved for multi-roll steps; v1 always treats it as 1 and emits one result per step.

### Fate chart

`data/charts/mythic-fate.json`:

```json
{
  "name": "mythic-fate",
  "source": "Mythic GME 2e",
  "likelihoods": [
    "has_to_be", "near_sure_thing", "very_likely", "likely",
    "50_50", "unlikely", "very_unlikely", "near_impossible", "no_way"
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

Array index = `cf - 1`. Values copied from the current `skills/mythic-gme/fate-check.md`; flagged for cross-check against the Mythic 2e PDF when the Mythic sub-project begins. Not blocking this sub-project.

**Threshold math** (in `charts.py`):

- `yes_threshold = thresholds[likelihood][cf - 1]`
- `exceptional_yes_cap = yes_threshold // 5`
- `exceptional_no_floor = 100 - ((100 - yes_threshold) // 5)`

**d100 reading of 2d10** (Mythic convention):

- Roll `d1` and `d2`, each 0..9.
- `roll = d1 * 10 + d2`, with the special case `(0, 0) → 100`.

**Outcome classification:**

- `roll ≤ exceptional_yes_cap` → `exceptional_yes`
- else `roll ≤ yes_threshold` → `yes`
- else `roll ≥ exceptional_no_floor` → `exceptional_no`
- else → `no`

**Random event:** `d1 == d2 AND d1 ≤ cf`.

## CLI contract

All subcommands write JSON to stdout (never text, never markdown). Errors go to stderr with nonzero exit.

### Global flags

- `--seed N` — seeds a local `random.Random(N)`. Omitted → system entropy. Shipped for user-facing reproducibility; not asserted on in tests.
- `--data DIR` — override the data directory (else `SOLO_ROLL_DATA` env, else package-default).

### Exit codes

- `0` — success
- `1` — bad args (unknown table, unknown likelihood, CF out of 1..9)
- `2` — data-file error (invalid JSON, entry-count mismatch, missing file)

### `solo-roll table <name>`

Roll any single table by id. `<name>` supports nested paths.

```bash
solo-roll table action1
solo-roll table elements/plottwist
```

Output:
```json
{
  "table": "action1",
  "display_name": "Action (Meaning Table 1)",
  "dice": "d100",
  "roll": 42,
  "result": "Betray"
}
```

### `solo-roll meaning-pair`

Convenience for Mythic Meaning Tables: rolls action1 + descriptor1 in one call.

```bash
solo-roll meaning-pair
solo-roll meaning-pair --tables action2,descriptor2
```

Output:
```json
{
  "action":      {"table": "action1",     "roll": 42, "result": "Betray"},
  "description": {"table": "descriptor1", "roll": 77, "result": "Roughly"}
}
```

`--tables` optional, accepts a comma-pair. Default is `action1,descriptor1`.

### `solo-roll fate-check --likelihood <key> --cf <1..9>`

Full Mythic fate check: rolls 2d10, reads as d100, looks up thresholds, classifies outcome, detects doubles-under-CF for random events.

```bash
solo-roll fate-check --likelihood likely --cf 5
```

Output:
```json
{
  "likelihood": "likely",
  "cf": 5,
  "yes_threshold": 75,
  "exceptional_yes_cap": 15,
  "exceptional_no_floor": 95,
  "dice": [4, 3],
  "roll": 43,
  "outcome": "yes",
  "exceptional": false,
  "random_event_triggered": false
}
```

`outcome` ∈ `yes | no | exceptional_yes | exceptional_no`. The field is named `outcome` (not `result`) so it does not collide with the `result` field on table rolls when fate-check output is composed into larger JSON structures by future recipes.

Accepted likelihood keys: `has_to_be`, `near_sure_thing`, `very_likely`, `likely`, `50_50`, `unlikely`, `very_unlikely`, `near_impossible`, `no_way`.

### `solo-roll quickset <id>`

Runs a quickset chain end-to-end.

```bash
solo-roll quickset npc_profile
```

Output:
```json
{
  "id": "npc_profile",
  "name": "NPC Profile",
  "steps": [
    {"label": "Identity",    "table": "elements/characteridentity",    "roll": 12, "result": "Aristocrat"},
    {"label": "Description", "table": "elements/characterdescription", "roll": 7,  "result": "Colorful"},
    {"label": "Appearance",  "table": "elements/characterappearance",  "roll": 33, "result": "Equipped"},
    {"label": "Background",  "table": "elements/characterbackground",  "roll": 48, "result": "Influential"},
    {"label": "Personality", "table": "elements/characterpersonality", "roll": 88, "result": "Mysterious"},
    {"label": "Motivation",  "table": "elements/charactermotivation",  "roll": 15, "result": "Revenge"},
    {"label": "Skills",      "table": "elements/characterskills",      "roll": 61, "result": "Knowledgeable"},
    {"label": "Trait",       "table": "elements/charactertrait",       "roll": 29, "result": "Creepy"}
  ]
}
```

## Module layout

- `solo_roll.rng` — `DiceSource` protocol (`roll(low, high) -> int`). Default impl wraps `random.Random`. Tests inject a scripted source.
- `solo_roll.tables` — JSON loader, schema validation, `roll_table(name, dice_source) -> dict`.
- `solo_roll.charts` — fate chart loader, threshold math functions (pure), `fate_check(likelihood, cf, dice_source) -> dict`.
- `solo_roll.quicksets` — quickset loader, `run_quickset(id, dice_source) -> dict`.
- `solo_roll.cli` — argparse wiring. Each subcommand builds a `DiceSource`, calls the corresponding library function, prints JSON.

## Testing

`pytest` suite. Seeding is available for user reproducibility but tests do not assert on stdlib RNG output (those would be brittle and test CPython rather than our code). Determinism in tests comes from injected `DiceSource` instances.

### `test_tables.py`

- Load every JSON file in `data/tables/**`. Parses cleanly; schema valid.
- Flat table invariant: `len(entries) == dice_faces`.
- Ranged table invariant: ranges cover 1..faces with no gaps or overlaps.
- Unknown table name → exit 1 with a clear message.
- Corrupt data file (entries count wrong) → exit 2.

### `test_charts.py` — pure-math, no RNG

- Fate chart loads, has 9 likelihoods × 9 CF columns, all ints in 1..99.
- Threshold formula test cases: for every (likelihood, cf) combination, the computed `exceptional_yes_cap` and `exceptional_no_floor` are asserted against hand-checked values.
- d100 read mapping: `(0,0) → 100`, `(4,3) → 43`, `(9,0) → 90`, `(0,7) → 7`.
- Outcome classification: injected roll values cover each branch — an `exceptional_yes` case, a `yes` case, a `no` case, an `exceptional_no` case.
- Random event detection: `(4,4)` at cf=5 fires; `(4,4)` at cf=3 does not; `(4,3)` at any cf does not.

### `test_quicksets.py`

- Every quickset in `data/quicksets/` loads.
- Every step's `table` resolves to an existing table file.
- Chain executor with N steps returns N result entries with the correct labels (structural check, no value assertions).

### `test_cli.py` (subprocess-level)

- Exit codes: valid args → 0; unknown likelihood → 1; unknown table → 1; corrupt data → 2.
- Output contract: for each subcommand, stdout is valid JSON containing all required keys for that subcommand. Field values are not asserted.
- `--seed` reproducibility: two invocations with the same seed produce byte-equal stdout.

## Installation

```bash
cd ~/git/solo-rpg-toolkit
pipx install -e .
```

Editable install — edits to `src/solo_roll/` take effect immediately. `solo-roll` on PATH globally via pipx's isolated venv.

`pyproject.toml`:

```toml
[project]
name = "solo-roll"
version = "0.1.0"
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
```

Data discovery order (first match wins):

1. `--data DIR` CLI flag.
2. `SOLO_ROLL_DATA` env var.
3. `~/.config/solo-roll/data/` (user override). Only used if the directory exists; its absence is not an error.
4. Package default: resolved from `__file__` relative to repo root (works for editable installs, which is the v1 target).

Adding new tables later: drop a JSON file into `data/tables/`, optionally validate with `solo-roll table <newname>`. No rebuild, no reinstall.

Uninstall: `pipx uninstall solo-roll`.

### README updates (this sub-project)

- Add an "Install the `solo-roll` CLI" section with the `pipx install -e .` command and a verify step (`solo-roll table action1`).
- Leave the existing "Install skills" and "Per-campaign setup" sections untouched — skill rewrites are a later sub-project.
- Note the new repo layout at a high level (where tables live, where to drop new JSON).

## Risks and open items

- **Non-editable installs** are not supported in v1 (the `__file__`-based data resolution breaks). If PyPI distribution is ever wanted, revisit: ship data inside the wheel via `importlib.resources`, or document `SOLO_ROLL_DATA`.
- **Fate chart values** are copied from the current placeholder file; they need a cross-check against the Mythic 2e PDF as part of the Mythic sub-project. Not blocking this sub-project.
- **Table name collisions** across namespaces (e.g., a future `elements/action1` vs root `action1`) — the nested-path scheme already disambiguates; document convention in README.
- **Ranged table v1 coverage** — the schema is accepted by the loader but no v1 subcommand returns a ranged roll directly. First ranged use is event-focus in the Mythic sub-project.
