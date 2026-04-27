# Vault Templates + Progress Tracks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize Thread / Location vault file shapes, switch vault narrative to fictional dates, rename session logs to `Session NNN.md`, and add an Ironsworn vault overlay that writes a progress-track table to vow Threads.

**Architecture:** Two-layer split. `skills/solo-journaler/SKILL.md` carries system-agnostic vault shape (Thread + Location examples, fictional-date rule, sequential session filenames). `skills/ironsworn/SKILL.md` adds an overlay section that writes a progress table to vow Threads. `skills/ironsworn/character-template.md` gains a `Current date` line. New `tests/test_skills_content.py` asserts skill markdown contains the required sections so future edits don't silently break the agent contract.

**Tech Stack:** Python 3.12, pytest, plain markdown skills.

**Spec:** `docs/superpowers/specs/2026-04-26-vault-templates-progress-tracks-design.md`

---

## File Structure

**Created:**
- `tests/test_skills_content.py` — assertions over markdown content of `skills/solo-journaler/SKILL.md`, `skills/ironsworn/SKILL.md`, and `skills/ironsworn/character-template.md`.

**Modified:**
- `skills/solo-journaler/SKILL.md` — replace NPC-only example set with Thread + Location + updated NPC examples; add fictional-date rule; add canonical-context rule; switch session-log filename convention to `Session NNN.md`; update session-end instruction set.
- `skills/ironsworn/SKILL.md` — add "Vow opened — vault overlay" section instructing the agent to insert a progress-table block into Thread files.
- `skills/ironsworn/character-template.md` — add `**Current date**:` placeholder line in the basics block.

**Untouched but worth noting:**
- `example-campaign/playervault/` — directory structure unchanged; no `_template.md` files added (per spec, dropped as YAGNI).
- `skills/ironsworn/SKILL.md:80` — existing rank → step-size table stays authoritative; the overlay section references it instead of duplicating.

---

## Task 1: Create skill-content test scaffolding

**Files:**
- Create: `tests/test_skills_content.py`

- [ ] **Step 1: Write the file with shared fixtures**

```python
"""Assertions over the markdown content of bundled skills.

The agent reads these files at runtime; if a section it relies on is
removed or renamed, behavior breaks silently. These tests pin the
contract.
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"


@pytest.fixture
def journaler_skill() -> str:
    return (SKILLS_DIR / "solo-journaler" / "SKILL.md").read_text()


@pytest.fixture
def ironsworn_skill() -> str:
    return (SKILLS_DIR / "ironsworn" / "SKILL.md").read_text()


@pytest.fixture
def ironsworn_character_template() -> str:
    return (SKILLS_DIR / "ironsworn" / "character-template.md").read_text()


def test_skills_dir_exists():
    assert SKILLS_DIR.is_dir()
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `pytest tests/test_skills_content.py -v`
Expected: PASS (1 test).

- [ ] **Step 3: Commit**

```bash
git add tests/test_skills_content.py
git commit -m "test(skills): add scaffolding for skill-content assertions"
```

---

## Task 2: Pin Thread example in solo-journaler SKILL.md

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_journaler_has_thread_example(journaler_skill):
    """Thread example must be present with all required sections."""
    # Heading anchors example block
    assert "## Example Thread file" in journaler_skill or \
           "## Example thread file" in journaler_skill
    # Required sections inside the Thread example
    for heading in (
        "## What we know",
        "## What we suspect",
        "## Progression",
        "## Resolution",
    ):
        assert heading in journaler_skill, f"missing Thread heading: {heading}"
    # Stakes line is part of the metadata block
    assert "**Stakes**" in journaler_skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_journaler_has_thread_example -v`
Expected: FAIL (Thread example not yet added).

- [ ] **Step 3: Add Thread example to solo-journaler SKILL.md**

In `skills/solo-journaler/SKILL.md`, after the existing `## Example session log (vault side)` section, insert:

````markdown
## Example Thread file

`./playervault/Threads/Find the Sister.md`:

```markdown
# Find the Sister

- **Opened**: Snowmonth 14
- **Status**: open
- **Stakes**: Sister vanished six months ago. Promise to mother on her deathbed.

## What we know
- Sister was last seen heading east from [[Stonebeck]]
- [[Kesta Ulfhild]] knew her name before I said it

## What we suspect
- Kesta is hiding something — possibly knew sister personally
- The mimicking thing in [[Ashveil]] may be related (timing lines up)

## People
- [[Kesta Ulfhild]] — smith, evasive
- [[Mara]] — bound by promise to be told everything

## Places
- [[Stonebeck]] — last known location
- [[The Eastern Wood]] — direction of travel

## Progression
- Snowmonth 14 — Kesta revealed she knew the name
- Snowmonth 21 — found tracks heading east

## Resolution
(filled when closed)
```

