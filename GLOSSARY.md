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
The span of play between two End session actions. It is usually one sitting, but only the player ends it. The harness resumes one Referee conversation for it until End session.
_Avoid_: game night, run, sitting

**Recap**:
The Referee's short retelling of the story so far, at the start of a session or after a long gap in play.
_Avoid_: summary, previously-on

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

**Confirm level**:
A campaign setting of each procedure. An Auto procedure that the Referee proposes runs at once; a Confirm procedure waits as a proposal for the player.
_Avoid_: approval mode

**Target number**:
The number a roll must meet, for example an ability score, a save, a DC, or an AC. It comes from plugin data when the data exists; otherwise it is a proposal input. Every mechanics card carries a citation.
_Avoid_: difficulty (when it means the number)

**Citation**:
The rule that a mechanics card or the Referee points to: the book, the section, and the pages, or "no page" when the toolkit builds the procedure. A click on it opens the rule text.
_Avoid_: source (when it means the rule), reference

**Rule index**:
The list of rules that a plugin can cite, each with its book, section, and pages. It holds no book text.
_Avoid_: rules list, table of contents

**Judgment call**:
A step in a procedure that needs a human decision, for example "does this action mark progress?". The Referee suggests an answer, and the player decides.
_Avoid_: gut call, ruling

**Record**:
A story fact that play established, kept as a markdown note in the campaign vault: an NPC, a place, a thread, a clue, or a session log entry. The Referee and the player write records freely. A new session learns the story from records, not from old chat.
_Avoid_: memory, lore, note (when it means a record)

**Vault**:
The Obsidian folder that holds the records of one campaign. The player can open it in Obsidian outside the harness.
_Avoid_: journal (when it means the folder), notes folder

**Raw log**:
The engine's record of everything in the play of one session, events and chat, in play order. Nobody edits it.
_Avoid_: transcript, session log

**Session note**:
The Referee's short story of one session, written from the raw log at End session, with links to the records.
_Avoid_: summary, write-up (when it means the note)

**Mechanical block**:
The part of a character note that the engine rewrites after every action, between the `%% engine:begin %%` and `%% engine:end %%` markers. It shows the character's mechanical state in Obsidian. The Referee cannot change it.
_Avoid_: stat block (when it means this), sheet

**Referee folder**:
The folder beside the vault, outside it, where the Referee keeps secrets the player has not found. Neither the harness nor Obsidian shows it.
_Avoid_: GM notes, secrets vault

**Map**:
One set of areas, the connections between them, and what the player knows about each one, for example one dungeon level or one town. A campaign holds many maps. Distance and position are narrative unless a ruleset adds tactical movement.
_Avoid_: scene (Mythic GME uses Scene for a narrative unit), dungeon (when it means the map), level

**Active map**:
The map that the party is on now. The harness shows it, and the Referee or a link (for example a staircase) changes it.
_Avoid_: current scene, current level

**Link**:
A way from an area of one map to an area of another map, for example a staircase or a dungeon entrance. A link goes one way. Taking it moves the party to the other map, which becomes the active map.
_Avoid_: portal, exit (when it means a way to another map), teleport

**Map fact**:
A value that a map carries and that procedures read, for example the dungeon level or how often wandering monsters come.
_Avoid_: map setting, map property, tag

**Token**:
The mark of a party member, a monster, or an NPC on a map. A token stands in one area. The player moves only the tokens of the party.
_Avoid_: piece, mini, avatar

**Area**:
One place on a map that the player can be in, for example a room or a corridor.
_Avoid_: room (when it means any area), node, tile

**Fog**:
What the player knows of each area of a map. An area is hidden (the player sees nothing), known (the player knows that it exists, for example from a rumor), or explored (the party saw it). The area that holds the party is visible.
_Avoid_: vision (a later system that decides what each token sees), reveal state

**Available action**:
An action that the engine offers for the current state, for example "go through the north door". The player can start it with a click. Free text is always available beside it.
_Avoid_: option, command

**Direct action**:
A change that the player makes to their own party through the engine, for example an edit to the sheet, a move of gear, a check, or a move of the party token. It gets no Referee turn unless it raises a wake.
_Avoid_: manual edit, override

**Referee turn**:
One reply of the Referee: narration, rulings, or moves of the world, after which it waits for the player.
_Avoid_: GM turn, AI turn

**Wake**:
An event that tells the harness that the world must answer, so a Referee turn starts. For example, the party enters an unexplored area, or a wandering-monster check finds a monster.
_Avoid_: trigger (a Trigger is plugin code), interrupt

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
