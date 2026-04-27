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

## Sub-project 3.6: Bootstrap Customization
Make solo-campaign accept campaign-shape choices instead of always copying the same example template.

 - [ ] system <ironsworn|none> flag — which system skill to activate (default: ironsworn)
 - [ ] oracle <mythic|ironsworn-native|none> flag — which oracle layer to wire in (default: mythic)
 - [ ] Multiple example-campaign templates in the toolkit (example-campaign-ironsworn-mythic/, example-campaign-ironsworn-only/, etc.) OR template substitution at bootstrap time
 - [ ] Interactive prompt fallback when flags omitted and stdin is a tty
 - [ ] Update README with example invocations

---

## Sub-project 3.7: Campaign Status Bar
Show character name + live resources in Claude Code's status bar during Ironsworn play.

- [x] `skills/ironsworn/statusline.sh` — reads Character.md callout lines, outputs colored name + HP/SP/SU/MO
- [x] `campaign.py` writes `.claude/settings.json` when ironsworn selected (statusLine command → script)
- [x] Tests: with ironsworn → settings.json written; without → not written
- [ ] Debility badges — append short codes when marked (e.g. `[WND]` `[SHK]`) so active impacts are visible at a glance
- [ ] Active progress track — show current fight or journey tracker inline when one is open (e.g. `⚔ 4/10`)
- [ ] Active vow — show the vow the model judges to be current focus (name-truncated + progress), e.g. `~ Find Cian 0/10`

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

## Sub-project 4.5: Pre-published Adventure Support
Play published adventures with Claude as GM. Requires GM secrets (information the player hasn't read) and a dual-vault structure hidden from the player.

- [ ] Adventure extraction pipeline: PDF → structured markdown (encounter blocks, NPC sheets, location maps)
- [ ] Dual-vault restore: `dm-notes/` with hidden layer, player vault with only revealed content
- [ ] `solo-journaler` skill: dual-vault mode with public/hidden section splits
- [ ] GM secrets management: track what player has discovered vs. what remains hidden
- [ ] `solo-campaign` bootstrap flag: `--mode gm-secrets` creates dual-vault structure
- [ ] Test with one short published module (PF2e Beginner Box or similar OSR adventure)

---

## Sub-project 5: Vault Templates + Progress Track Integration
Formalize the file structure and progress track conventions that emerged during play. Spec: `docs/superpowers/specs/2026-04-26-vault-templates-progress-tracks-design.md`. Plan: `docs/superpowers/plans/2026-04-26-vault-templates-progress-tracks.md`.

- [x] `solo-journaler` SKILL.md: Thread + Location examples added (self-contained-context shape — metadata, What we know / suspect, People / Places, Progression / Visits, Resolution)
- [x] Fictional dates only in vault narrative — ISO ("Played:") restricted to session-log metadata; in-fiction "Current date" stored in `Character.md` (or `Lore/Calendar.md` fallback)
- [x] Sequential session-log filenames: `Session NNN.md` (3-digit pad), shared between `./sessions/` and `./playervault/Session Log/`
- [x] Threads / Places canonical-context rule — synthesis layer, update in place rather than letting context drift to session logs
- [x] Ironsworn skill: vow-vault overlay — instructs agent to write a 10-column progress-track table block to vow Threads on creation; rank → ticks-per-mark mapping (Troublesome 3 / Dangerous 2 / Formidable 1 / Extreme 1-per-2 / Epic 1-per-4)
- [x] Ironsworn `character-template.md`: `Current date` field added to Basics block
- [x] Skill-content test pin (`tests/test_skills_content.py`, 9 assertions) — guards the agent contract against silent breakage
- ~~Starter `_template.md` files in `example-campaign/playervault/`~~ — dropped as YAGNI per spec; SKILL.md examples drive agent behavior, no second source of truth needed
- ~~Mechanical session-log "Oracle reasoning" rename~~ — current SKILL.md wording already uses "oracle reasoning" / "reasoning behind oracle interpretations"; no holdover language remained to drop

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