Required sections: metadata block (Opened / Status / Stakes), `What we know`, `What we suspect`, `Progression`, `Resolution`. People and Places sections are optional — add them once entries exist. Move suspicions to `What we know` when confirmed.
````

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_journaler_has_thread_example -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): add Thread example with self-contained-context shape"
```

---

## Task 3: Pin Location example in solo-journaler SKILL.md

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_journaler_has_location_example(journaler_skill):
    """Location example must be present with required sections."""
    assert "## Example Location file" in journaler_skill or \
           "## Example location file" in journaler_skill
    # The example file uses Stonebeck — that string should appear in a
    # Place context (it already appears in the Thread example, so the
    # check below depends on the heading anchor above)
    assert "# Stonebeck" in journaler_skill
    for heading in (
        "## Description",
        "## Visits",
    ):
        assert heading in journaler_skill, f"missing Location heading: {heading}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_journaler_has_location_example -v`
Expected: FAIL (Location example not yet added).

- [ ] **Step 3: Add Location example to solo-journaler SKILL.md**

In `skills/solo-journaler/SKILL.md`, after the Thread example added in Task 2, insert:

````markdown
## Example Location file

`./playervault/Places/Stonebeck.md`:

```markdown
# Stonebeck

- **First visited**: Snowmonth 14
- **Type**: Mining village, edge of [[The Eastern Wood]]

## Description
Stone-built, smoke-stained. Smithy at the north end. Maybe forty souls.

## What we know
- Iron-rich seams nearby — village livelihood
- Travelers stop here before heading east

## What we suspect
- Locals know more about the woods than they share

## People
- [[Kesta Ulfhild]] — smith
- [[Old Rann]] — innkeep, friendly

## Threads
- [[Find the Sister]] — sister last seen here
- [[The Eastern Wood Mimic]] — locals avoid the woods

## Notable features
- The smithy — Kesta's domain, watched our hands
- The ridge road east — fades into woods after a mile

## Visits
- Snowmonth 14 — arrived, met Kesta
- Snowmonth 21 — passed through northbound
```

Required sections: metadata block (First visited / Type), `Description`. Other sections (`What we know`, `What we suspect`, `People`, `Threads`, `Notable features`, `Visits`) are optional — add once content exists.
````

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_journaler_has_location_example -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): add Location example matching Thread shape"
```

---

## Task 4: Update existing NPC example to fictional date

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_npc_example_uses_fictional_date(journaler_skill):
    """The Kesta NPC example must not use ISO-date strings — vault
    narrative is fictional-date only."""
    # Find the NPC example block. Anchor on the existing heading.
    assert "## Example NPC file" in journaler_skill
    # The Kesta block previously contained `Met: 2026-04-26`. After this
    # change it must use a fictional-date string and must not contain
    # any 4-digit-year-dash-month-dash-day pattern within the example.
    npc_section_start = journaler_skill.index("## Example NPC file")
    # The next "## " heading bounds the section
    next_heading = journaler_skill.find("\n## ", npc_section_start + 1)
    npc_section = journaler_skill[npc_section_start:next_heading if next_heading != -1 else None]
    # No ISO-date inside the NPC example
    import re
    assert re.search(r"\b20\d{2}-\d{2}-\d{2}\b", npc_section) is None, \
        "NPC example still contains an ISO date"
    # And the fictional Met line is present
    assert "**Met**: " in npc_section
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_npc_example_uses_fictional_date -v`
Expected: FAIL (current example uses `2026-04-26`).

- [ ] **Step 3: Update Kesta example to fictional date**

The current example (lines roughly 80–100 of `skills/solo-journaler/SKILL.md`) starts with the heading `## Example NPC file`. First, add or rename the section heading so it reads exactly `## Example NPC file` if it doesn't already.

Then in the Kesta code block, replace the metadata line:

```markdown
- **Met**: 2026-04-26, at the smithy in [[Stonebeck]]
```

with:

```markdown
- **Met**: Snowmonth 14, at the smithy in [[Stonebeck]]
```

And replace the `## Last seen` line:

```markdown
[[Stonebeck]], morning of Session 1.
```

