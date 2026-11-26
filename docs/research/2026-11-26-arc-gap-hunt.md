# Arc gap hunt: the full campaign arc against the v0.7.0 harness

Date: 2026-11-26. Ticket: #26 (child of map #25).

Question: for each step of the "fully playable" arc, what does the harness lack today?

## Sources

- Harness code at tag `v0.7.0`: `src/solo_roll/harness/` (engine, registry, OSE and FlexTale plugins, Referee tools, server) and `web/src/`.
- ADR 0001, ADR 0002, and ADR 0003 (player controls the character, Referee controls the world; not yet committed).
- Playtest notes: `docs/playtests/2026-11-26-first-delve.md`.
- Local OSE rules markdown in `templates/ose/rules/` (gitignored). It has six files: character creation and gear, the bard class, combat, the dungeon turn, encounters, and druid spells of level 1.
- FlexTale Solo Adventuring Toolkit (SAT) PDF, the Campaign Generator PDF (DCG), and the structure of three spreadsheets: Trackers, Campaign Generator Table Matrix, and Hexcrawl Generator Table Matrix. This note uses section names, sheet names, column headers, and page numbers only.
- Imported FlexTale tables in `~/.local/share/solo-rpg-toolkit/flextale/tables/quickstart/`.

## How to read the tables

- **Kind**: procedure, engine state, direct action, UI, Referee tool, or data.
- **Issue**: an open issue that covers the gap. A dash means a new gap.
- **Phase**: the suggested phase of the working draft. 1 Solid ground, 2 The table, 3 The full arc, 4 Modules, 5 Later.
- **Evidence**: a file and line at `v0.7.0`, or a book section and page.
- "Direct action" follows ADR 0003: the player changes their own party through the engine, and no Referee turn runs.

## Step 1: make a character, roll starting gold, buy gear

What works: the `create_character` procedure rolls 3d6 in order for a class, rolls the hit die, and adds the character to the party. The web form asks for class, name, and description.

| # | Gap | Kind | Issue | Phase | Evidence |
|---|-----|------|-------|-------|----------|
| 1.1 | The player picks the class before the roll. OSE rolls the scores first and then picks a class. When the roll does not meet the class minimums, the engine refuses the command and changes nothing, so the player can roll again until a roll passes. | procedure | - | 3 | `harness/plugins/ose/character.py:46` |
| 1.2 | The player cannot bring an existing character. No form, no import, and no procedure accepts given scores, HP, class, and level. | direct action | - | 3 | `web/src/lib/CharacterCreation.svelte:26`; `harness/referee/tools.py` (only `create_character`) |
| 1.3 | The character record has no XP, gold, gear, weapon, armor, alignment, or languages. AC is always the unarmored value. | engine state | #20 (gold, gear) | 3 | `harness/plugins/ose/character.py:16-26`, `:58` |
| 1.4 | No procedure rolls starting gold, and no shop step buys gear from the ruleset list. | procedure | #20 | 3 | `templates/ose/rules/character-creation.md`, section "Adventuring gear" (prices exist, no procedure) |
| 1.5 | The local rules markdown has adventuring gear only. It has no weapon list, armor list, weapon damage, or armor AC values. Shopping and AC need that data. | data | - | 3 | `templates/ose/rules/character-creation.md` (section headings) |
| 1.6 | Caster classes have no spells: no spell list, no prepared spells, no spell slots. The local rules have only the bard and druid level 1 spells. | engine state | - | 3 | `templates/ose/rules/`; `harness/plugins/ose/character.py:16-26` |
| 1.7 | The player cannot edit their own sheet (name, description, a corrected score) as a direct action. | direct action | - | 2 | ADR 0003 |
| 1.8 | The web app hard-codes the OSE class list. The ruleset plugin does not supply it. | UI | - | 2 | `web/src/lib/socket.svelte.ts:171` |

## Step 2: start in a settlement with a reason to go somewhere

What works: the Referee can write NPC, place, and thread records freely in the vault.

