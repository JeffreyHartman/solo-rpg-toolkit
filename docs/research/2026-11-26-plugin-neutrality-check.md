# Plugin neutrality check: a new ruleset, a new generator, and a mix

Date: 2026-11-26. Ticket: #28 (child of map #25).

Question: where does OSE or FlexTale leak into the engine, the plugin interface, the Referee tools, the web app, or the arc steps of the gap hunt (#26)?

## Sources

- Harness code on `main` at `fcfbdea`. File references are relative to `src/solo_roll/harness/` or `web/src/`.
- `GLOSSARY.md`, ADR 0001 (engine owns state), ADR 0003 (player controls the character, Referee controls the world).
- Gap hunt note: `docs/research/2026-11-26-arc-gap-hunt.md` on `research/arc-gap-hunt`.
- Ironsworn: `skills/ironsworn/` and the Datasworn Ironsworn Classic dataset (CC-BY-4.0).
- Mythic GME: `skills/mythic-gme/`, `src/solo_roll/charts.py`, `data/charts/mythic-fate.json`.
- This note names mechanics only. It has no book text.

## Summary

The core of the interface is neutral. Procedures, confirm levels, proposals, judgment calls, settings, state defaults, Referee guides, and mechanics cards work for all three cases. A Mythic GME plugin fits today with no engine change: a `mythic` state default for the chaos factor, procedures for the fate check, the scene test, and the scene end, and a judgment category for the chaos factor change. Ironsworn weak-hit costs and momentum burns fit as judgment calls.

The leaks are at the edges. OSE and FlexTale talk through an undocumented event contract. Shared state (inventory, time, map movement) belongs to whichever plugin came first. No rule decides between two plugins that answer one event. The web app, the state note, and two Referee tools read OSE field names. The plugin list is hard-coded.

The check found 17 leaks. No case in phases 1 to 4 tests the plugin bar, because every planned campaign is OSE with FlexTale.

## Leaks

Cases: 1 Ironsworn ruleset, 2 Mythic GME generator, 3 OSE with FlexTale and Mythic GME.

| # | Leak | Where | Case | What the engine or interface needs | Phase impact |
|---|------|-------|------|------------------------------------|--------------|
| L1 | The shipped plugin list is a fixed dict with fixed data paths. A new plugin needs a code change in the toolkit. | `plugins/__init__.py:11-16`; `cli.py:114-115` | 1, 2 | Plugin discovery (package entry points or a plugin folder) and a factory that gets a data root. | Must come before phase 4 (each module is a plugin) |
| L2 | The FlexTale generator gets its ruleset as a constructor argument (`"osr"`). The campaign never sets it. | `plugins/flextale/__init__.py:122` | 1, 3 | The registry tells each plugin the campaign's ruleset. | Belongs in phase 5 |
| L3 | The FlexTale trap check reads OSE ability names and OSE saves from the character. | `plugins/flextale/checks.py:71`, `:104-109` | 1 | A ruleset seam: a generator raises a challenge with a difficulty, and the ruleset picks its own roll (an OSE check, an Ironsworn Face Danger). | Belongs in phase 3 (travel hazards reuse it) |
| L4 | OSE combat and the FlexTale Simple AI share events that no document names (`combat_encounter`, `monster_turn`, `monster_decision`). With OSE alone, no plugin answers `monster_turn`, so monsters never act. Two AI plugins make each monster act twice. | `plugins/ose/combat.py:50`, `:138`; `plugins/flextale/simple_ai.py:31`; `plugins/flextale/encounters.py:125` | 1, 2, 3 | A documented event vocabulary, and a "one responder" rule for events that need exactly one answer. | Must come before phase 3 (morale, missiles, and flee extend this contract) |
| L5 | Two plugins that register the same procedure, command, state key, or judgment category stop the campaign from opening. | `registry.py:123-124`, `:146-147`, `:173-174`, `:187-188` | 3 | A name rule per plugin (for example `mythic.fate_check`), or a campaign choice of provider. | Belongs in phase 3 (set the rule before phase 3 adds procedures) |
| L6 | Every trigger for an event runs, in plugin order, and the first target source wins. On a rest turn, the OSE wandering check and the FlexTale rest encounter both roll. | `engine.py:328-329`; `registry.py:154-161`; `plugins/ose/dungeon_turn.py:70-74`; `plugins/flextale/encounters.py:89-94` | 3 | A campaign setting that names the plugin that answers each kind of question: encounters, area content, monster actions. | Belongs in phase 3 (travel encounters, gap 3.5) |
| L7 | The FlexTale generator owns the inventory, with a gp, gems, and items shape. The state note prints "gp". Ironsworn has no gold. | `plugins/flextale/treasure.py:25-30`; `vault.py:91-92` | 1, 3 | Engine-owned item records (name, count, value, carrier) with a ruleset currency. Generators add items through an engine command. | Must come before phase 3 (#20) |
| L8 | The only clock is the OSE dungeon turn. FlexTale counts backtracks on its own. Mythic counts scenes, and the engine has no scene. | `plugins/ose/dungeon_turn.py:31-41`; `plugins/flextale/encounters.py:81`; `engine.py:339-352` | 1, 2, 3 | Engine time with plugin units (turn, day, scene), clocks per site, and clock events for triggers. | Must come before phase 3 (with the site model) |
| L9 | The engine creates the map, but the OSE ruleset owns the `move` command. The Referee `move` tool calls it. Every generator gets four open exits, also one that makes no map. | `plugins/ose/__init__.py:36`, `:55-78`; `referee/tools.py:43-45`; `library.py:24-27`, `:83`; `campaign.py:100-105` | 1, 2 | An engine-owned move on the map (the ADR 0003 token move). The ruleset adds the cost with a trigger on `moved`. A generator declares that it makes maps. | Must come before phase 2 (token move is a direct action) |
| L10 | The Referee tool list is fixed, and `create_character` has the OSE inputs (class, name, description). | `referee/tools.py:86-88`, `:149-158` | 1 | Build the tool from the ruleset's creation procedure inputs, or let plugins add engine tools. | Belongs in phase 3 (creation and import) |
| L11 | A target is one integer. The Ironsworn action roll has an action die plus a stat against two challenge dice, three outcomes, and a match. The Mythic fate check has four outcome bands and a random event on doubles. | `registry.py:60-61`; `proposals.py:107-144`; `lib/protocol.ts:58-62` | 1, 2 | An outcome model: the target is optional, and the result bands are data on the card. Procedures with `target=False` work today. | Belongs in phase 2 (card design, #22) |
| L12 | The engine has no track. Ironsworn needs health, spirit, supply, momentum, and progress tracks with a rank. Mythic needs the chaos factor. | `plugins/ose/character.py:16-26` (schema types: string, integer, object) | 1, 2 | A track type in engine state (name, min, max, value, owner) that the web and the state note show with no plugin code. | Belongs in phase 2 (sheet UI) |
| L13 | The web app shows OSE fields by name and ignores `character_schema`. The class list is hard-coded. The combat panel and the light line expect OSE shapes. | `lib/socket.svelte.ts:171`; `lib/CharacterCreation.svelte:18`; `lib/CharacterPanel.svelte:19-24`; `lib/protocol.ts:26-34`, `:89-102`; `App.svelte:21-36`; `registry.py:120` (never read) | 1 | The web renders the sheet, the creation form, and panels from registry metadata (schema, input `choices`, tracks). The class list fix is one `choices` entry. | Belongs in phase 2 (class list fits phase 1) |
| L14 | The state note writes the map, the OSE dungeon, the FlexTale inventory, and the FlexTale encounter by key name. | `vault.py:71-87`, `:112-121`, `:143` | 1, 2 | Each plugin supplies its own state note section. | Belongs in phase 3 |
| L15 | "Standing" means `hp > 0`, and the Simple AI picks targets by HP. Ironsworn has a 0 to 5 health track and a Face Death move. | `party.py:19`; `plugins/flextale/simple_ai.py:59-61` | 1 | A ruleset hook that says if a member can act and how hurt it is. | Belongs in phase 5 |
| L16 | Mythic keeps thread and character lists, and random events roll on them, so they are mechanical state (ADR 0001). The Referee keeps threads and NPCs as vault notes, and the gap hunt asks for quest state (gap 2.4). Three owners hold one list. | `referee/tools.py:104-169` (no world tools); gap 2.4, 2.6 | 2, 3 | Engine-owned thread and NPC lists, shared by quests, the Referee world tools, and oracles. | Belongs in phase 3 |
| L17 | Each state-changing click starts a Referee turn. The split needs per-procedure data: an Ironsworn move or an OSE check is a direct action, and a Mythic fate question needs the world to answer. | `server.py:173-174` | 1, 2 | Procedure metadata: who starts it, and if a Referee turn follows. | Must come before phase 2 (gap 4.10) |

## Leak count by phase impact

| Phase impact | Leaks | Count |
|--------------|-------|-------|
| Must come before phase 2 | L9, L17 | 2 |
| Belongs in phase 2 | L11, L12, L13 | 3 |
| Must come before phase 3 | L4, L7, L8 | 3 |
| Belongs in phase 3 | L3, L5, L6, L10, L14, L16 | 6 |
| Must come before phase 4 | L1 | 1 |
| Belongs in phase 5 | L2, L15 | 2 |

## Findings that can change a phase boundary or the order

1. **Phase 2 opens with the control seam.** The direct-action split (L17) and an engine-owned token move (L9) are one change. `move` leaves the OSE plugin in the same change.
2. **Phase 2 builds the sheet from metadata, not from OSE fields.** When the phase 2 sheet and direct edits read OSE names (L12, L13), phase 5 Ironsworn redoes phase 2. Add tracks and schema-driven rendering to the phase 2 scope.
3. **Phase 3 needs an engine seams step first, or its own phase.** Inventory (L7), time (L8), the event vocabulary and the one-responder rule (L4, L6), and the site model from the gap hunt all change engine state. Together they are large enough for a phase between 2 and 3.
4. **Plugin discovery comes before phase 4.** Each converted module is a plugin. With a hard-coded plugin list (L1), each module needs a toolkit release.
5. **Nothing tests the plugin bar before phase 5.** Every campaign in phases 1 to 4 is OSE with FlexTale, so leaks grow unseen. A Mythic GME generator plugin is a cheap probe: `charts.py` already has the fate math, and the fate check and the scene test need no book text. Make it the exit test of the seams step or of phase 3. Ironsworn stays in phase 5.