with:

```markdown
[[Stonebeck]], morning of [[Session 001]].
```

(Wikilink uses the new sequential session filename — see Task 5.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_npc_example_uses_fictional_date -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): switch NPC example to fictional date"
```

---

## Task 5: Switch session-log filename convention to `Session NNN.md`

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_journaler_uses_sequential_session_filenames(journaler_skill):
    """Session log filenames are `Session NNN.md` — three-digit pad,
    sequential, not ISO-date based."""
    # The filename-conventions section must reference the new pattern
    assert "Session NNN.md" in journaler_skill
    # And must NOT prescribe ISO-date filenames for session logs.
    # Specifically: the old wording contained
    # "ISO date for all session logs ... 2026-04-26.md"
    # which we are removing. Allow the literal date elsewhere (e.g. in
    # the Played: metadata of the session-log example).
    assert "ISO date for all session logs" not in journaler_skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_journaler_uses_sequential_session_filenames -v`
Expected: FAIL.

- [ ] **Step 3: Rewrite Filename conventions section**

In `skills/solo-journaler/SKILL.md`, find the `## Filename conventions` section. Replace its body with:

```markdown
- Title case for proper nouns: `Kesta Ulfhild.md`, `The Old Road.md`
- Sequential, three-digit zero-padded filenames for session logs (both `./sessions/` and `./playervault/Session Log/`): `Session 001.md`, `Session 002.md`, …, `Session NNN.md`. Both folders share the number — `./sessions/Session 001.md` and `./playervault/Session Log/Session 001.md` describe the same play session.
- Lower-kebab for top-level mechanical files: `mythic-state.md`
```

Also: update the two existing references in the same file. Find:

```markdown
- `./sessions/YYYY-MM-DD.md` — mechanical session log:
```

Replace with:

```markdown
- `./sessions/Session NNN.md` — mechanical session log:
```

And find:

```markdown
1. Write `./sessions/YYYY-MM-DD.md` with: rolls made,
```

Replace with:

```markdown
1. Write `./sessions/Session NNN.md` with: rolls made,
```

And find:

```markdown
2. Write `./playervault/Session Log/YYYY-MM-DD.md` —
```

Replace with:

```markdown
2. Write `./playervault/Session Log/Session NNN.md` —
```

(Each `NNN` stands for the next sequential number; the agent computes it from existing files in the folder.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_journaler_uses_sequential_session_filenames -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): use sequential Session NNN.md filenames"
```

---

## Task 6: Update session-log narrative example to new shape

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_session_log_example_has_dual_date_metadata(journaler_skill):
    """The vault-side session-log example uses a `Session 001` heading
    and a top metadata block with both Played (real-world ISO) and
    In-fiction (fictional) dates."""
    # Anchor: the example uses heading `# Session 001`
    assert "# Session 001" in journaler_skill
    # Metadata block contents
    assert "**Played**: " in journaler_skill
    assert "**In-fiction**: " in journaler_skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_session_log_example_has_dual_date_metadata -v`
Expected: FAIL.

- [ ] **Step 3: Update the vault-side session-log example**

Find the existing block in `skills/solo-journaler/SKILL.md` that begins:

````markdown
## Example session log (vault side)

`./playervault/Session Log/2026-04-26.md`:

```markdown
# Session — 2026-04-26
````

Replace the example body with:

````markdown
## Example session log (vault side)

`./playervault/Session Log/Session 001.md`:

```markdown
# Session 001

**Played**: 2026-04-26
**In-fiction**: Snowmonth 14, Year of the Iron Wolf

Arrived at [[Ashveil]] after a hard road. [[Ossian]] had walked out of [[The Eastern Wood]] on torn feet; [[Fen]] found him and was already tending him when I came down the track.

Whatever took the missing people from Ashveil — it mimics voices. It knows mine now. That's not something you forget.

[[Mara]] was steady when I told her about [[Cian]]. She extracted a promise: I tell her everything, not just what the Ring hears. Fair.

Cian is back, but he's not right.
```
````

(`**Played**` is the real-world ISO date; `**In-fiction**` is the in-story date. These are the only places ISO dates appear in vault content.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_session_log_example_has_dual_date_metadata -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): rewrite session-log example with dual-date metadata"
```

---

## Task 7: Add fictional-dates rule + Current-date storage

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_journaler_has_fictional_dates_rule(journaler_skill):
    """The skill must document the fictional-dates-only rule and where
    the current in-fiction date is stored."""
    # Heading anchors the rule
    assert "## Dates" in journaler_skill or \
           "## Fictional dates" in journaler_skill
    # Storage location for current date
    assert "Current date" in journaler_skill
    assert "Character.md" in journaler_skill
    assert "Calendar.md" in journaler_skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_journaler_has_fictional_dates_rule -v`