| # | Gap | Kind | Issue | Phase | Evidence |
|---|-----|------|-------|-------|----------|
| 2.1 | A new campaign starts in an anonymous "Entrance" area with four generator exits. | engine state | #20 (start from a place) | 3 | `harness/library.py:50-54` |
| 2.2 | The harness has no settlement mode. Every move takes a dungeon turn, burns the torch, and can trigger a wandering check, also in a town. | engine state | - | 3 | `harness/plugins/ose/__init__.py:41`, `:50`; `harness/plugins/ose/dungeon_turn.py:65` |
| 2.3 | No procedure makes a hook: where the party begins, who gives the job, what the job is. The Campaign Generator has these tables, but the importer reads only the SAT Quick Start pages. | data | - | 3 | DCG, Quest Generators: Where You Begin p54, Quest-Giver p55, Quest Hooks p57, Quest Type p60 |
| 2.4 | The engine has no quest state: goal, giver, reward, status. A record can hold the story. The reward and the completion are mechanical, so the engine must own them (ADR 0001). | engine state | - | 3 | SAT, Quest Tracking p136 and Milestones p137; Trackers spreadsheet, "Quest Tracker" sheet |
| 2.5 | The harness has no town services: a shop with stock and prices, a temple, an inn. | procedure | #20 (shop) | 3 | `harness/plugins/` (no such procedure) |
| 2.6 | The Referee has no tool to put a world fact into engine state: a new place, an NPC in an area, shop stock. Its tools are `state`, `propose`, `judgment_call`, `move`, `create_character`, and `end_session`. ADR 0003 gives the world to the Referee, but the engine gives it no world tools. | Referee tool | - | 3 | `harness/referee/tools.py:104-170` |
| 2.7 | No settlement generator data is imported. | data | - | 3 | SAT, Generators & Tools: Settlement Size p491; DCG, Settlement p148 |

## Step 3: travel to a site (one procedure, no overworld map)

What works: nothing for this step. The engine knows one map and moves the party between connected areas of it.

| # | Gap | Kind | Issue | Phase | Evidence |
|---|-----|------|-------|-------|----------|
| 3.1 | A campaign holds one map. The engine has no idea of a site: a settlement and a dungeon cannot each have their own map, explored state, and party position. | engine state | - | 3 | `harness/campaign.py:100-105` |
| 3.2 | No travel procedure exists: pick a destination, roll the distance and days, use rations, check for encounters, arrive. | procedure | - | 3 | SAT, Rough Distance p491 and Travel Pace p506; DCG, Overland Distance p129 |
| 3.3 | The engine has a dungeon turn clock only. It has no day clock for travel, healing, or time in town. | engine state | - | 3 | `harness/plugins/ose/dungeon_turn.py:31-41` |
| 3.4 | The local rules markdown has no wilderness travel rules: daily movement, getting lost, foraging, wilderness encounter checks. | data | - | 3 | `templates/ose/rules/` (six files, none on wilderness) |
| 3.5 | No travel encounter or weather tables are imported. | data | - | 3 | SAT, Environment Encounter Tables appendix p532-563; DCG, Overland Generators p133-145 |
| 3.6 | Rations and other consumables are not engine state. | engine state | #20 | 3 | `harness/plugins/flextale/treasure.py:25-26` (inventory has coins, gems, items only) |
| 3.7 | No UI shows travel: the known destinations, the days on the road, and the travel events. | UI | - | 3 | `web/src/App.svelte` (map and actions only) |

## Step 4: delve with real inventory, light, encumbrance, and combat

What works: the FlexTale map generator, area encounters, traps and obstacles with a DC check, treasure rolls, OSE search and listen, the torch clock, wandering checks, and narrative combat with side initiative, melee attacks, and the Simple AI for monsters.

