# The Augur: how a player runs each step of the arc

Date: 2026-11-26

Ticket: [Study how The Augur lets a player run each step of the arc](https://github.com/JeffreyHartman/solo-rpg-toolkit/issues/27)

Question: in The Augur (theaugur.app), how does the player run each step of the
"fully playable" arc by hand, and where does its AI chat take part?

## Method and limits

- App version 2.0.14b, web client, on the owner's account. An agent drove the
  owner's logged-in Chrome through the Claude in Chrome extension.
- The agent made a new game, "Wayfinder Study", with the Knave - OSR ruleset. Knave
  is the nearest ruleset to OSE. The owner's other game was not opened.
- The app has no help pages. The only built-in guide is the Quickstart panel. Most
  toolbar buttons show a tooltip on hover, and some panels show a "Hint" line.
- The AI chat needs the player's own OpenAI API key. The agent cannot enter API
  keys, so no AI reply was tested. The note describes the AI chat from its panels
  and settings only.
- The study is as a player. No app code was read.
- Screenshots are outside the repo, in `~/temp/augur-study/` (`s00.jpg` to
  `s86.jpg`). The raw observation log is `~/temp/augur-study/log.md`. The
  [screenshot index](#screenshot-index) lists what each one shows.

## Summary

1. **The Augur is a toolbox, not a referee.** It gives the player panels, generators,
   oracles, maps, and dice. It does not run any procedure. Nothing happens unless the
   player clicks it, and no roll changes any state by itself.
2. **Generators are the strongest part.** A new settlement or dungeon comes from a
   template with art, a map, rolled traits, a leader and NPCs, and zones. The player
   can "Roll another" or "Accept". A settlement "Trouble" and a foe "Quest Starter"
   give the hook.
3. **The OSE arc mostly has no support.** The agent found no gold field, no shop, no
   buy or sell, no XP, no level up, no rest or healing procedure, no travel procedure,
   no encounter check, no light or encumbrance tracking, and no combat tracker.
4. **The ruleset choice is shallow.** With Knave selected, the sheet shows Knave
   ability names. The oracles stay Starforged, the moves stay Ironsworn, and the attack
   rolls a d6 dice pool with a "Push" option. That pool is not Knave.
5. **Roll results do not persist.** Each roll shows as a toast with a copy button. The
   journal does not record rolls. The player copies results into notes by hand.
6. **The AI chat is a side panel, not a game master.** It is a list of chat pages. Each
   page has an editable system prompt and a summarize prompt. Neither prompt mentions
   game state, and the agent found no setting that sends the sheet or the map to the
   model. With the ChatGPT toggle off, the same page is a plain text log.
7. **The table frame is good.** The canvas holds the current location map. Every tool
   opens as a panel that the player can dock left, center, or right. Saving is automatic
   and synced. Reload returns to the same map with tokens in place.

## The app frame

The screen is a full-window canvas with two toolbars at the bottom. See `s02`.

- **Left toolbar:** the character portrait (opens the sheet), New Ship, Character
  List, Map Settings, Settings, and Browser.
- **Right toolbar:** Quick Menu, Oracles & Moves, Dice Roller (right-click for the full
  panel), Drawing Toolbar, Journal, AI Chat, and Assets.
- **Center:** the Current Location button. After the player opens a second location, a
  main-map button and a back button appear next to it (`s71`).
- **Panels:** each panel has a layout button next to its close button. The choices are
  Left Panel, Center Panel, and Right Panel (`s17`, `s18`). Two panels can be open at
  once, one on each side.
- **Browser:** a tree of everything in the game: the journal, locations, and their
  children. "+" makes a New Location, Faction, Character, Note, or Folder. Right-click
  gives options. Drag and drop changes the order (`s54`).
- **Settings:** Games, Quickstart, Modules, Rulesets, UI Theme, Account, ChatGPT, Edit
  Background, Go Fullscreen, and Old 1.4 Version (`s04`).

## Step 1: make a character, roll gold, buy gear

**Panels and clicks.**

1. The Quickstart panel opens on a new game. It lists Select a ruleset, Select UI
   theme, Select Modules, and Create character (`s02`).
2. Rulesets: Ironsworn, Starforged, Knave - OSR, or System Agnostic. One choice. A
   hint says that the player can change it at any time (`s06`).
3. Modules: content packs. The defaults are Core, Ironsworn, Starforged, Sci-Fi, and
   Fantasy. There is no Knave or OSR content pack (`s08`).
4. Create character opens a portrait builder first: Appearance, Body, Torso, Bottom,
   Weapon, Shield, and Background slots. Some art is locked behind a paid tier. Weapon
   art shows a hand and a slot count (`s09`, `s10`).
5. A name dialog follows. The character then appears as a portrait button in the left
   toolbar (`s11`).

**The sheet** (`s12`). Six Knave abilities, all 0. Health 4/4 and Armor 0. Four tabs:

- **Narrative:** a yes/no oracle with five odds, and word oracles for Action, Theme,
  Descriptor, and Focus (`s24`, `s25`).
- **Bonds:** a drop zone for characters and locations (`s27`).
- **Gear:** Add Attack, a paper doll with equipment slots, a 10 x 4 inventory grid,
  the appearance editor, and Add Custom Item (`s19`, `s20`).
- **Overview:** Add Personality Traits and a Markdown description (`s15`).

Below the abilities, the sheet also shows four generic attributes (Strength, Agility,
Wits, Empathy, each +2) and twelve skills, all 0.

**What the player edits directly.** Name, portrait art, custom items (name and Markdown
description), attacks (name, bonus, damage, range, special), and the description.

**What the app does.** Nothing for Knave character creation. There is no button to roll
ability scores. A click on an ability opens a check popup (value, modifier, difficulty
11, Roll), not an editor (`s13`, `s14`). Clicks, double-clicks, right-clicks, and typing
on the value did not change it. There is no gold field, no starting-gold roll, no
equipment list with prices, and no shop. The weapon chosen in the portrait builder did
not appear in an equipment slot. "Items" in the asset library are pictures only, with
no stats or prices (`s45`).

**AI chat.** Not part of this step.

## Step 2: start in a settlement with a reason to go somewhere

**Panels and clicks.**

1. Browser, then "+", then New Location (`s54`).
2. Pick a location type: Hexmap, Planets, Settlements, Ships, Dungeons, or Star Map
   (`s55`).
3. Pick a settlement template: Castle, City, Coastal Village, Settlement, Village, or
   Habitat Station (locked). There is a theme filter and a culture choice (`s56`).
4. The app generates a settlement. The test made "Fireoak": cover art, Prosperity,
   Population, Project, Trouble, an extended description, a leader with a portrait and
   role, and two notable NPCs (`s57` to `s61`).
5. "Roll another" makes a new one. "Accept" keeps it. A hint says that the player can
   edit or add NPCs after accepting.
6. The settlement appears in the Browser. "Open Map" puts a drawn village map on the
   canvas (`s62`, `s63`).
7. The player drags the character portrait from the toolbar onto the map. That makes a
   token. Right-click on a token gives Open Details Panel, Customize Avatar, Show as
   Avatar, Hide Name, Flip, Resize, Lock, Remove from map, and Delete from game (`s64`,
   `s65`).

**What the player edits directly.** Everything after Accept: NPCs, description, cover,
and icon. Location settings also allow "Make default/main location" and a per-location
Custom Ruleset (`s51` to `s53`).

**What the app does.** Generates the settlement, its map, and its people. NPC
disposition, long-term goal, and task stay "Unknown" until the player rolls or writes
them. The settlement "Trouble" is the built-in reason to go somewhere. Foe cards also
carry a "Quest Starter" (`s76`).

**AI chat.** Not part of this step.

## Step 3: travel to a site

**Panels and clicks.**

1. Make a Dungeon location the same way as a settlement. Templates include Castle, Dark
   Temple, Derelict Facility, Necromancer's Lair, and Ruins. Some are locked (`s67`).
2. The generated dungeon has art, Condition, Outer and Inner Appearance, and a list of
   zones (for example Quarters, Sanctum, Access). Each zone has art and Type, Area,
   Feature, and Opportunity fields (`s68` to `s70`).
3. "Open Map" switches the canvas to the dungeon map (`s71`).

**What the app does.** Travel is a change of map. There is no travel procedure, no
time, no distance, and no encounter roll. The character token does not move with the
player: each map has its own tokens. A hexmap location type and Hexmap Tools exist for
painting a region by hand (terrain tiles by biome, rivers, roads, eraser, map size)
(`s49`). The agent found no hexmap generator.

**AI chat.** Not part of this step.

## Step 4: delve with inventory, light, encumbrance, and combat

**Panels and clicks.**

1. Right-click on the map: New Location, New Character, New Foe, Enable Fog of War, Show
   Map Grid, Enable Grid Snapping, Hexmap Tools, and Drawing Tools (`s72`).
2. New Foe opens a foe list with art, type, and an Ironsworn-style rank. The player drags
   a foe's image onto the map (`s73`, `s74`).
3. The foe details panel shows art, features, drives, tactics, prose, a Quest Starter,
   and an "Imagine" paragraph (`s75` to `s79`).
4. An attack on the sheet opens a popup: skill, a melee maneuver list (for example
   Target Prone, Defenseless Target, Diving Blow), a modifier, and Roll (`s82`, `s83`).
5. The roll shows a toast with the dice, "Missed" or a hit, and a Push button (`s84`).
6. Oracles & Moves panel: the yes/no oracle, a d100 button, oracle tables by source and
   category, and a move list. A move card shows its rules text and a Roll button. Its
   result is a toast with the action die, the challenge dice, the outcome, and "Match"
   (`s28` to `s35`).

**What the player edits directly.** Foe placement, fog of war, the grid, drawings, map
layers (visible, locked, selectable, order) (`s46` to `s48`), and the inventory grid.

**What the app does.** Rolls dice and shows the result. It does not pick a target, apply
damage, track foe hit points, keep turn order, or apply a move's effects (for example
momentum or supply). Foes have no hit points or attack stats on their card. There is
no light or encumbrance tracking. The inventory grid has 40 cells, and the portrait
weapons show a slot count, but the agent saw no rule that uses them.

**AI chat.** Not part of this step, unless the player asks the chat by hand.

## Step 5: go back to town, sell, heal, gain XP, level up

**Panels and clicks.** The back button and the main-map button in the center toolbar
return to an earlier map (`s71`). The settlement keeps its NPCs and map.

**What the app does.** The agent found no way to sell treasure, no gold, no healing or
rest procedure, no XP field, and no level up. Health is a field on the sheet. The agent
did not find how to edit it, for the same reason as the ability scores.

**AI chat.** Not part of this step.

## Step 6: end the session and start the next one

**Panels and clicks.**

1. Nothing to do. A hint says that the game saves and syncs on its own (`s04`).
2. Settings, then Games: a list of games with delete, rename, and "+" for a new game
   (`s85`).
3. After a page reload, the main menu shows the last character's portrait and "Continue:
   Wayfinder Study". One click returns to the same dungeon map with the foe token in
   place (`s86`).

**What the app does.** Auto-save, cloud sync, and resume. There is no session boundary,
no session recap, and no session log beyond the player's own journal and chat pages.

**AI chat.** The Summarize Text button on a chat page can summarize earlier text. That is
the nearest thing to a recap. It was not tested.

## Rolls and records

- Every roll result is a toast above the left toolbar. A toast has a close button and a
  copy button. Toasts do not stack into a log.
- The Journal is one rich-text page: font size, bold, italic, color, lists (`s36`). It
  stays empty until the player writes in it.
- Oracle results stay inline in the oracle panel under the table name, with a copy
  button (`s30`).
- The sheet's Narrative tab keeps its last oracle results until the player clears them.

## The AI chat

- The AI Chat panel is a list called "Conversations with the Augur". "+" makes a new
  page, and pages can go in folders. A double tap opens a page in the center panel
  (`s37`, `s38`).
- A page has an input box, a send button, a ChatGPT toggle, a Summarize Text button, a
  Copy Text button, and a settings button.
- Page settings: "Show current map in page panel", an editable system prompt, an
  editable summarization prompt, and Delete Page (`s41`). The default system prompt
  describes a general assistant inside a tabletop app. It does not mention the
  character, the location, or the rules.
- The key is the player's own OpenAI API key. The app stores it in the browser on each
  device and says that it does not store it on its servers (`s05`).
- With the toggle off, a sent message stays on the page as plain text (`s42`). So one
  page type serves as an AI chat and as a manual play log.
- The AI cannot act on the game. The agent found no control that lets the chat roll,
  change the sheet, place a token, or make a location.

## What this means for the harness

These are observations for the phase tickets, not decisions.

- **The Augur sets the bar for the table, not for the referee.** Docked panels, a
  location tree, generated places with maps, drag-to-place tokens, and auto-resume are
  the parts worth matching in phase 2 ("The table").
- **The OSE arc is the gap The Augur leaves open.** Gold, shopping, encumbrance, light,
  travel, combat state, XP, and levels are all manual or missing there. Phase 3 ("The
  full arc") is where this harness can be better than the bar.
- **Generate, then let the player re-roll or accept.** The "Roll another" and "Accept"
  pair is a cheap pattern for any generator plugin.
- **Keep a roll log.** The Augur loses roll results once a toast closes. A persistent,
  searchable log of rolls and procedures is a clear improvement.
- **A shallow ruleset switch confuses.** Knave in name with Ironsworn moves and a d6 pool
  is worse than one ruleset done fully. The plugin bar must make a ruleset own its
  sheet, its rolls, and its procedures together.
- **An AI chat without state is a notebook.** The Augur's chat cannot see or change the
  game. The harness Referee acts through engine tools, which is the larger difference.

## Screenshot index

All files are in `~/temp/augur-study/`.

| File | What it shows |
|---|---|
| `s00` | New game name dialog on the main menu |
| `s01` | Loading screen for the new game |
| `s02` | Empty table, both toolbars, Quickstart panel |
| `s03` | Browser panel, empty tree |
| `s04` | Settings menu, top half |
| `s05` | ChatGPT settings: API key field |
| `s06` | Ruleset selection |
| `s07` | Quickstart after the ruleset choice |
| `s08` | Modules list |
| `s09` | Portrait builder |
| `s10` | Character name dialog |
| `s11` | Character portrait in the left toolbar |
| `s12` | Character sheet, Knave abilities |
| `s13` | Ability check popup |
| `s14` | Ability check result toast |
| `s15` | Overview tab |
| `s16` | Gear tab, top |
| `s17` | Panel layout menu |
| `s18` | Sheet as center panel |
| `s19`, `s20` | Gear tab: paper doll, inventory grid, buttons |
| `s21` | Add Custom Item card |
| `s22` | Sheet scrolled to top |
| `s23` to `s26` | Narrative tab: yes/no oracle and word oracles |
| `s27` | Bonds tab |
| `s28` | Oracles & Moves panel |
| `s29` | Oracle source list |
| `s30` | Oracle result inline |
| `s31` | Oracle category list |
| `s32` | Moves list |
| `s33` | Move card |
| `s34` | Move roll menu |
| `s35` | Move result toast |
| `s36` | Journal |
| `s37` | AI Chat list |
| `s38` | Chat page |
| `s39`, `s40` | Chat footer tooltips: Summarize Text, Copy Text |
| `s41` | Chat page settings and prompts |
| `s42` | Chat page with the AI toggle off |
| `s43` | Assets library |
| `s44`, `s45` | Item assets: pictures only |
| `s46` to `s48` | Map Settings and layers |
| `s49` | Hexmap Tools |
| `s50` | Current Location panel |
| `s51` to `s53` | Location settings |
| `s54` | Browser "+" menu |
| `s55` | Location types |
| `s56` | Settlement templates |
| `s57` to `s61` | Generated settlement before Accept |
| `s62` | Settlement after Accept |
| `s63` | Settlement map |
| `s64` | Character token on the map |
| `s65` | Token right-click menu |
| `s66` | Settlement map, panels closed |
| `s67` | Dungeon templates |
| `s68` to `s70` | Generated dungeon and zones |
| `s71` | Dungeon map, center navigation buttons |
| `s72` | Map right-click menu |
| `s73` | Foe list |
| `s74` | Foe token on the map |
| `s75` to `s79` | Foe details panel |
| `s80` | Add Attack form |
| `s81` | Attack card on the sheet |
| `s82`, `s83` | Attack popup and maneuver list |
| `s84` | Attack result toast with Push |
| `s85` | Games list |
| `s86` | Resumed game after reload |
