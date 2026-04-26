# Vault Consolidation Design

**Date:** 2026-04-26  
**Status:** Approved  
**Scope:** Collapse dual-vault (dm-notes + external player vault) into single `playervault/` inside campaign directory

---

## Problem

Current campaign structure has two note locations:
- `dm-notes/` inside campaign dir — mechanical state, GM secrets, NPC full truth
- External Obsidian vault in separate directory — narrative, player-facing content

This causes duplication: NPCs, locations, and threads each have two files. The split made sense for pre-published adventures (GM secrets) but Ironsworn and Mythic are discover-as-you-play — there are no meaningful GM secrets. The external vault path is an absolute reference in `CLAUDE.md`, breaking self-containment.

---

## Design

### Approach: Thin root layer

Campaign root holds only machine/operational files. `playervault/` subfolder holds all narrative content and serves as the Obsidian vault.

**What lives at campaign root:**
- `CLAUDE.md` — config, session procedures, skill list
- `.claude/` — settings, skill symlinks
- `mythic-state.md` — chaos factor + live thread/character tracking (only if `mythic-gme` skill active)
- `sessions/` — mechanical session logs (rolls, CF shifts, oracle reasoning)

**What lives in `playervault/`:**
- `Character.md` — character sheet, stats, assets, vows, bonds
- `Session Log/` — narrative session journals (character voice)
- `People/` — NPCs (what character knows/observed)
- `Places/` — locations (what character has visited/been told)
- `Threads/` — active vows and mysteries (character's understanding)
- `Lore/Truths/` — setting worldbuilding (Ironsworn truths, etc.)
- `.obsidian/` — Obsidian app config

---

## Folder Structure

```
campaign-name/
├── CLAUDE.md
├── .claude/
│   ├── settings.json
│   └── skills/                  # symlinks to toolkit skills
├── mythic-state.md              # only present if mythic-gme skill installed
├── sessions/
│   └── YYYY-MM-DD.md
└── playervault/
    ├── .obsidian/
    ├── Character.md
    ├── Session Log/
    │   └── YYYY-MM-DD.md
    ├── People/
    ├── Places/
    ├── Threads/
    └── Lore/
        └── Truths/
```

---

## Component Changes

### `solo-journaler` skill

Full rewrite. Current skill encodes split rules: what goes to `dm-notes/` vs player vault. New version has no split — single vault at `./playervault/`. Rules:

- Narrative content (character experience, NPC interactions, discoveries) → `playervault/`
- Mechanical state (CF, oracle results, roll reasoning) → root files (`mythic-state.md`, `sessions/`)
- No duplication of entity files

### `example-campaign/` template

- Remove `dm-notes/` directory tree entirely
- Add `playervault/` with `.obsidian/` config and empty subdirs (People, Places, Threads, Session Log, Lore/Truths)
- Add `sessions/` at campaign root with `README.md`
- Keep `mythic-state.md` at root (conditional on skill)

### `CLAUDE.md` template

- Remove `PLAYER_VAULT_PATH` absolute-path config var
- Reference vault as `./playervault/` (relative, self-contained)
- Update session start/end procedures to new paths

### `solo-campaign` bootstrap (`campaign.py`)

- Stop creating external vault directory
- Create `playervault/` inside campaign dir with `.obsidian/` config
- `mythic-state.md` only created when `mythic-gme` is in the selected skills list (oracle flag mechanism deferred to sub-project 3.6 — for now, presence of skill in bootstrap selection drives this)

### ROADMAP

Add sub-project 4.5: **Pre-published adventure support**
- GM secrets and dual-vault (DM notes hidden from player)
- Adventure PDF extraction pipeline
- Playing published adventures with Claude as GM

This is the deferred motivation for the dual-vault complexity removed in this sub-project.

---

## Migration: `ironsworn-test1`

One-time migration of the existing test campaign:

1. Copy `/home/jeff/rgp/claude/ironsworn-test1-playervault/` → `ironsworn-test1/playervault/`
2. Move `dm-notes/mythic-state.md` → `ironsworn-test1/mythic-state.md`
3. Move `dm-notes/sessions/` → `ironsworn-test1/sessions/`
4. For each entity type (NPCs, locations, threads):
   - Player vault version is canonical — keep it
   - If DM file has non-secret flavor not in player file, fold it in
   - DM file discarded after merge
5. Delete `dm-notes/` entirely
6. Update `CLAUDE.md` vault path to `./playervault/`
7. Delete old vault at `/home/jeff/rgp/claude/ironsworn-test1-playervault/`

---

## Deferred: GM Secrets

Dual-vault with hidden DM layer is deferred to sub-project 4.5. Applies when running pre-published adventures where Claude GMs from extracted adventure content the player hasn't read. Not needed for discover-as-you-play systems (Ironsworn, Mythic).

---

## Success Criteria

- New campaign bootstrapped by `solo-campaign` has `playervault/` inside campaign dir, no external vault
- `solo-journaler` skill works with single vault — no split-write logic
- `mythic-state.md` absent from campaigns without `mythic-gme` skill
- `ironsworn-test1` migrated: one file per NPC/location/thread, no duplication
- `CLAUDE.md` references vault with relative path `./playervault/`