| # | Gap | Kind | Issue | Phase | Evidence |
|---|-----|------|-------|-------|----------|
| 4.1 | The party gets one torch. No spare light exists, and no procedure lights a torch or fills a lantern. | procedure | #20 | 3 | `harness/plugins/ose/dungeon_turn.py:38`; playtest notes |
| 4.2 | The engine does not track encumbrance or movement rate. | engine state | #20 | 3 | `templates/ose/rules/dungeon-turn.md`, "Basic encumbrance movement rates" |
| 4.3 | The inventory is one pool for the party, and the FlexTale generator owns it. No character carries gear, and no direct action moves gear between characters. | engine state | #20 | 3 | `harness/plugins/flextale/treasure.py:3`, `:30` |
| 4.4 | The web app does not show the inventory. Only `State.md` in the vault shows it. | UI | #20, #16 | 2 | `harness/vault.py:91`; no `inventory` in `web/src/` |
| 4.5 | The combat code does not match the campaign's rules text. The rules markdown says the campaign uses ascending AC and variable weapon damage. The engine uses THAC0 against descending AC and a 1d6 default for every character. | procedure | - | 1 | `templates/ose/rules/combat.md:44`, `:63`; `harness/plugins/ose/combat.py:182`, `:206-211` |
| 4.6 | Combat has melee attacks only. It has no missile attacks, no spells, no morale checks, and no flee or pursuit for the party. | procedure | - | 3 | `harness/plugins/ose/combat.py:167`; `templates/ose/rules/encounters.md:72`, `:99` |
| 4.7 | The bestiary has five monsters. Every other result gets a generic stat block. No entry has an XP value or a morale score. | data | - | 3 | `templates/ose/data/bestiary.json`; `harness/plugins/ose/combat.py:29` |
| 4.8 | A character at 0 HP stays in the party with no rule for death, dying, or recovery of the body and gear. | procedure | - | 3 | `harness/party.py:17` |
| 4.9 | The player cannot roll their own check. Ability checks and saving throws exist, but no button starts them; only a Referee proposal does. | direct action | - | 2 | `harness/plugins/ose/checks.py:18-38`; `web/src/App.svelte:61-62` |
| 4.10 | Every click that changes state starts a Referee turn. ADR 0003 says a direct action takes no Referee turn, and the Referee reads a log of direct actions at its next turn. No such log or split exists. | engine state | - | 2 | `harness/server.py:174` |
| 4.11 | The party cannot leave the site. No action ends the delve or resets the dungeon clock and light state. | procedure | - | 3 | `harness/plugins/ose/dungeon_turn.py:31-41` |
| 4.12 | The map does not make closed exits clear. The Referee described an arch that the player did not see. | UI | #3 | 2 | playtest notes, "the map" |
| 4.13 | Some imported tables have wrong ranges, and `treasure-b` is missing from the import. | data | #19 | 1 | `~/.local/share/solo-rpg-toolkit/flextale/tables/quickstart/` |
| 4.14 | Rule sources come only from the table `source` field. Code-built cards have no page, and citations do not open the rules text. | UI | #22 | 2 | playtest notes, "Answers found while triaging" |

## Step 5: go back to town, sell treasure, heal, gain XP, level up

What works: treasure adds coins, gems, and items to the inventory.

| # | Gap | Kind | Issue | Phase | Evidence |
|---|-----|------|-------|-------|----------|
| 5.1 | Gems and items have no value. A gem keeps a name and a count, and an item keeps a name. Selling needs a value. | engine state | - | 3 | `harness/plugins/flextale/treasure.py:146`, `:152` |
| 5.2 | No procedure sells treasure or trades gear. | procedure | #20 (buy side) | 3 | `harness/plugins/` (no such procedure) |
| 5.3 | No healing exists. Rest takes one dungeon turn and gives no HP back. No day-based rest and no paid healing exist. | procedure | - | 3 | `harness/plugins/ose/dungeon_turn.py:61` |
| 5.4 | Characters have no XP. Monsters give no XP, recovered treasure gives no XP, and the class prime requisite does not change XP. | engine state | - | 3 | `harness/plugins/ose/character.py:16-26`; `templates/ose/data/bestiary.json` |
| 5.5 | The XP model is not decided: OSE XP for monsters and treasure, or FlexTale Reward Stars that convert to XP between adventures. The Reward Star conversion sheet has columns for Pathfinder, 5E, DCC, and Pathfinder 2E, and no OSR column. | procedure | - | 3 | SAT, Experience Points and Reward Stars p17-19; Trackers spreadsheet, "Reward Star XP Conversion" sheet |
| 5.6 | No level-up procedure exists. The engine has no class progression data (XP thresholds, hit dice, saves, attack values, spells) except the bard table in the local rules. Saves are fixed at level 1. | data | - | 3 | `src/solo_roll/character.py:20`; `templates/ose/rules/class-bard.md:69` |
| 5.7 | The Referee has no tool to grant a quest reward (coins, an item, Reward Stars) or to close a quest. | Referee tool | - | 3 | `harness/referee/tools.py:104-170` |
| 5.8 | No between-adventures step exists for XP conversion, upkeep, training, or other downtime. | procedure | - | 3 | SAT, Converting Reward Stars to XP p18; Experience & Leveling p99-100 |