Expected: FAIL.

- [ ] **Step 3: Add a "Dates" section to solo-journaler SKILL.md**

In `skills/solo-journaler/SKILL.md`, after the `## Linking conventions` section and before `## Filename conventions`, insert:

```markdown
## Dates

Vault narrative uses **fictional dates only** — the in-fiction calendar string the player has chosen for the campaign (e.g. `Snowmonth 14, Year of the Iron Wolf`, `Day 12 of the journey`, or `4717 AR Sarenith 3`). Format is free-form; maintain continuity from prior writing.

Real-world ISO dates appear only in the `**Played**:` metadata line at the top of session-log files. They never appear in People, Places, Threads, or other narrative content.

**Current date** is stored at the top of `./playervault/Character.md` when a character file exists:

```markdown
**Current date**: Snowmonth 14, Year of the Iron Wolf
```

If the campaign has no `Character.md` (no system skill loaded, or a system that doesn't track a character sheet), store the current date at the top of `./playervault/Lore/Calendar.md` instead. Create that file on first session if needed.

Set the current date during the first session if blank. At session end, ask the player how much in-fiction time has passed (or infer from narrative) and update.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_journaler_has_fictional_dates_rule -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): add fictional-dates rule and current-date storage"
```

---

## Task 8: Add canonical-context rule (Threads/Places are not just stubs)

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_journaler_has_canonical_context_rule(journaler_skill):
    """The skill must instruct the agent to keep Thread / Place files
    self-contained — updating them in place rather than letting context
    drift into session logs."""
    assert "canonical context" in journaler_skill.lower()
    # And must mention moving suspicions to `What we know` when confirmed
    assert "What we know" in journaler_skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_journaler_has_canonical_context_rule -v`
Expected: FAIL.

- [ ] **Step 3: Add a "Threads and Places are canonical context" subsection**

In `skills/solo-journaler/SKILL.md`, inside the existing `## Writing rules` section, after the `### During the session` block, insert:

```markdown
### Threads and Places are canonical context

A Thread or Place file is a **synthesis layer** — the agent must be able to read the single file and understand the full state of the thread or place without paging through session logs.

When new info is revealed mid-session:

- Update the relevant Thread / Place file directly. Don't leave the new fact stranded in the session log.
- Move suspicions from `What we suspect` to `What we know` when they're confirmed.
- Add wikilinks to People / Places / Threads as they're introduced.
- Append to the `Progression` (Threads) or `Visits` (Places) list with a short fictional-date-prefixed entry.

Session logs remain history; Thread and Place files remain the canonical, current view.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_journaler_has_canonical_context_rule -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): add canonical-context rule for Threads and Places"
```

---

## Task 9: Add session-end "update Current date" instruction

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/solo-journaler/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_journaler_session_end_updates_current_date(journaler_skill):
    """Session-end procedure must include updating the current
    in-fiction date."""
    # Anchor: the existing heading
    assert "### At the end of a session" in journaler_skill
    # The end-of-session block must mention updating Current date
    end_idx = journaler_skill.index("### At the end of a session")
    next_heading = journaler_skill.find("\n## ", end_idx + 1)
    end_block = journaler_skill[end_idx:next_heading if next_heading != -1 else None]
    assert "Current date" in end_block
    assert "in-fiction" in end_block.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_journaler_session_end_updates_current_date -v`
Expected: FAIL.

- [ ] **Step 3: Add the bullet to the end-of-session checklist**

In `skills/solo-journaler/SKILL.md`, find the `### At the end of a session` section. Append a new numbered bullet to its list (after the existing Character.md update bullet):

```markdown
6. Ask the player how much in-fiction time has passed (or infer from narrative); update `**Current date**:` at the top of `./playervault/Character.md` (or `./playervault/Lore/Calendar.md` if no Character.md exists).
```

