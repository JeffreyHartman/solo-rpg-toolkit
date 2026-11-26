# Solo RPG Toolkit

Tools for solo tabletop play. A player runs a campaign alone, with procedures and an AI referee in place of a human game master.

## Play

**Harness**:
The program in which a player plays a session: map, chat, and state in one place.
_Avoid_: app, client, VTT

**Engine**:
The part of the harness that owns all mechanical state and all dice: HP, position, the map, clocks, and inventory counts. Every player action and Referee action that changes mechanical state goes through it.
_Avoid_: backend, game server

**Campaign**:
One continuous game with its state, journal, and the plugins it uses.
_Avoid_: game, save, world

**Party**:
The player characters of a campaign. It can hold one character or several.
_Avoid_: group, team, PC (when it means all of them)

**Session**:
One sitting of play. Each session starts a new Referee conversation from campaign state, and the player can end it and start a new one at any time.
_Avoid_: game night, run

**Campaign settings**:
The choices for one campaign that the player can change at any time during play, for example the confirm level of a procedure or who decides a judgment call.
_Avoid_: config, preferences

**Referee**:
The AI role in the harness. It narrates, interprets free text, proposes procedures, and writes records. It changes mechanical state only through the engine.
_Avoid_: GM, DM, narrator, AI

**Procedure**:
A fixed sequence of rule steps that the engine runs, for example an Ironsworn move, a dungeon turn, or a FlexTale room roll. A plugin defines it.
_Avoid_: move (except for Ironsworn moves), routine, flow

**Proposal**:
A procedure with its inputs, offered by the Referee for the player to confirm, change, or reject before the engine runs it.
_Avoid_: suggestion, request

**Judgment call**:
A step in a procedure that needs a human decision, for example "does this action mark progress?". The Referee suggests an answer, and the player decides.
_Avoid_: gut call, ruling

**Record**:
A story fact that play established, kept as a markdown note in the campaign vault: an NPC, a place, a thread, a clue, or a session log entry. The Referee and the player write records freely. A new session learns the story from records, not from old chat.
_Avoid_: memory, lore, note (when it means a record)

**Vault**:
The Obsidian folder that holds the records of one campaign. The player can open it in Obsidian outside the harness.
_Avoid_: journal (when it means the folder), notes folder

**Mechanical block**:
The part of a character note that the engine rewrites after every action, between the `%% engine:begin %%` and `%% engine:end %%` markers. It shows the character's mechanical state in Obsidian. The Referee cannot change it.
_Avoid_: stat block (when it means this), sheet

**Referee folder**:
The folder beside the vault, outside it, where the Referee keeps secrets the player has not found. Neither the harness nor Obsidian shows it.
_Avoid_: GM notes, secrets vault

**Map**:
The areas of a campaign, the connections between them, and what the player knows about each one. Distance and position are narrative unless a ruleset adds tactical movement.
_Avoid_: dungeon (when it means the map), level

**Area**:
One place on a map that the player can be in, for example a room or a corridor.
_Avoid_: room (when it means any area), node, tile

**Available action**:
An action that the engine offers for the current state, for example "go through the north door". The player can start it with a click. Free text is always available beside it.
_Avoid_: option, command

## Plugins

**Plugin**:
A package that adds rules or content to the harness. Each plugin is a ruleset, a generator, or a module.
_Avoid_: extension, add-on, system

**Trigger**:
Plugin code that the engine runs on an engine event, for example a wandering-monster check every two turns.
_Avoid_: hook, listener

**Ruleset**:
A plugin that holds the mechanics for the player character: stats, checks, combat, rest. A campaign has exactly one.
_Avoid_: system, game system

**Generator**:
A plugin that holds procedures which make content or answer questions from tables. A campaign has zero or more. Mythic GME, FlexTale, and the Ironsworn oracles are generators.
_Avoid_: oracle (when it means the whole plugin), table pack

**Module**:
A plugin that holds fixed, authored content, for example a published dungeon with its map and key. A campaign has zero or one.
_Avoid_: adventure, scenario