## Step 6: end the session and start the next one from saved state

What works: `engine/state.json` holds all mechanical state and reloads when the campaign opens. End session has the Referee write the session note and update records, and the next Referee conversation starts from the vault and the state.

| # | Gap | Kind | Issue | Phase | Evidence |
|---|-----|------|-------|-------|----------|
| 6.1 | The next session opens silently. The Referee reads the vault and gives a recap only after the player types the first message. | Referee tool | - | 2 | `harness/server.py:310-317`; `harness/referee/base.py:95-107` |
| 6.2 | The direct-action log of ADR 0003 must cross the session boundary, so that the Referee sees changes the player made between sessions (for example, shopping or sheet edits). | engine state | - | 2 | ADR 0003 |
| 6.3 | The dungeon clock, light, and encounter state carry over with no site context. With more than one site, each site needs its own saved state: explored areas, cleared rooms, and time since the last visit. | engine state | - | 3 | `harness/plugins/ose/__init__.py:41`; `harness/plugins/flextale/__init__.py:44` |
| 6.4 | Only the Referee can close a session. When the write-up turn fails, for example at a plan limit, the session stays open, and the player cannot close it without the Referee. | procedure | - | 1 | `harness/server.py:286-305` |

## Gap count

| Step | New gaps | Gaps on existing issues | Total |
|------|----------|-------------------------|-------|
| 1 Character, gold, gear | 6 | 2 (#20) | 8 |
| 2 Settlement and hook | 5 | 2 (#20) | 7 |
| 3 Travel | 6 | 1 (#20) | 7 |
| 4 Delve | 7 | 7 (#20, #16, #3, #19, #22) | 14 |
| 5 Town, XP, levels | 7 | 1 (#20) | 8 |
| 6 Sessions | 4 | 0 | 4 |
| All | 35 | 13 | 48 |

#17 (smoke test), #21 (GM voice), #23 (headless screenshots), and #24 (usability research) do not close one arc gap. They make the gaps above cheaper to find and test.

## Surprises

1. **The server already breaks ADR 0003.** Every click that changes state starts a Referee turn (`harness/server.py:174`). The split between a direct action and a Referee turn is not only phase 2 UI. It changes the server, the engine log, and the Referee prompt. Phase 2 must start with it, or phase 1 takes it.
2. **The combat code does not follow the campaign's own rules text** (gap 4.5). The rules markdown picks ascending AC and variable weapon damage, and the engine does neither. This is a phase 1 fix, because every later combat and gear change builds on it.
3. **The inventory belongs to a generator.** The FlexTale plugin owns `state["inventory"]` (`treasure.py:30`). An OSE campaign with no FlexTale has no inventory, and the inventory is one pool for the party. Inventory must move to the engine or the ruleset before #20 can work. This also touches the plugin bar (#28).
4. **"Site" is an engine-state change, not a phase 3 detail.** One map per campaign and an always-on dungeon clock block the settlement, travel, and return steps (gaps 2.2, 3.1, 3.3, 6.3). A site model is also the seam for modules (phase 4) and the hexcrawl (phase 5). Design it at the start of phase 3, or split it into its own phase.
5. **The XP model needs a decision before code.** The FlexTale Reward Star conversion has no OSR column, and OSE gives XP for treasure. Pick the model with a grilling ticket and an ADR before the level-up work.
6. **The arc needs more source data than the repo has.** The local OSE markdown covers six topics, and the FlexTale import covers only the SAT Quick Start pages. The arc also needs weapons and armor, starting gold, wilderness travel, healing, class progression for every class, spells, hook and quest tables, settlement tables, and travel encounter tables. This data work comes before most of phase 3 and can be its own phase.
7. **The spreadsheet matrices change the import question.** The map puts Excel import out of scope because the bundle has no spreadsheet of the Quick Start tables. The Campaign Generator and Hexcrawl Generator tables do exist as spreadsheets. For the hook, settlement, and travel tables, a spreadsheet import is possibly cheaper than PDF extraction. Decide this when phase 3 is charted.
8. **ADR 0003 does not say who owns a trade.** Buying, selling, and paid healing change the player's own party, but the shop stock and the prices are world. The ADR needs one more line on trades before the shop design starts.
9. **The class check lets the player roll again for free** (gap 1.1). This is a rules fidelity bug in shipped code, so it fits phase 1.