If the existing list has fewer or more bullets, use the next sequential number. If a different bullet already covers Current-date update, edit that bullet to include the in-fiction language instead of adding a duplicate.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_journaler_session_end_updates_current_date -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/solo-journaler/SKILL.md
git commit -m "feat(solo-journaler): update Current date at session end"
```

---

## Task 10: Add `Current date` placeholder to Ironsworn character template

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/ironsworn/character-template.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_ironsworn_character_template_has_current_date(ironsworn_character_template):
    """The Ironsworn character template must include a Current date
    placeholder so new campaigns start with the field present."""
    assert "**Current date:**" in ironsworn_character_template or \
           "**Current date**:" in ironsworn_character_template
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_ironsworn_character_template_has_current_date -v`
Expected: FAIL.

- [ ] **Step 3: Add the line to the character template**

In `skills/ironsworn/character-template.md`, find the `## Basics` block:

```markdown
## Basics

**Name:**  
**Look:** (short physical description — 1-2 sentences)  
**Background:** (who they were before the vow)
```

Replace it with:

```markdown
## Basics

**Name:**  
**Look:** (short physical description — 1-2 sentences)  
**Background:** (who they were before the vow)  
**Current date:** (in-fiction calendar string — set at first session)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_ironsworn_character_template_has_current_date -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/ironsworn/character-template.md
git commit -m "feat(ironsworn): add Current date field to character template"
```

---

## Task 11: Add Ironsworn vow-overlay section

**Files:**
- Modify: `tests/test_skills_content.py`
- Modify: `skills/ironsworn/SKILL.md`

- [ ] **Step 1: Add failing test**

Append to `tests/test_skills_content.py`:

```python
def test_ironsworn_has_vow_vault_overlay(ironsworn_skill):
    """The Ironsworn skill must instruct the agent to write a progress
    table block to the vow's Thread file when a vow is opened."""
    # Heading anchors the section
    assert "## Vow opened" in ironsworn_skill or \
           "### Vow opened" in ironsworn_skill or \
           "Vow opened — vault overlay" in ironsworn_skill
    # Table column header line — verifies the template is literally
    # present rather than just described
    assert "| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |" in ironsworn_skill
    # Required heading-format hints
    assert "ticks per mark" in ironsworn_skill
    # All five ranks documented
    for rank in ("Troublesome", "Dangerous", "Formidable", "Extreme", "Epic"):
        assert rank in ironsworn_skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills_content.py::test_ironsworn_has_vow_vault_overlay -v`
Expected: FAIL (no such section yet — current SKILL.md has rank table but no vault overlay block).

- [ ] **Step 3: Add the overlay section to `skills/ironsworn/SKILL.md`**

Append a new top-level section to `skills/ironsworn/SKILL.md` (after the existing content, near the bottom is fine — pick a position adjacent to existing vow / progress-track guidance if one is obvious):

````markdown
## Vow opened — vault overlay

