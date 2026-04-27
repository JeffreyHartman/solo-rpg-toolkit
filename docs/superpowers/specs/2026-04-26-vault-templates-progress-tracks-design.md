# Sub-project 5 — Vault Templates + Progress Track Integration

**Date:** 2026-04-26
**Roadmap:** `docs/ROADMAP.md` § Sub-project 5
**Status:** spec (pre-implementation)

## Motivation

Solo-journaler currently ships a single NPC example (Kesta Ulfhild) and instructs the agent to create files in `People/`, `Places/`, `Threads/`, and `Lore/`. In practice this leaves Threads and Locations under-shaped — the agent improvises layouts, and long-running threads spread context across many session logs instead of consolidating in their own file.

This sub-project formalizes vault file shapes, adds a fictional-time convention so narrative immersion isn't broken by real-world ISO dates, and defines a system-agnostic seam where Ironsworn (and future systems) can overlay mechanics like progress tracks without polluting the journaler skill.

## Goals

1. Long-running Thread and Location files are **self-contained context** — the LLM can read one file and understand the full state of the thread or place without paging through session logs.
2. Vault narrative uses **fictional dates only**. Real-world ISO dates live in session log metadata only.
3. Solo-journaler stays **system-agnostic**. Ironsworn-specific concepts (progress tracks, ranks) live in the Ironsworn skill, not the journaler.
4. Ironsworn skill provides a **vault overlay** that adds a progress track table to Thread files when a vow is opened.

## Non-goals

- Bootstrapping new campaigns (sub-project 3.6).
- Statusline integration of active tracks (sub-project 3.7).
- Pre-published adventure / dual-vault GM secrets (sub-project 4.5).
- Shipping `_template.md` files in `example-campaign/playervault/`. The roadmap originally listed this; we drop it as YAGNI — SKILL.md examples drive agent behavior, and `_template.md` files would add a second source of truth that needs to be kept in sync.

## Approach: two-layer skill split

Solo-journaler owns generic vault shape. Ironsworn skill owns Ironsworn-specific overlays. When the campaign uses Ironsworn, both skills are active and the agent layers Ironsworn content on top of the generic shape.

Future systems (PF2e, OSR, etc.) follow the same pattern: their skill defines its own overlays. Solo-journaler never needs to know which system is in use.

## Vault file shapes

All shapes assume the player's vault at `./playervault/`. Wikilinks (`[[Name]]`) are used throughout for Obsidian navigability.

### Thread (`./playervault/Threads/<Name>.md`)

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

**Required sections:** metadata block, What we know, What we suspect, Progression, Resolution.
**Optional sections:** People, Places (only present once entries exist).

The agent updates this file directly when a session reveals new information. Suspicions move to "What we know" when confirmed. Progression entries link to fictional dates, not session numbers — but the fictional date can be matched to a session by checking the Session Log.

### Location (`./playervault/Places/<Name>.md`)

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

**Required sections:** metadata block, Description.
**Optional sections:** What we know, What we suspect, People, Threads, Notable features, Visits.

### NPC (existing — update for fictional dates)

The existing `Kesta Ulfhild.md` example currently uses `**Met**: 2026-04-26`. Update to fictional date: `**Met**: Snowmonth 14, at the smithy in [[Stonebeck]]`. Same shape otherwise.

### Session log — vault narrative side (`./playervault/Session Log/Session NNN.md`)

```markdown
# Session 001

**Played**: 2026-04-26
**In-fiction**: Snowmonth 14, Year of the Iron Wolf

Arrived at [[Ashveil]] after a hard road. [[Ossian]] had walked out of [[The Eastern Wood]] on torn feet…
```

**Filename:** `Session NNN.md` — three-digit zero-pad, sequential. Both `./sessions/Session NNN.md` (mechanical) and `./playervault/Session Log/Session NNN.md` (narrative) share the number.

**Top metadata block:** `Played` is the real-world ISO date the session was run; `In-fiction` is the in-story date. These are the only places ISO dates appear in vault content.

### Session log — mechanical side (`./sessions/Session NNN.md`)

Free-form mechanical log: rolls, oracle results, CF shifts, threads opened/closed, NPCs introduced, **Oracle reasoning** (interpretations of rolls and oracle results — replaces the older "Secrets / DM notes" framing). No structural template required; the heading "Oracle reasoning" is the agreed name when a structured section is wanted.

## Date convention

**Fictional dates only in vault narrative content.** People, Places, Threads, character notes — all use the in-fiction calendar string.

**Real-world ISO dates appear only:**
- As `Played:` metadata at the top of session log files (both mechanical and narrative)
- (Nowhere else in vault narrative)

**Calendar system:** free-form string. Player declares format at first session (e.g., `Snowmonth 14, Year of the Iron Wolf`, `Day 12 of the journey`, `4717 AR Sarenith 3`). The agent maintains continuity from prior writing.

**Current date:** stored at the top of `./playervault/Character.md` when a character file exists (Ironsworn campaigns ship one via `skills/ironsworn/character-template.md`):

```markdown
**Current date**: Snowmonth 14, Year of the Iron Wolf
```

