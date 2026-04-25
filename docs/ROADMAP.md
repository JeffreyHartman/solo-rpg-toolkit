# Solo RPG GM Assistant — Roadmap

Sub-projects in priority order. Each is self-contained: design → plan → implement → merge.

---

## Sub-project 1: Core RNG + Table Library (`solo-roll` CLI)
- [x] DiceSource protocol + RandomDice + ScriptedDice (`rng.py`)
- [x] JSON table loader + `roll_table` (`tables.py`)
- [x] Convert all `.txt` tables → JSON (49 files: action1/2, descriptor1/2, 45 elements)
- [x] Fate chart math — thresholds, d100 read, classify, random-event detection (`charts.py`)
- [x] Mythic fate chart JSON (`data/charts/mythic-fate.json`)
- [x] `fate_check()` function wired to real RNG
- [x] Quicksets module — loader + runner (`quicksets.py`)
- [x] Per-file quickset JSON (npc_profile, location_profile, creature_profile)
- [x] CLI: `solo-roll table <name>`
- [x] CLI: `solo-roll fate-check --likelihood --cf`
- [x] CLI: `solo-roll meaning-pair`
- [x] CLI: `solo-roll quickset <id>`
- [x] 75 tests, `v0.1.0` tagged, merged to main

---

## Sub-project 2: Mythic GME Skill Rewrite
Wire the existing `skills/mythic-gme/` skill to call `solo-roll` for all dice and table lookups. No more LLM-generated numbers.

- [x] Rewrite `SKILL.md` — instruct agent to invoke `solo-roll` subcommands instead of imagining dice
- [x] Fate check flow: `solo-roll fate-check --likelihood X --cf N` → interpret JSON result
- [x] Meaning pair flow: `solo-roll meaning-pair` → interpret `action` + `description` fields
- [x] Scene test: `solo-roll table` (d10 roll against CF) for altered/interrupted scene
- [x] Random event: `solo-roll fate-check` doubles detection + `solo-roll table elements/plottwist` (or similar) for event focus
- [x] Cross-check `data/charts/mythic-fate.json` values against Mythic 2e PDF
- [x] Populate `event-focus.md` from Mythic 2e book (d100 ranges)
- [x] Populate `meaning-tables.md` if not already done (or confirm fallback path works)
- [x] Update `chaos-factor.md` to reference `dm-notes/mythic-state.md` format
- [ ] Integration test: play a 3-scene session, verify all dice sourced from CLI

---

## Sub-project 3: Campaign Bootstrap Script
One command to scaffold a new campaign folder and install skills.

- [x] Shell/fish script: `new-campaign <name> <path>`
- [x] Copies `example-campaign/` to target path
- [x] Installs skills to `~/.claude/skills/` (idempotent)
- [x] Runs `uv tool install --editable .` for `solo-roll`
- [x] Prompts for `PLAYER_VAULT_PATH` and writes to campaign `CLAUDE.md`
- [x] Creates Obsidian vault folder structure at `PLAYER_VAULT_PATH`
- [x] Prints "ready — run `claude` in `<path>`"
- [x] Works on Linux/macOS; documents Windows PowerShell equivalent in README

---

## Sub-project 3.5: Datasworn Ingestion (Ironsworn Truths)
First feature in a multi-step ingestion of the `@datasworn/ironsworn-classic` JSON dataset (`reference/datasworn-ironsworn-classic/`, CC-BY-4.0). Future features (oracles, moves, assets) are separate specs.

- [x] Reusable converter `scripts/datasworn_to_truths.py` (pure stdlib, pytest-tested)
- [x] Generated `skills/ironsworn-truths/truths.md` reference file
- [x] New skill `skills/ironsworn-truths/SKILL.md` — multi-turn truth-locking workflow
- [x] Soft hook from `skills/ironsworn/SKILL.md` ("truths not locked — want to set them up?")
- [x] Spec: `docs/superpowers/specs/2026-04-24-ironsworn-truths-skill-design.md`
- [x] Plan: `docs/superpowers/plans/2026-04-25-ironsworn-truths-skill.md`

---

## Sub-project 4: PDF → Markdown Pipeline
Extract published adventure path content from PDF into structured markdown the agent can run from.

- [ ] Design extraction schema: scenes, NPCs, locations, encounters, secrets
- [ ] Script to convert PDF → raw markdown (via `pdftotext` or `pymupdf`)
- [ ] Agent post-processing prompt: clean raw markdown → structured scene files
- [ ] Output format: `adventure/<slug>/scenes/`, `npcs/`, `locations/`, `items/`
- [ ] New skill: `adventure-runner` — reads scene files, runs encounters, tracks progress
- [ ] `adventure-runner` skill knows to call Ironsworn moves for resolution
- [ ] Integration: Mythic scene tests still fire on top of scripted scenes
- [ ] Test with one short published module (PF2e or OSR)

---

## Sub-project 5: Enhanced Journaling + Obsidian Vault
Improve the solo-journaler skill and the player-facing vault structure.

- [ ] Pre-built Obsidian vault template (folders, index file, CSS snippets)
- [ ] Session log auto-format: Obsidian-friendly headers, wikilinks, callout blocks
- [ ] NPC file template with fields: met/location/demeanor/hidden-truth split
- [ ] Location file template
- [ ] Thread/vow tracker: syncs with Ironsworn progress tracks
- [ ] End-of-session summary command: agent writes both logs in one pass
- [ ] `solo-journaler` skill rewrite: clearer write/don't-write rules, example outputs

---

## Sub-project 6: Additional Systems + Skills
Expand beyond Ironsworn.

- [ ] `une-npc-generator` skill — Universal NPC Emulator
- [ ] `pf2e-adventure-runner` skill — run PF2e APs from converted markdown
- [ ] `golarion-world` skill — Pathfinder setting reference
- [ ] `hex-crawl` skill — generate + track hex exploration
- [ ] `dungeon-stocker` skill — classic 1d6 dungeon contents
- [ ] `westmarches-tracker` skill — shared-world bookkeeping for pseudo-group solo play
- [ ] Additional quicksets: encounter_profile, faction_profile, rumor_table
- [ ] Additional element tables extracted from other system PDFs

---

## Sub-project 7: Distribution
Make it easy to hand this to someone else.

- [ ] `npm`-style install script (or fish/bash) that sets up everything from zero
- [ ] Published GitHub repo with README covering full setup
- [ ] Versioned skill releases (zip each skill dir, tag)
- [ ] `solo-roll` PyPI publish or pipx-from-git instructions
- [ ] Example campaign folder with a complete played session log included
