# Table Discoverability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `solo-roll list` CLI subcommand and a `description` field on every table JSON so Claude (and humans) can discover available tables in-band, then update the `mythic-gme`, `ironsworn`, and `ironsworn-truths` skills to use the new affordance and stop auto-substituting Mythic mechanics for Ironsworn-native ones.

**Architecture:** Schema gets an optional `description` string field (validator-enforced). All shipped tables are backfilled with descriptions in the same change. New `_cmd_list` handler in `cli.py` walks `<data_dir>/tables/` recursively, loads each table through the existing loader, and renders either grouped human-readable text or a JSON envelope. Skill markdown gets surgical edits — additions in `mythic-gme`, replacement of the override-list in `ironsworn`, generalization of the per-truth Mythic option in `ironsworn-truths`.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `pytest`, JSON. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-25-table-discoverability-design.md`

**Note on counts:** the spec says "47 themed tables" in `elements/`. Actual count is 45 (`ls data/tables/elements/ | wc -l` → 45). Total shipped tables: 4 top-level (`action1`, `action2`, `descriptor1`, `descriptor2`) + 45 elements/* + 1 `mythic/event-focus` = 50. Tasks in this plan reflect the actual count.

---

## File Structure

**Modified:**
- `src/solo_roll/tables.py` — add `description` to validator (Task 1).
- `src/solo_roll/cli.py` — add `_cmd_list` handler + parser registration (Task 7).
- `tests/test_tables.py` — three new validator cases + one shipped-table assertion (Tasks 1, 6).
- `tests/test_cli.py` — five new cases for `solo-roll list` (Task 7).
- `data/tables/action1.json`, `action2.json`, `descriptor1.json`, `descriptor2.json` — add `description` (Task 2).
- `data/tables/elements/*.json` — 45 files, add `description` (Tasks 3, 4, 5).
- `data/tables/mythic/event-focus.json` — add `description` (Task 5).
- `CLAUDE.md` — update "Adding a table" section (Task 8).
- `skills/mythic-gme/SKILL.md` — two new sections (Task 9).
- `skills/ironsworn/SKILL.md` — replace Mythic-coupling section, drop scene-test directive (Task 10).
- `skills/ironsworn-truths/SKILL.md` — refine Mythic option language (Task 11).

**Created:** None.

---

## Task 1: Schema validator accepts optional `description`

**Files:**
- Modify: `src/solo_roll/tables.py:45-89` (`_validate` function)
- Test: `tests/test_tables.py`

- [ ] **Step 1: Write failing tests for description validation**

Add to `tests/test_tables.py` (anywhere after `test_load_flat_table`):

```python
def test_load_table_with_description(data_dir: Path):
    _write_json(
        data_dir / "tables" / "described.json",
        {
            "name": "described",
            "dice": "d4",
            "description": "A handy one-line summary.",
            "entries": ["a", "b", "c", "d"],
        },
    )
    table = load_table("described", data_dir)
    assert table["description"] == "A handy one-line summary."


def test_load_table_without_description(data_dir: Path):
    _write_json(
        data_dir / "tables" / "undescribed.json",
        {
            "name": "undescribed",
            "dice": "d4",
            "entries": ["a", "b", "c", "d"],
        },
    )
    table = load_table("undescribed", data_dir)
    assert "description" not in table or table.get("description") is None


def test_load_table_non_string_description_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "baddesc.json",
        {
            "name": "baddesc",
            "dice": "d4",
            "description": 42,
            "entries": ["a", "b", "c", "d"],
        },
    )
    with pytest.raises(TableDataError):
        load_table("baddesc", data_dir)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_tables.py::test_load_table_non_string_description_raises tests/test_tables.py::test_load_table_with_description tests/test_tables.py::test_load_table_without_description -v`

Expected: `test_load_table_non_string_description_raises` FAILS (no validation rejects the int — load succeeds). The other two PASS already (loader returns the dict as-is). At minimum the non-string test must fail.

- [ ] **Step 3: Add description validation to `_validate`**

In `src/solo_roll/tables.py`, modify `_validate` to add a check immediately after the existing `name` check (after line 47):

```python
def _validate(payload: dict[str, Any], path: Path) -> None:
    if not isinstance(payload.get("name"), str):
        raise TableDataError(f"{path}: 'name' must be a non-empty string")

    if "description" in payload and not isinstance(payload["description"], str):
        raise TableDataError(f"{path}: 'description' must be a string when present")

    dice = payload.get("dice")
    # ... rest unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tables.py -v`

Expected: all tests pass. The three new ones plus all existing ones.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/tables.py tests/test_tables.py
git commit -m "feat(tables): allow optional description field on table JSON"
```

---

## Task 2: Backfill descriptions on top-level meaning tables

**Files:**
- Modify: `data/tables/action1.json`, `data/tables/action2.json`, `data/tables/descriptor1.json`, `data/tables/descriptor2.json`

- [ ] **Step 1: Add `description` to each meaning-pair JSON**

For each file, insert a new `"description"` line directly after `"display_name"`. Use these exact descriptions:

`data/tables/action1.json`:
```json
"description": "Verb word list (Mythic 2e Meaning Table — Actions 1). Default 'action' half of solo-roll meaning-pair.",
```

`data/tables/action2.json`:
```json
"description": "Alternate verb word list (Mythic 2e Meaning Table — Actions 2). Drop-in replacement for action1 to vary tone.",
```

`data/tables/descriptor1.json`:
```json
"description": "Adverb/descriptor word list (Mythic 2e Meaning Table — Descriptions 1). Default 'description' half of solo-roll meaning-pair.",
```

`data/tables/descriptor2.json`:
```json
"description": "Alternate adverb/descriptor list (Mythic 2e Meaning Table — Descriptions 2). Pair with action2 for a different feel.",
```

- [ ] **Step 2: Verify each file still parses**

Run: `python -c "import json; [json.loads(open(f).read()) for f in ['data/tables/action1.json', 'data/tables/action2.json', 'data/tables/descriptor1.json', 'data/tables/descriptor2.json']]; print('ok')"`

Expected: `ok`. Any `JSONDecodeError` means a stray comma or syntax slip — re-edit.

- [ ] **Step 3: Verify validator still loads them**

Run: `pytest tests/test_tables.py::test_all_shipped_tables_load_from_real_data -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add data/tables/action1.json data/tables/action2.json data/tables/descriptor1.json data/tables/descriptor2.json
git commit -m "data: backfill description on meaning-pair tables"
```

---

## Task 3: Backfill descriptions on elements/* — characters & creatures

**Files:**
- Modify: 17 files under `data/tables/elements/`

This task covers character-related and creature-related tables. Splitting the elements/ backfill into three tasks (3, 4, 5) keeps each commit reviewable.

- [ ] **Step 1: Add `description` to each file**

Insert directly after `"display_name"`. Use these exact descriptions:

| File | Description |
|------|-------------|
| `characters.json` | "Character archetype/role hooks for quick NPC seeds (Mythic 2e style)." |
| `characteract.json` | "Single-action verbs for what a character is doing in the moment." |
| `characterappearance.json` | "Visible physical traits (build, posture, distinguishing marks). Combine with characterpersonality for an NPC sketch." |
| `characterbackground.json` | "Backstory hooks (origin, formative event, social standing) for fleshing out an NPC." |
| `charactercombat.json` | "Combat style or fighting state (cautious, frenzied, defensive)." |
| `characterconvo.json` | "Conversational tone or topic (probing, evasive, boastful)." |
| `characterdescription.json` | "General character descriptors — broad personality and trait words." |
| `characteridentity.json` | "Role/identity terms (mentor, rival, fugitive). Useful for naming an NPC's function in the story." |
| `charactermotivation.json` | "Goal/drive words (revenge, redemption, survival). Answers 'what do they want?'." |
| `characterpersonality.json` | "Personality trait words (stoic, capricious, generous). Combine with characterappearance for full NPC color." |
| `characterskills.json` | "Notable abilities or competencies the character is known for." |
| `charactertrait.json` | "Quirks, habits, or distinguishing mannerisms — small details that make an NPC memorable." |
| `creature.json` | "Single-word creature traits (Loud, Ancient, Many-eyed). Combine with creatureabilities for monster generation." |
| `creatureabilities.json` | "Special powers or unnatural traits (Element, Flight, Mimicry). Pairs with creature for monster builds." |
| `alien.json` | "Alien species traits and encounter color for sci-fi or weird-fiction beats." |
| `mutation.json` | "Physical, mental, or supernatural mutations — useful for corrupted creatures or post-cataclysm survivors." |
| `undead.json` | "Undead types and traits (revenant, husk, shrieker). Pair with creatureabilities for variant horrors." |

- [ ] **Step 2: Verify all parse + validate**

Run: `pytest tests/test_tables.py::test_all_shipped_tables_load_from_real_data -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add data/tables/elements/character*.json data/tables/elements/creature*.json data/tables/elements/alien.json data/tables/elements/mutation.json data/tables/elements/undead.json
git commit -m "data: backfill description on character/creature elements tables"
```

---

## Task 4: Backfill descriptions on elements/* — places, objects, magic

**Files:**
- Modify: 16 files under `data/tables/elements/`

- [ ] **Step 1: Add `description` to each file**

| File | Description |
|------|-------------|
| `city.json` | "City features and street-level color (markets, walls, districts). Pair with civilization for cultural texture." |
| `civilization.json` | "Culture and society descriptors (theocratic, fractured, isolationist). Pair with city or noblehouse." |
| `cavern.json` | "Cavern features — formations, hazards, and signs of inhabitants. Use for underground exploration." |
| `domicile.json` | "Home and dwelling features (humble, defensible, abandoned)." |
| `dungeon.json` | "Dungeon room and feature words. Pair with dungeontrap to populate a delve." |
| `dungeontrap.json` | "Trap types and triggers for dungeon hazards." |
| `forest.json` | "Forest features and atmosphere (overgrown, ancient, blighted)." |
| `terrain.json` | "Generic terrain descriptors for wilderness travel and journey rolls." |
| `location.json` | "Generic location features — use when no themed table fits." |
| `noblehouse.json` | "Noble house traits (sigil, motto, current crisis). Pair with civilization for political plots." |
| `army.json` | "Army composition, tactics, or morale state. Useful for war scenes or large-scale opposition." |
| `object.json` | "Generic object descriptors — found items, set dressing, scavenged loot." |
| `magicitem.json` | "Magic item effects and properties for treasure or quest rewards." |
| `spell.json` | "Spell effects and arcane phenomena. Useful for novel magic or wild surge results." |
| `powers.json` | "Special powers and supernatural abilities — for characters, creatures, or items." |
| `curses.json` | "Curse types and lingering hexes. Pair with mutation or undead for darker beats." |

- [ ] **Step 2: Verify all parse + validate**

Run: `pytest tests/test_tables.py::test_all_shipped_tables_load_from_real_data -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add data/tables/elements/city.json data/tables/elements/civilization.json data/tables/elements/cavern.json data/tables/elements/domicile.json data/tables/elements/dungeon.json data/tables/elements/dungeontrap.json data/tables/elements/forest.json data/tables/elements/terrain.json data/tables/elements/location.json data/tables/elements/noblehouse.json data/tables/elements/army.json data/tables/elements/object.json data/tables/elements/magicitem.json data/tables/elements/spell.json data/tables/elements/powers.json data/tables/elements/curses.json
git commit -m "data: backfill description on place/object/magic elements tables"
```

---

## Task 5: Backfill descriptions on remaining elements/* + mythic/

**Files:**
- Modify: 12 files under `data/tables/elements/`, 1 file under `data/tables/mythic/`

- [ ] **Step 1: Add `description` to each file**

| File | Description |
|------|-------------|
| `elements/adventuretone.json` | "Mood/genre tags for an adventure (grim, whimsical, cosmic). Set up at session start." |
| `elements/animalaction.json` | "What an animal is doing right now (foraging, watching, fleeing). Use for wilderness encounters." |
| `elements/crypticmessage.json` | "Riddle and omen fragments — for prophecies, dreams, coded notes, or oracular utterances." |
| `elements/god.json` | "Deity domains and aspects (sun-and-storm, broken-vow, hidden-name). Pair with civilization for pantheons." |
| `elements/legend.json` | "Legend hooks (ancient battle, lost ruler, vanished people). Useful for lore drops and quest seeds." |
| `elements/names.json` | "Name fragments to assemble or pick whole. Pulls names without committing to one culture." |
| `elements/plottwist.json` | "Plot twist seeds (Mythic 2e Plot Twist table) — when the story needs a sharp turn." |
| `elements/scavenge.json` | "Scavenging results — what you find rummaging through ruins, packs, or rubble." |
| `elements/smell.json` | "Scent descriptors for setting atmosphere (charred, sweet-rot, ozone)." |
| `elements/sound.json` | "Sound descriptors for setting atmosphere (whispering, distant-thunder, scraping)." |
| `elements/starship.json` | "Starship features and quirks for sci-fi vessels (combine with civilization for fleet identity)." |
| `elements/vision.json` | "Vision/dream content fragments — for prophetic dreams, scrying results, or hallucinations." |
| `mythic/event-focus.json` | "Mythic 2e Event Focus — 12-category lookup that classifies a Random Event. Always rolled before meaning-pair when an event fires." |

- [ ] **Step 2: Verify all parse + validate**

Run: `pytest tests/test_tables.py::test_all_shipped_tables_load_from_real_data -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add data/tables/elements/adventuretone.json data/tables/elements/animalaction.json data/tables/elements/crypticmessage.json data/tables/elements/god.json data/tables/elements/legend.json data/tables/elements/names.json data/tables/elements/plottwist.json data/tables/elements/scavenge.json data/tables/elements/smell.json data/tables/elements/sound.json data/tables/elements/starship.json data/tables/elements/vision.json data/tables/mythic/event-focus.json
git commit -m "data: backfill description on remaining elements + mythic event-focus"
```

---

## Task 6: Add assertion that all shipped tables have a description

**Files:**
- Modify: `tests/test_tables.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tables.py`:

```python
def test_all_shipped_tables_have_description():
    from solo_roll import DEFAULT_DATA_DIR
    tables_root = DEFAULT_DATA_DIR / "tables"
    json_files = sorted(tables_root.rglob("*.json"))
    missing: list[str] = []
    for path in json_files:
        rel_name = path.relative_to(tables_root).with_suffix("").as_posix()
        table = load_table(rel_name, DEFAULT_DATA_DIR)
        desc = table.get("description")
        if not isinstance(desc, str) or not desc.strip():
            missing.append(rel_name)
    assert not missing, f"tables missing description: {missing}"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_tables.py::test_all_shipped_tables_have_description -v`

Expected: PASS — Tasks 2-5 already added descriptions to every shipped table. If FAIL, the failure message lists which files were missed; go back and add the description.

- [ ] **Step 3: Commit**

```bash
git add tests/test_tables.py
git commit -m "test(tables): assert every shipped table has a description"
```

---

## Task 7: Implement `solo-roll list` subcommand

**Files:**
- Modify: `src/solo_roll/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_cli.py`:

```python
def test_list_no_args_groups_top_level_and_directories():
    result = _run("list")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    # Top-level group rendered first, with bare label
    assert "(top-level)" in out
    # Directory groups have trailing slash
    assert "elements/" in out
    assert "mythic/" in out
    # Several known tables appear
    assert "action1" in out
    assert "creature" in out
    assert "event-focus" in out


def test_list_prefix_filters_to_directory():
    result = _run("list", "elements")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "elements/" in out
    assert "creature" in out
    # Top-level and mythic excluded
    assert "(top-level)" not in out
    assert "mythic/" not in out
    assert "action1" not in out


def test_list_prefix_with_trailing_slash_equivalent():
    a = _run("list", "elements")
    b = _run("list", "elements/")
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout


def test_list_json_output_shape():
    result = _run("list", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "tables" in payload
    assert isinstance(payload["tables"], list)
    assert len(payload["tables"]) >= 49
    for entry in payload["tables"]:
        assert set(entry.keys()) == {"name", "display_name", "dice", "description", "entry_count"}
        assert isinstance(entry["name"], str)
        assert isinstance(entry["dice"], str)
        assert isinstance(entry["entry_count"], int) and entry["entry_count"] > 0
    # All shipped tables have a description (post-Task 6)
    assert all(isinstance(e["description"], str) and e["description"] for e in payload["tables"])


def test_list_prefix_no_match_returns_empty():
    result = _run("list", "nonexistent_prefix")
    assert result.returncode == 0
    # Empty output (or empty group) — just no actual table lines
    assert "creature" not in result.stdout
    assert "action1" not in result.stdout


def test_list_custom_data_dir_with_synthetic_tables(tmp_path):
    # Custom data dir holding two tables; --data overrides default.
    tables = tmp_path / "data" / "tables"
    tables.mkdir(parents=True)
    (tables / "alpha.json").write_text(json.dumps({
        "name": "alpha", "display_name": "Alpha", "dice": "d4",
        "description": "First sample.", "entries": ["a", "b", "c", "d"],
    }))
    nested = tables / "themed"
    nested.mkdir()
    (nested / "beta.json").write_text(json.dumps({
        "name": "beta", "display_name": "Beta", "dice": "d6",
        "entries": ["1", "2", "3", "4", "5", "6"],
    }))
    result = _run("list", "--data", str(tmp_path / "data"), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    names = {t["name"] for t in payload["tables"]}
    assert names == {"alpha", "themed/beta"}
    descs = {t["name"]: t["description"] for t in payload["tables"]}
    assert descs["alpha"] == "First sample."
    assert descs["themed/beta"] is None  # absent in source → null in output


def test_list_missing_data_dir_exits_1(tmp_path):
    bogus = tmp_path / "nope"
    result = _run("list", "--data", str(bogus))
    assert result.returncode == 1
    assert "data dir not found" in result.stderr.lower()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_cli.py -k "test_list_" -v`

Expected: every `test_list_*` FAILS (subcommand not registered yet — argparse error or `solo-roll: error: invalid choice: 'list'`).

- [ ] **Step 3: Implement `_cmd_list` and register it**

In `src/solo_roll/cli.py`:

(a) Update the existing `from .tables import` line at the top of the file (currently `from .tables import TableDataError, TableNotFoundError, roll_table`) to also import `load_table`:

```python
from .tables import TableDataError, TableNotFoundError, load_table, roll_table
```

(b) Add the handler. Place after `_cmd_roll` (around line 117) and before `def main`:

```python
def _cmd_list(args: argparse.Namespace) -> int:
    data_dir = _resolve_data_dir(args.data)
    if not data_dir.exists():
        print(f"error: data dir not found: {data_dir}", file=sys.stderr)
        return 1
    tables_root = data_dir / "tables"
    entries: list[dict] = []
    if tables_root.exists():
        prefix = args.prefix.rstrip("/") if args.prefix else None
        for path in sorted(tables_root.rglob("*.json")):
            rel_name = path.relative_to(tables_root).with_suffix("").as_posix()
            if prefix is not None and rel_name != prefix and not rel_name.startswith(prefix + "/"):
                continue
            try:
                table = load_table(rel_name, data_dir)
            except (TableNotFoundError, TableDataError) as exc:
                print(f"warning: skipped {path}: {exc}", file=sys.stderr)
                continue
            if "entries" in table:
                count = len(table["entries"])
            else:
                count = sum(b["max"] - b["min"] + 1 for b in table["ranges"])
            entries.append({
                "name": rel_name,
                "display_name": table.get("display_name", table["name"]),
                "dice": table["dice"],
                "description": table.get("description"),
                "entry_count": count,
            })
    if args.json:
        print(json.dumps({"tables": entries}, indent=2))
        return 0
    _render_list_text(entries)
    return 0


def _render_list_text(entries: list[dict]) -> None:
    if not entries:
        return
    groups: dict[str, list[dict]] = {}
    for e in entries:
        group = e["name"].rsplit("/", 1)[0] if "/" in e["name"] else "(top-level)"
        groups.setdefault(group, []).append(e)
    ordered: list[str] = []
    if "(top-level)" in groups:
        ordered.append("(top-level)")
    ordered.extend(sorted(g for g in groups if g != "(top-level)"))
    for group in ordered:
        header = group if group == "(top-level)" else f"{group}/"
        print(header)
        members = groups[group]
        name_w = max(len(e["name"].rsplit("/", 1)[-1]) for e in members)
        display_w = max(len(e["display_name"]) for e in members)
        for e in members:
            short = e["name"].rsplit("/", 1)[-1]
            desc = e["description"] if e["description"] else "—"
            print(f"  {short:<{name_w}}  {e['dice']:<4}  {e['entry_count']:>3} entries  {e['display_name']:<{display_w}}  — {desc}")
        print()
```

(c) Register the parser inside `main()`. Add after `p_roll` block (around line 150):

```python
    p_list = subparsers.add_parser("list", help="List available tables grouped by directory")
    p_list.add_argument("prefix", nargs="?", default=None,
                        help="Optional prefix to filter (e.g. 'elements' or 'mythic')")
    p_list.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of grouped text")
    p_list.add_argument("--data", type=str, default=None)
    p_list.set_defaults(func=_cmd_list)
```

Note: `_add_common_args` is not used here because `--seed` is irrelevant to listing. Only `--data` is needed.

- [ ] **Step 4: Run the new tests to confirm they pass**

Run: `pytest tests/test_cli.py -k "test_list_" -v`

Expected: all PASS.

- [ ] **Step 5: Run the full test suite**

Run: `pytest --tb=short -q`

Expected: every test PASS. No regressions in other CLI commands.

- [ ] **Step 6: Smoke test by hand**

Run:
```bash
solo-roll list | head -20
solo-roll list elements | head -10
solo-roll list --json | python -m json.tool | head -20
```

Expected:
- First: top-level group printed, then `elements/` lines.
- Second: only `elements/` group.
- Third: valid JSON with `tables` array.

- [ ] **Step 7: Commit**

```bash
git add src/solo_roll/cli.py tests/test_cli.py
git commit -m "feat(cli): solo-roll list subcommand for table discovery"
```

---

## Task 8: Update `CLAUDE.md` "Adding a table" section

**Files:**
- Modify: `CLAUDE.md` (around the "Adding a table" section)

- [ ] **Step 1: Read the current section**

Read `CLAUDE.md` and locate the "Adding a table" subsection (under Dev workflow). It currently reads:

```markdown
### Adding a table
Drop a JSON file into `data/tables/<name>.json`. Two formats — mutually exclusive:
- **Flat:** `{name, display_name, dice, source, entries: ["...", ...]}` — index by roll-1
- **Weighted:** `{name, display_name, dice, source, ranges: [{min, max, result}, ...]}` — used for d100 lookups with non-uniform weights

No rebuild. No reinstall. `solo-roll table <name>` reads it directly. Nested paths work too: `data/tables/elements/plottwist.json` → `solo-roll table elements/plottwist`.
```

- [ ] **Step 2: Replace the section**

Replace the bullets with this updated version (note the new `description` field and the closing line about `solo-roll list`):

```markdown
### Adding a table
Drop a JSON file into `data/tables/<name>.json`. Two formats — mutually exclusive:
- **Flat:** `{name, display_name, description, dice, source, entries: ["...", ...]}` — index by roll-1
- **Weighted:** `{name, display_name, description, dice, source, ranges: [{min, max, result}, ...]}` — used for d100 lookups with non-uniform weights

`description` is a one-line string explaining what the table covers. It is optional in the schema, but ship every new table with one — `solo-roll list` surfaces it as the table's user-facing summary, and the test suite asserts every shipped table has one.

No rebuild. No reinstall. `solo-roll table <name>` reads it directly. Nested paths work too: `data/tables/elements/plottwist.json` → `solo-roll table elements/plottwist`. Use `solo-roll list` (or `solo-roll list <prefix>`) to see what's available.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document description field + solo-roll list in adding-a-table"
```

---

## Task 9: Add "Available tables" + "Using arbitrary tables" sections to mythic-gme skill

**Files:**
- Modify: `skills/mythic-gme/SKILL.md`

- [ ] **Step 1: Locate insertion point**

Open `skills/mythic-gme/SKILL.md`. Find the existing "Detail Check / Meaning Pair" section (around line 142) and the following "Interpretation discipline" section (around line 156). Both new sections go BETWEEN these — i.e., after Detail Check ends, before Interpretation discipline begins.

- [ ] **Step 2: Insert the two new sections**

Insert this block immediately before the `## Interpretation discipline` heading:

```markdown
---

## Available tables

The toolkit ships a library of Mythic 2e themed tables in addition to the default meaning pair.

- **Top-level** (`action1`, `action2`, `descriptor1`, `descriptor2`) — canonical meaning-pair word lists.
- **`elements/`** — themed lookup tables for creatures, civilizations, locations, magic, omens, and more.
- **`mythic/`** — GME mechanics tables (event focus, etc.).

**To discover what's available, run `solo-roll list`** (or `solo-roll list <prefix>` to scope, e.g., `solo-roll list elements`). Each entry shows dice, entry count, display name, and a one-line description.

**Useful combinations:**

- `elements/creature` + `elements/creatureabilities` — flesh out a monster or horror.
- `elements/city` + `elements/civilization` — generate a settlement with culture.
- `elements/dungeon` + `elements/dungeontrap` — populate a delve with hazards.
- `elements/characterappearance` + `elements/characterpersonality` — shape an NPC quickly.

These are starting points; combine any tables that fit the moment.

---

## Using arbitrary tables

When the player asks for color or detail beyond a single meaning pair (creature description, location flavor, magic-item quirks), find candidate tables with `solo-roll list [prefix]`, then roll each chosen table:

```bash
solo-roll table elements/creature
solo-roll table elements/creatureabilities
```

**Apply the same Interpretation discipline as meaning-pair:**

- Roll first, interpret after.
- Announce every result verbatim — quote the words from each JSON output exactly.
- Every rolled word counts. Don't silently drop a result because it's awkward; dissonance is a feature.
- If a result is genuinely forced, name the word and the reason explicitly before discarding.

The toolkit's discipline rules are not specific to `meaning-pair`. They apply any time the dice produce words you must integrate into the fiction.
```

- [ ] **Step 3: Verify the file still reads cleanly**

Read the file end-to-end. Confirm:
- The `## Available tables` heading appears after Detail Check and before Interpretation discipline.
- Horizontal rules (`---`) are correctly placed between sections.
- No duplicate section headings.

- [ ] **Step 4: Commit**

```bash
git add skills/mythic-gme/SKILL.md
git commit -m "skill(mythic-gme): document available tables + extend discipline to arbitrary rolls"
```

---

## Task 10: Rewrite Mythic-coupling section in ironsworn skill

**Files:**
- Modify: `skills/ironsworn/SKILL.md` (lines 40-48 + line 71)

- [ ] **Step 1: Replace the "When Mythic GME skill is also loaded" section**

In `skills/ironsworn/SKILL.md`, find lines 40-48 (the existing section starting `## When Mythic GME skill is also loaded` through the line ending `...moment-to-moment action and color.`).

Replace the entire section with:

```markdown
## When Mythic GME skill is also loaded

If `mythic-gme` is loaded, do **NOT** substitute its mechanics for Ironsworn's native ones. Mythic mechanics (Scene Test, Fate Check, Event Focus, Chaos Factor) are opt-in tools the player invokes explicitly — for example, "run a scene test", "roll a fate check on whether the guard noticed me", "use Mythic for this event". Default behavior stays Ironsworn-native: Ask the Oracle for yes/no, Ironsworn oracles for inspiration, Ironsworn pacing. Do not surface Mythic mechanics unprompted, and do not pre-empt an Ironsworn move with a Mythic equivalent.
```

- [ ] **Step 2: Remove the Scene Test directive in "Scene framing"**

In the same file, find the "Scene framing" section (around line 65). It currently reads:

```markdown
## Scene framing

Good solo play needs clear scenes, not continuous sludge. Between scenes, briefly:
1. Summarize where the character is and what's unresolved.
2. Ask: "What do you want to do next?"
3. Once the player states intent, frame the next scene (one or two sentences of setup).
4. If Mythic is loaded, run a Scene Test first.
```

Remove the fourth bullet entirely. The result:

```markdown
## Scene framing

Good solo play needs clear scenes, not continuous sludge. Between scenes, briefly:
1. Summarize where the character is and what's unresolved.
2. Ask: "What do you want to do next?"
3. Once the player states intent, frame the next scene (one or two sentences of setup).
```

- [ ] **Step 3: Verify the file reads cleanly**

Read the file end-to-end. Confirm:
- Mythic-coupling section is the new directive paragraph (no "prefer it for" list).
- "Scene framing" has only three numbered steps.
- No stray references to "Mythic" instructing auto-substitution.

- [ ] **Step 4: Commit**

```bash
git add skills/ironsworn/SKILL.md
git commit -m "skill(ironsworn): make mythic-gme strictly opt-in, drop auto scene-test"
```

---

## Task 11: Generalize Mythic option in ironsworn-truths skill

**Files:**
- Modify: `skills/ironsworn-truths/SKILL.md` (lines 129-135)

- [ ] **Step 1: Check for unrelated working-tree changes first**

Before editing, confirm the existing modification to this file (visible at session start) is unrelated to this plan. Run:

```bash
git diff skills/ironsworn-truths/SKILL.md
```

If the diff shows changes you (or another session) already made for *this* feature, integrate them rather than overwriting. Otherwise, the existing change is unrelated; preserve it. **Do not stash, reset, or discard it.**

- [ ] **Step 2: Replace the "Mythic 2e graceful coupling" section**

Find the section starting `## Mythic 2e graceful coupling` (around line 129) through the line ending `If mythic-gme is not loaded, do not mention this option. Never auto-load it.` (around line 135).

Replace the entire section with:

```markdown
## Mythic 2e graceful coupling

If `mythic-gme` skill is loaded — detected by either (a) `mythic-gme` appearing in the active skills list shown to you by the harness, (b) a prior invocation of `solo-roll meaning-pair` or `solo-roll fate-check` in this session, or (c) the campaign `CLAUDE.md` listing it as an active skill — include this option in the per-truth menu:

> **Mythic meaning pair (player-directed)** — invoke `solo-roll meaning-pair` once. Before rolling, ask the player which target: a fresh truth/option, a quest seed for the chosen option, or both. Announce both words verbatim and apply the [Interpretation discipline](../mythic-gme/SKILL.md#interpretation-discipline) from the `mythic-gme` skill — roll one pair first, use both words (dissonance is a feature), and only roll a second pair or discard a word *explicitly* if the first reading is genuinely forced.

If `mythic-gme` is not loaded, do **not** mention this option. Never auto-load it. Never substitute it for the standard A/B/C/Roll/Fresh/Riff/Freeform paths unless the player asks for it.
```

- [ ] **Step 3: Verify the file reads cleanly**

Read the file end-to-end. Confirm:
- The Mythic option text now begins `Mythic meaning pair (player-directed)` and the player-direction sentence appears.
- The closing paragraph forbids auto-load and auto-substitution.
- No other sections were disturbed.

- [ ] **Step 4: Commit**

```bash
git add skills/ironsworn-truths/SKILL.md
git commit -m "skill(ironsworn-truths): generalize mythic option to truth or quest seed"
```

---

## Task 12: Final verification

**Files:** None (read-only verification).

- [ ] **Step 1: Full test suite**

Run: `pytest --tb=short -q`

Expected: 100% PASS.

- [ ] **Step 2: Smoke test the discoverability story**

Run:
```bash
solo-roll list
solo-roll list elements
solo-roll list mythic
solo-roll list --json | python -m json.tool | head -30
```

Expected:
- `solo-roll list`: three groups visible — `(top-level)`, `elements/`, `mythic/`. Every line has `dN  N entries  Display Name  — description`.
- `solo-roll list elements`: only `elements/` group.
- `solo-roll list mythic`: only `mythic/` group with `event-focus`.
- `--json`: parses, every entry has all five fields, `description` is non-null for every shipped table.

- [ ] **Step 3: Spot-check skill changes**

Read each modified skill file (`skills/mythic-gme/SKILL.md`, `skills/ironsworn/SKILL.md`, `skills/ironsworn-truths/SKILL.md`) end-to-end. Confirm headings, prose, and code blocks match the plan's intent. No orphan paragraphs, no broken markdown.

- [ ] **Step 4: Confirm `CLAUDE.md` mentions both `description` and `solo-roll list`**

Run: `grep -n -E "description|solo-roll list" CLAUDE.md`

Expected: at least one match for each in the "Adding a table" section.

- [ ] **Step 5: Branch ready for PR**

Run: `git log --oneline main..HEAD`

Expected: 11 commits in this branch, one per task (excluding this verification task), in order:
1. feat(tables): allow optional description field on table JSON
2. data: backfill description on meaning-pair tables
3. data: backfill description on character/creature elements tables
4. data: backfill description on place/object/magic elements tables
5. data: backfill description on remaining elements + mythic event-focus
6. test(tables): assert every shipped table has a description
7. feat(cli): solo-roll list subcommand for table discovery
8. docs: document description field + solo-roll list in adding-a-table
9. skill(mythic-gme): document available tables + extend discipline to arbitrary rolls
10. skill(ironsworn): make mythic-gme strictly opt-in, drop auto scene-test
11. skill(ironsworn-truths): generalize mythic option to truth or quest seed

If counts differ, investigate before opening PR.

---

## Coverage check (plan vs. spec)

| Spec section | Tasks |
|--------------|-------|
| 1. Schema change: optional `description` field | Task 1 |
| 2. CLI: `solo-roll list` | Task 7 |
| 3. Backfill descriptions | Tasks 2, 3, 4, 5 + assertion in Task 6 |
| 4a. mythic-gme "Available tables" section | Task 9 |
| 4b. mythic-gme "Using arbitrary tables" section | Task 9 |
| 5. ironsworn auto-substitution removed | Task 10 |
| 6. ironsworn-truths Mythic option generalized | Task 11 |
| 7. Tests | Tasks 1, 6, 7 |
| 8. CLAUDE.md "Adding a table" update | Task 8 |
| Out of scope (quickset listing, search, etc.) | — |

Every spec requirement maps to at least one task.