For campaigns without a `Character.md` (no system skill loaded, or a system that doesn't track a character sheet), the agent stores `Current date` at the top of `./playervault/Lore/Calendar.md` instead. Solo-journaler creates this file on first session if no `Character.md` is present.

Set during first session if blank. Updated at session end based on in-fiction time elapsed (the agent asks the player or infers from narrative).

**Cross-references between vault files use fictional dates.** No ISO leaks into Threads/Places/Progression lists.

## Solo-journaler SKILL.md changes

**New / updated sections:**

1. **Vault structure** — unchanged.
2. **Mechanical state** — unchanged.
3. **Filename conventions** — replace ISO-date rule for session logs with `Session NNN.md` (3-digit zero-pad). ISO date format remains for any future mechanical files (none currently).
4. **Threads and Places are canonical context** (new) — instructs the agent: when new info is revealed mid-session, update the relevant Thread/Place file directly. Don't leave context stranded in the session log. Move suspicions to "What we know" when confirmed. Add wikilinks to People/Places when introduced.
5. **Fictional dates in vault, ISO only in session metadata** (new) — explicit rule plus the `Current date` location in Character.md.
6. **Session-end instruction** — add: "Ask the player how much in-fiction time has passed (or infer from narrative); update `Character.md` current date."
7. **Examples** — add Thread example, add Location example. Update existing NPC example and session-log example to use fictional dates and `Session 001` filename.

## Ironsworn SKILL.md changes (overlay)

Add a new section that fires when the agent opens a Thread for a vow:

> **Vow opened — vault overlay.** When you create a new Thread file for a vow (Swear an Iron Vow, or any vow you're tracking with a progress track), insert this block immediately after the metadata block and before `## What we know`:
>
> ```markdown
> ## Progress (<Rank>, 10 boxes, <ticks-per-mark>)
>
> | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
> |---|---|---|---|---|---|---|---|---|----|
> |   |   |   |   |   |   |   |   |   |    |
> ```
>
> **Rank → ticks-per-mark phrasing:**
> - Troublesome → `3 ticks per mark`
> - Dangerous → `2 ticks per mark`
> - Formidable → `1 tick per mark`
> - Extreme → `1 tick per 2 marks`
> - Epic → `1 tick per 4 marks`
>
> **Cell values:** empty = 0 ticks, `1`/`2`/`3` = partial ticks (1–3 of 4), `X` = full box (4 ticks). Fill left-to-right.

The progress fill rules at `skills/ironsworn/SKILL.md:80` (marks per rank, fractional handling) remain authoritative and don't need changes.

## Progress table format

```markdown
## Progress (Dangerous, 10 boxes, 2 ticks per mark)

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|----|
| X | X | 3 |   |   |   |   |   |   |    |
```

- Renders as a 10-column table in Obsidian.
- One cell per box. Cell content tracks tick state at quarter granularity.
- Heading carries rank + ticks-per-mark so the agent can compute updates without consulting external state.
- The agent updates cells in place (e.g., empty → `2` → `X`) as marks accrue.

## Test plan

**Unit (extend existing skill-content tests):**

- Verify `solo-journaler/SKILL.md` contains a Thread example section with the required headings (`What we know`, `What we suspect`, `Progression`, `Resolution`).
- Verify `solo-journaler/SKILL.md` contains a Location example section with `Description` and at least one of (`What we know`, `Visits`).
- Verify `solo-journaler/SKILL.md` references `Session NNN.md` filename pattern, not ISO-date pattern, for session logs.
- Verify `solo-journaler/SKILL.md` contains a "fictional dates" rule and a "Current date in Character.md" instruction.
- Verify `ironsworn/SKILL.md` contains the vault overlay instruction with the progress table template.

**Manual integration:**

- Run `solo-campaign` to create a fresh test campaign with Ironsworn enabled.
- Open Obsidian on the player vault; confirm that the Thread and Location templates render readably.
- Simulate opening a vow via the agent; confirm the progress table appears in the Thread file in the documented position.
- Confirm `Character.md` has a `Current date` line and that the agent updates it after a mock session.

## Files touched

- `skills/solo-journaler/SKILL.md` — examples added, new sections, filename convention update, fictional-date rule.
- `skills/ironsworn/SKILL.md` — new "Vow opened — vault overlay" section.
- `skills/ironsworn/character-template.md` — add `**Current date**:` line at top (so new campaigns start with the field).
- `example-campaign/playervault/Character.md` — add `**Current date**:` line if the file exists in the example campaign; otherwise no change (current example-campaign ships without a Character.md, which is fine).
- `tests/test_skills_content.py` (or equivalent existing skill-content test) — new assertions per Test plan.

## Risks

- **Existing campaigns adopting fictional dates mid-stream:** new sessions get `Session NNN.md` and fictional dates; old ISO-named session files stay as-is. Agent reads both. Cross-link between old and new sessions falls on the player. Acceptable — sub-project 5 doesn't promise migration.
- **Player chooses no calendar system:** the `Current date` field stays blank or holds a free-form `Day 1` style string. Agent must tolerate that — the convention is "string", not "structured date".
- **Progress table edits in Obsidian:** if the player edits the table directly (typo, mis-mark), the agent re-reads and may correct on next mark. Document that the file is canonical state — manual edits override agent memory.
