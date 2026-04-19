---
name: solo-journaler
description: Use during any solo RPG session to maintain persistent notes across two locations — a player-facing Obsidian vault (what the character knows and has experienced) and a separate DM-notes folder in the campaign directory (what the GM knows but the player does not). Activates whenever new information is introduced in a session — NPCs met, locations visited, vows made, threads opened, secrets revealed, or at the end of a scene when the session log needs updating.
---

# Solo Journaler Skill

This skill keeps the *player's canon* and the *GM's secrets* separate so solo play doesn't collapse into omniscience. You (the agent) know things the character doesn't. That knowledge belongs in `dm-notes/`. The player's Obsidian vault gets only things the character has experienced or been told.

## Vault configuration

The campaign's `CLAUDE.md` declares a `PLAYER_VAULT_PATH`. Read it at session start:

```
PLAYER_VAULT_PATH: /home/user/Obsidian/MyVault/Ironsworn Campaign
```

If it's missing or the path doesn't exist, ask the player to set it before writing anything player-facing.

## The split

### Player vault (only things the character knows)

Goes in `$PLAYER_VAULT_PATH/`. Structure:

```
<player vault>/
├── Character.md            # current character sheet state
├── Session Log/            # one file per session, dated
│   └── 2026-04-19.md
├── People/                 # NPCs the character has met
│   └── Aland the Smith.md
├── Places/                 # places the character has been or been told of
│   └── Stonebeck.md
├── Threads/                # active vows, promises, mysteries the character is aware of
│   └── Find my sister.md
└── Lore/                   # worldbuilding the character has learned
    └── The Old Road.md
```

**What goes here**: anything the character has seen, done, heard, been told, or reasonably knows. Write in first person or close-third — this is the player's own journal. Include speculation the character is making, but label it as speculation.

**What does NOT go here**: any fact the player doesn't know yet. No "Aland is secretly a cultist" unless the character has seen evidence. No "the treasure is actually cursed" unless it's been revealed. No chaos factor, no random event mechanics, no spoilers.

### DM notes (everything else)

Goes in `dm-notes/` at the campaign root. Structure:

```
<campaign root>/
└── dm-notes/
    ├── mythic-state.md         # CF, scene tracker, threads list, characters list
    ├── npcs/
    │   └── Aland the Smith.md   # full truth about the NPC
    ├── locations/
    │   └── Stonebeck.md         # hidden features, factions, etc.
    ├── threads/
    │   └── The Sister's Trail.md # both what's known and what's hidden
    └── sessions/
        └── 2026-04-19.md        # GM-side session log with rolls, reasoning, plans
```

**What goes here**: everything — including what's in the player vault. DM notes are a superset. Put the whole truth about each NPC, the chaos factor log, the reasoning behind oracle interpretations, tentative ideas for where plot threads might go, and anything the player hasn't earned yet through play.

## Writing rules

### At the start of a session
1. Read the most recent session log from both `dm-notes/sessions/` and the player vault's `Session Log/`.
2. Read `dm-notes/mythic-state.md` to restore Chaos Factor and active threads.
3. Briefly recap for the player: "Last session you ended at X with Y unresolved."

### During the session
- When the player meets a new NPC: create the NPC file in *both* vaults (player-facing version has only what was observed; DM version has the full truth).
- When an oracle roll reveals a secret to the player: update the player vault file to include the revelation; update the DM file to record when it was revealed.
- When an oracle roll reveals something *only the agent* now knows: update only the DM file.
- Keep a running "this session" note in `dm-notes/sessions/YYYY-MM-DD.md` as a scratchpad.

### At the end of a session
1. Finalize `dm-notes/sessions/YYYY-MM-DD.md` with: rolls made, key decisions, chaos factor shifts, threads opened/closed, NPCs introduced.
2. Write the parallel player-facing entry in `<player vault>/Session Log/YYYY-MM-DD.md` — this is the character's journal. Use their voice if known; otherwise close narration. Omit mechanics.
3. Update Chaos Factor in `dm-notes/mythic-state.md` if Mythic is loaded.
4. Update any NPC / location / thread files that changed.

## Linking conventions

In the player vault, use Obsidian wikilinks: `[[Aland the Smith]]`, `[[Stonebeck]]`. This makes the vault navigable in Obsidian for the player to browse between sessions.

In DM notes, use relative paths or wikilinks — whatever is consistent within the campaign.

## Filename conventions

- Use title case for proper nouns: `Aland the Smith.md`, `The Old Road.md`
- Use ISO date for session logs: `2026-04-19.md`
- Lower-kebab-case is fine for DM-side concept files that aren't proper nouns: `mythic-state.md`

## What about mid-session note operations?

When introducing something that deserves a file, do it inline — briefly tell the player you're jotting it down, then continue:

> *"An older woman in furs looks up from her whetstone as you enter. Rolling name oracle… Kesta Ulfhild. Adding her to your People folder."*

Don't pause for five minutes to perfectly author files. Minimal skeleton during play, flesh out at session end.

## Example minimal NPC file at first meeting

**Player vault** (`People/Kesta Ulfhild.md`):
```markdown
# Kesta Ulfhild
- **Met**: 2026-04-19, at the smithy in [[Stonebeck]]
- **Appearance**: Older woman in furs, sharpening a blade when we arrived.
- **Demeanor**: Wary but not hostile. Watched our hands more than our faces.
- **Notes**: She knew my sister's name before I said it.
```

**DM notes** (`npcs/Kesta Ulfhild.md`):
```markdown
# Kesta Ulfhild
## Public (in player vault)
- Older woman, smith in Stonebeck
- Knew the sister's name unprompted

## Hidden
- She was part of the raiding party seven years ago that took the sister. She's been waiting for someone to come looking.
- Has a broken iron token matching the one the PC carries.
- Chaos: if pushed to reveal, she will lie first and test the PC's response.

## Rolls that produced her
- Name: Ironsworn name oracle → Kesta Ulfhild
- Personality: Action/Theme → Preserve/Secret
- Fate check "does she know about the sister?": Likely, CF 5, rolled 12 → Yes
```

Keep them linked by name. The contract is: whenever the player-facing file gains info, check the DM file to see what's now revealed vs. still hidden and update accordingly.
