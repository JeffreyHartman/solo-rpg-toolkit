---
name: solo-journaler
description: Use during any solo RPG session to maintain notes in the player vault at ./playervault/. Activates when new information is introduced — NPCs met, locations visited, vows made, threads opened, discoveries revealed — and at end of session to write session logs.
---

# Solo Journaler Skill

Single source of truth: `./playervault/` relative to campaign root. Open this folder in Obsidian between sessions.

## Vault structure

```
./playervault/
├── Character.md            # current character sheet state
├── Session Log/            # one file per session, sequential
│   └── Session 001.md
├── People/                 # NPCs the character has met
│   └── Kesta Ulfhild.md
├── Places/                 # places the character has been or been told of
│   └── Stonebeck.md
├── Threads/                # active vows, mysteries the character is tracking
│   └── Find the Sister.md
└── Lore/                   # worldbuilding the character has learned
    └── Truths/
```

## Mechanical state (not in vault)

- `./mythic-state.md` — chaos factor, threads list, characters list (Mythic GME only; absent otherwise)
- `./sessions/Session NNN.md` — mechanical session log: rolls, oracle results, CF shifts, reasoning

## Writing rules

### At the start of a session

1. Read `./sessions/` for the most recent mechanical log. If `./sessions/` is empty, this is the first session — skip this step.
2. Read `./mythic-state.md` if Mythic is active.
3. Read `./playervault/Character.md` for current character state.
4. Recap for the player: where things stand, what hooks are open.

### During the session

When something note-worthy happens, write it inline — tell the player briefly, then continue:

> *"Adding Kesta to your People folder."*

Minimal skeleton during play. Flesh out at session end.

- New NPC met → create `./playervault/People/<Name>.md`
- New location → create `./playervault/Places/<Name>.md`
- Vow made or mystery opened → create `./playervault/Threads/<Name>.md`
- World lore established → add to `./playervault/Lore/` (Ironsworn world truths go in `Lore/Truths/`; other lore as individual files directly in `Lore/`)

### Threads and Places are canonical context

A Thread or Place file is a **synthesis layer** — the agent must be able to read the single file and understand the full state of the thread or place without paging through session logs.

When new info is revealed mid-session:

- Update the relevant Thread / Place file directly. Don't leave the new fact stranded in the session log.
- Move suspicions from `What we suspect` to `What we know` when they're confirmed.
- Add wikilinks to People / Places / Threads as they're introduced.
- Append to the `Progression` (Threads) or `Visits` (Places) list with a short fictional-date-prefixed entry.

Session logs remain history; Thread and Place files remain the canonical, current view.

### At the end of a session

1. Write `./sessions/Session NNN.md` with: rolls made, oracle results, CF shifts, threads opened/closed, NPCs introduced, reasoning behind oracle interpretations.
2. Write `./playervault/Session Log/Session NNN.md` — character journal, first person or close narration. No mechanics, no meta.
3. Confirm `./mythic-state.md` matches the last finished scene (if Mythic active). CF is written at the end of each scene, not here.
4. Update any People/Places/Threads files that changed this session.
5. Update `./playervault/Character.md` for non-stat changes (bonds forged, assets advanced, experience spent). Stats update live during play.
6. Ask the player how much in-fiction time has passed (or infer from narrative); update `**Current date**:` in the `## Basics` block of `./playervault/Character.md` (or at the top of `./playervault/Lore/Calendar.md` if no Character.md exists).

## What goes in the vault

Write what the **character** has seen, done, heard, or been told. Include the character's own speculation — labeled as such. Write in first person or close third.

Do NOT write oracle mechanics, roll results, chaos factor, or GM reasoning in vault files. Those belong in `./sessions/`.

## Linking conventions

Use Obsidian wikilinks in the vault: `[[Kesta Ulfhild]]`, `[[Stonebeck]]`, `[[Find the Sister]]`. Makes the vault navigable in Obsidian.

## Dates

Vault narrative uses **fictional dates only** — the in-fiction calendar string the player has chosen for the campaign (e.g. `Snowmonth 14, Year of the Iron Wolf`, `Day 12 of the journey`, or `4717 AR Sarenith 3`). Format is free-form; maintain continuity from prior writing.

Real-world ISO dates appear only in the `**Played**:` metadata line at the top of session-log files. They never appear in People, Places, Threads, or other narrative content.

**Current date** is stored in the `## Basics` block of `./playervault/Character.md` when a character file exists:

```markdown
**Current date**: Snowmonth 14, Year of the Iron Wolf
```

If the campaign has no `Character.md` (no system skill loaded, or a system that doesn't track a character sheet), store the current date at the top of `./playervault/Lore/Calendar.md` instead. Create that file on first session if needed.

Set the current date during the first session if blank. At session end, ask the player how much in-fiction time has passed (or infer from narrative) and update.

## Filename conventions

- Title case for proper nouns: `Kesta Ulfhild.md`, `The Old Road.md`
- Sequential, three-digit zero-padded filenames for session logs (both `./sessions/` and `./playervault/Session Log/`): `Session 001.md`, `Session 002.md`, …, `Session NNN.md`. Both folders share the number — `./sessions/Session 001.md` and `./playervault/Session Log/Session 001.md` describe the same play session.
- Lower-kebab for top-level mechanical files: `mythic-state.md`

## Example NPC file

`./playervault/People/Kesta Ulfhild.md`:

```markdown
# Kesta Ulfhild

- **Met**: Snowmonth 14, at the smithy in [[Stonebeck]]
- **Appearance**: Older woman in furs, sharpening a blade when we arrived.
- **Demeanor**: Wary but not hostile. Watched our hands more than our faces.

## Known to [character name]

Knew my sister's name before I said it.

## Threads

- [[Find the Sister]]

## Last seen

[[Stonebeck]], morning of [[Session 001]].
```

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