When you create a new Thread file in the player vault for a vow (Swear an Iron Vow, or any vow you're tracking with a progress track), insert this block immediately after the metadata block (Opened / Status / Stakes) and before `## What we know`:

```markdown
## Progress (<Rank>, 10 boxes, <ticks-per-mark>)

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|----|
|   |   |   |   |   |   |   |   |   |    |
```

**Heading — `<ticks-per-mark>` phrasing by rank:**

| Rank        | Heading suffix         |
|-------------|------------------------|
| Troublesome | `3 ticks per mark`     |
| Dangerous   | `2 ticks per mark`     |
| Formidable  | `1 tick per mark`      |
| Extreme     | `1 tick per 2 marks`   |
| Epic        | `1 tick per 4 marks`   |

**Cell values:** empty cell = 0 ticks, `1` / `2` / `3` = partial ticks (1–3 of 4), `X` = full box (4 ticks). Fill left-to-right.

When the player marks progress, update cells in place (e.g. empty → `2` → `X` → next cell starts at `2`). The fill rules at the live-stat-tracking section above (Troublesome 3, Dangerous 2, Formidable 1, Extreme 0.5, Epic 0.25 — partial boxes tracked, never rounded prematurely) remain authoritative.

This overlay does not replace the live progress shown in `Character.md` Vows callouts — both are kept in sync. The Thread file is canonical for the vow's narrative arc; the Character.md vow line is the live mechanical resource.
````

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills_content.py::test_ironsworn_has_vow_vault_overlay -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skills_content.py skills/ironsworn/SKILL.md
git commit -m "feat(ironsworn): vault overlay — write progress table to vow Threads"
```

---

## Task 12: Full test suite + lint pass

**Files:**
- None (verification only)

- [ ] **Step 1: Run full pytest suite**

Run: `pytest --tb=short -q`
Expected: all tests pass — pre-existing 75+ tests plus the 9 new content tests added in Tasks 1–11. Investigate any regression.

- [ ] **Step 2: Visual review of `skills/solo-journaler/SKILL.md`**

Open the file. Read top-to-bottom. Verify:

- Vault structure block — unchanged.
- Mechanical state block — `Session NNN.md` filenames, not ISO.
- Writing rules — start, during, canonical-context subsection, end (with Current-date bullet).
- Dates section — fictional-dates rule, Current-date storage with both `Character.md` and `Calendar.md` paths.
- Linking conventions — unchanged.
- Filename conventions — `Session NNN.md` pattern, no ISO-date rule for session logs.
- Examples: NPC (fictional Met date), session log (Session 001, dual-date metadata), Thread (full shape), Location (full shape).

- [ ] **Step 3: Visual review of `skills/ironsworn/SKILL.md`**

Open the file. Verify the new "Vow opened — vault overlay" section is present and renders the progress-table template literally (the agent will copy it).

- [ ] **Step 4: Visual review of `skills/ironsworn/character-template.md`**

Verify the `## Basics` block has the new `Current date:` line.

- [ ] **Step 5: Commit only if anything was tweaked during review**

If review surfaced a fix, commit with:

```bash
git add -p
git commit -m "docs(skills): polish from review pass"
```

Otherwise no commit.

---

## Task 13: Manual integration walkthrough

**Files:**
- None (manual verification — record outcome in this file by checking the boxes below).

- [ ] **Step 1: Bootstrap a throwaway test campaign**

```bash
solo-campaign vault-test /tmp/vault-test --skills ironsworn,solo-journaler,mythic-gme
```

(Use whatever invocation matches the current `solo-campaign` CLI; the spec does not require any bootstrap changes.)

- [ ] **Step 2: Inspect the bootstrapped vault**

```bash
ls /tmp/vault-test/playervault/
cat /tmp/vault-test/playervault/Character.md   # if Ironsworn copies the template
```

Expected: vault directories present (People, Places, Threads, Lore, Session Log). If Character.md exists, it has a `**Current date:**` line.

- [ ] **Step 3: Open the vault in Obsidian**

Open `/tmp/vault-test/playervault/` as an Obsidian vault. Manually create a stub Thread file using the example shape from `skills/solo-journaler/SKILL.md` and a stub Location file similarly. Confirm wikilinks resolve and headings render as expected.

- [ ] **Step 4: Render a progress table**

Inside the stub Thread file, paste the progress-table block from the new Ironsworn overlay section. Confirm the 10-column table renders correctly in Obsidian preview, including filled (`X`), partial (`2`, `3`), and empty cells in different positions.

- [ ] **Step 5: Tear down**

```bash
rm -rf /tmp/vault-test
```

- [ ] **Step 6: Update roadmap**

Edit `docs/ROADMAP.md` Sub-project 5 section: tick the boxes for the items completed (Thread/Location examples, fictional dates, progress-table integration). Note explicitly that `_template.md` files were dropped as YAGNI per the design spec.

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark sub-project 5 complete"
```

---

## Self-Review Notes

- **Spec coverage:**
  - Two-layer skill split → Tasks 11 (Ironsworn overlay) + Tasks 2/3/7/8/9 (system-agnostic journaler additions).
  - Thread shape → Task 2.
  - Location shape → Task 3.
  - NPC fictional date → Task 4.
  - Session NNN.md filenames → Tasks 5 + 6.
  - Fictional-dates rule + Current-date storage → Task 7.
  - Canonical-context rule → Task 8.
  - Session-end Current-date update → Task 9.
  - Character.md Current-date placeholder (Ironsworn) → Task 10.
  - Ironsworn progress-table overlay → Task 11.
  - Test plan (unit + manual) → Tasks 1–13.
  - Out-of-scope items (`_template.md`, statusline tracks, dual-vault, bootstrap customization) → not present in plan, intentionally.

- **Placeholder scan:** No "TBD" / "TODO" / "implement later". Each step contains the literal markdown to insert and the literal command to run.

- **Type / heading consistency:**
  - `## Example NPC file`, `## Example Thread file`, `## Example Location file`, `## Example session log (vault side)` — same family of section headings.
  - `## Dates` introduced in Task 7, referenced consistently.
  - `Current date` capitalized identically across solo-journaler text, Character.md template, and tests.
  - Progress-table column header `| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |` matches between Task 11's spec template and the test assertion.
