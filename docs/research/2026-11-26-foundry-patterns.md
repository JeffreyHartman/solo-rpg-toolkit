# Foundry VTT patterns for an engine-owned table

Date: 2026-11-26

Ticket: [Research: Foundry VTT patterns for an engine-owned table](https://github.com/JeffreyHartman/solo-rpg-toolkit/issues/41)

Question: which patterns from Foundry VTT, and from other VTTs, fit a harness where
the engine owns state, the player moves only the party, and maps are made of areas?

## Method and limits

- Sources are the Foundry knowledge base (KB), the Foundry v13 API docs, and the
  release notes at foundryvtt.com. Each claim has a source tag. The
  [Sources](#sources) list gives the links.
- Foundry core is commercial software under the Foundry license. Its source is not
  in a public repo. The note uses only the public docs for core behavior.
- The `foundryvtt` GitHub organization holds issue trackers and systems. The
  `foundryvtt/foundryvtt` repo is an issue tracker with no license file. The note
  looked at file names in `foundryvtt/dnd5e` (MIT) only.
- The Owlbear Rodeo docs site refused automated fetches (HTTP 403). The Owlbear
  facts come from the Owlbear SDK type files (`owlbear-rodeo/sdk`, MIT) and from
  search-engine summaries of the docs and the blog. Those summaries are marked
  "(search)".
- The open-source VTT is MapTool (`RPTools/maptool`, AGPL-3.0). The note read
  field names and one method in its map model. It copies no code.
- Foundry v14 is current (stable 6, June 2026). The API pages are v13. The KB pages
  have no version on most of them.
- Words: the note uses "scene" only for the Foundry document. In this repo the same
  thing is a Map (`GLOSSARY.md`).

## Summary

1. **Foundry splits the persistent thing from its placement.** An Actor holds the
   character. A Token is the Actor's placement on one scene, with its own position
   in pixels [KB-TOK] [API-TOK]. A token on a second scene is a second document.
2. **Foundry has one shared coordinate space per scene.** Width, height, padding,
   and grid size are all in pixels. The grid is a setting of the scene, and
   "Gridless" is one grid type [KB-SCN]. Tokens, notes, and regions all use the same
   pixel space.
3. **Foundry fog is vision fog, not area fog.** Exploration is a raster image per
   user per scene, made from what tokens with vision see [KB-SCN] [API-FOG]. Walls
   drive it. The core docs show no tool to reveal an area by hand. Level B has no
   walls, so this pattern does not fit.
4. **Scene Regions are the nearest Foundry match to an Area.** A region is a set of
   shapes in scene space with behaviors that fire on token events, for example
   "Token Enters" and "Teleport Token" [KB-REG]. A region does not reveal fog.
5. **Owlbear Rodeo and MapTool both reveal fog by shape.** Owlbear fog is a set of
   shapes that the GM cuts open, room by room (search) [OBR-FOG]. MapTool stores an
   exposed area as a vector shape in map space [MT-ZONE]. Both fit level B.
6. **Ownership limits what a player controls.** In Foundry an Actor owner controls
   the token. A lower level lets the user see the sheet or nothing [KB-ACT]. Owlbear
   has a "CHARACTER_OWNER_ONLY" permission [OBR-PERM]. This matches ADR 0003.
7. **Chat is the log in all three tools, and Foundry systems make it a card.** A
   Foundry ChatMessage holds content, rolls, a speaker, and a whisper list
   [API-CHAT]. The dnd5e system renders cards with buttons and a list of state
   changes [DND5E].
8. **"Activate" is how a Foundry GM moves the party.** Activation pulls all users to
   one scene. A Teleport Token region moves a token to a region on another scene
   [KB-SCN] [KB-REG].

## Patterns

Each pattern has two checks:

- **Level B**: does it fit an image or styled map, area reveal, tokens in areas, and
  no walls?
- **Phase 7**: does it keep room for the phase 7 grid on the same coordinates, with
  no change to the save format?

### 1. Data model: Scene, Token, Actor, Item, JournalEntry, Compendium

What Foundry does:

- A **Scene** holds a background image, a size, a grid, fog settings, and embedded
  collections: tokens, walls, regions, notes, drawings, tiles, lights, sounds, and
  templates [API-SCN].
- An **Actor** is a character, ally, or monster. The game system defines the actor
  types [KB-ACT]. Ownership sets who sees the sheet and who controls the token.
- A **Token** belongs to one scene. It has `actorId`, `actorLink`, and `delta`
  fields, plus `x`, `y`, `elevation`, `width`, `height`, and `hidden` [API-TOK].
- "Link Actor Data" makes a token share resources with its Actor. With the link off,
  each token has its own resources. The KB says the link is "best used for unique or
  named characters" [KB-TOK].
- A **Prototype Token** is the Actor's preset for new tokens. A placed token "becomes
  its own independent copy of the prototype" [KB-TOK].
- **Items** are owned by Actors or stand alone in the sidebar. The KB actor article
  does not describe the link in detail [KB-ACT].
- A **JournalEntry** holds pages of text, image, PDF, or video. A Map Note pins an
  entry or a page to a point on a scene [KB-JRN].
- A **Compendium** pack stores documents of one type outside the world. An import
  makes a separate copy [KB-CMP].

Fit:

- **Level B: fits.** The split of Actor and Token matches the harness. The party is
  the Actor side, and the party token is a placement on the active map. A monster
  token with no link matches a Referee-placed monster with its own HP.
- **Phase 7: fits.** The token already carries width, height, and elevation in the
  same space as the grid.
- Foundry keeps the delta of an unlinked token inside the token. The engine owns all
  state (ADR 0001), so the engine decides where a monster's HP lives. The Foundry
  shape is one option for that.
- A Compendium is a store of templates that the world copies on import. A Module
  plugin with a dungeon key has the same role.

### 2. How a scene stores its background, grid, fog, and token positions

What Foundry does:

- The background image sets the default size in pixels. Padding adds a border, as a
  percentage of the size [KB-SCN].
- The grid has a type (square, hex, or "Gridless"), a size in pixels per space, and
  a scale label for distance. The KB says that a change of grid size can misalign
  walls, lights, notes, and tiles [KB-SCN].
- A token stores "Coordinates (Pixels)". Placement and moves set them [KB-TOK].
- Fog exploration has a setting per scene. When it is on, exploration "is tracked
  per user and saved to the database" [KB-SCN]. Each FogExploration document links a
  scene and a user and holds an image of the explored part [API-FOG].
- v14 adds scene levels: one scene stacks several images at set elevations, and each
  level has its own background, foreground, and fog texture [REL-14].

Fit:

- **Level B: partly fits.** One background image per map, sized in its own units,
  fits. Raster fog per user does not fit, because the engine reveals by area id, not
  by sight.
- **Phase 7: fits, with one warning.** Foundry keeps one space for gridless and
  gridded maps, so a grid turns on with no new coordinates. The warning is that
  Foundry measures in image pixels. A change of the image resolution or grid size
  moves everything. A unit that does not depend on the image avoids this.
- The v14 levels model matches a dungeon with stairs. A level is a layer of one
  scene, not a second scene.

### 3. How a GM moves the party to another scene

What Foundry does:

- **Activate** loads a scene and pulls all users to it. **View Scene** loads it for
  the GM only [KB-SCN].
- A "GM Only" scene stays hidden from players until a GM activates it or pulls a
  player to it [KB-SCN].
- The "Teleport Token" region behavior moves a token that enters a region to a
  destination region. The destination can be on another scene [KB-REG]. It came in
  v12 [REL-12].
- The KB recommends that combat encounters stay unlinked from the scene when a
  teleport is in use [KB-REG].

Fit:

- **Level B: fits.** "Active map" in `GLOSSARY.md` is the same idea as the active
  scene. A staircase area with a teleport behavior is the same shape as "a staircase
  switches the active map to level 2".
- **Phase 7: fits.** The teleport targets a region, not a grid cell.
- In Foundry the GM activates a scene. In the harness the engine switches the map
  when the party token enters the stair area. Then the Referee does not need a turn
  for the switch.

### 4. GM view, player view, fog reveal, and token permissions

What Foundry does:

- **User roles**: Player, Trusted, Assistant, Gamemaster. "GMs always own every
  document" [KB-USR].
- **Ownership levels**: None, Limited, Observer, Owner. For an Actor, only an Owner
  controls the token. An Observer sees the sheet and sees through the token
  [KB-ACT].
- **Token Vision**: when it is on, a player sees the scene only through an owned
  token with vision [KB-SCN].
- **Fog**: unexplored and explored parts have their own colors or image [KB-SCN].
  A reset deletes the FogExploration documents of all users [SRCH-FOG].
- The core docs show no tool for a manual reveal. The "Fog Weaver" package adds
  manual GM painting (search) [SRCH-FOG].
- A token has a `hidden` field, and the Token HUD has a visibility control [API-TOK]
  [API-HUD].
- GM-only canvas layers, for example walls and sounds, are "only ever visible to
  users with the gamemaster or assistant gamemaster roles" [KB-LAY].

Fit:

- **Level B: the permission model fits, and the fog model does not.** Owner control
  of the party matches ADR 0003. A hidden token matches the rule "the player sees a
  token only in a revealed area". Vision fog needs walls and light, and level B has
  neither.
- **Phase 7: fits.** Vision fog is the phase 7 feature. Area reveal and vision
  reveal can both feed one "revealed" mask. Area reveal comes first.
- In Foundry the client hides objects from the player. In the harness the engine
  sends the player only what the player knows. Then a hidden token never reaches
  the browser.

### 5. Sidebar, chat log, chat cards, roll messages, and the Token HUD

What Foundry does:

- The **sidebar** is on the right. Most tabs list one type of document (search) [KB-GLO].
  v14 adds a "Placeables" tab that lists the objects of the current layer (search) [KB-GLO].
- The **chat log** takes in-character, out-of-character, emote, and whisper
  messages, and four roll commands: `/roll`, `/gmroll`, `/blindroll`, and
  `/selfroll` [KB-CHAT].
- A click on a roll shows each die. The GM can export the log to a text file and can
  delete messages [KB-CHAT].
- A **ChatMessage** document has `author`, `content`, `flavor`, `rolls`, `speaker`,
  `whisper`, `blind`, `system`, and `type` [API-CHAT]. The `system` and `type`
  fields let a game system define its own message kinds.
- The dnd5e system has chat card templates for checks, attacks, damage, and items.
  It has parts for buttons and for "deltas", a list of state changes [DND5E].
- The **Token HUD** opens on a right-click on a placed token. It shows resource
  bars, status effects, elevation, a target toggle, and a combat toggle [KB-TOK]
  [API-HUD].

Fit:

- **Level B: fits.** The chat-as-log choice on map #40 is the Foundry pattern. A
  ChatMessage with a typed system payload matches a mechanics card. The dnd5e
  "deltas" part matches the ADR 0004 rule that each Referee edit shows what changed.
- **Phase 7: fits.** None of these depend on the map.
- A Token HUD on the party token is a place for direct actions in one area, for
  example "rest here" or "search". Token conditions go in the same place later.
- Roll modes (GM, blind, self) match the hidden out-of-character notes on map #40.
  A blind roll is a roll that the player does not see.

### 6. Scene and layer controls

What Foundry does:

- Scene Controls are the buttons on the far left. Each set is for one type of
  placeable object, for example tokens or regions (search) [KB-GLO].
- Token Controls is the default tool. It has Select Tokens, Select Targets, and
  Measure Distance [KB-TOK].
- The canvas draws, from the bottom: background, tiles, tokens, overhead tiles,
  foreground, weather, light and vision effects, templates, sounds, and walls
  [KB-LAY].

Fit:

- **Level B: mostly does not fit.** Most layers are GM build tools. The player in the
  harness moves only the party, so the player needs the token layer and nothing
  else.
- **Phase 7: fits.** The draw order is a good model for a later stack: background,
  area shapes, fog, tokens, then the grid and measure tools.
- The Referee builds the map through engine tools, not through a canvas. A layer
  stack is a render order in the browser, not a set of edit tools.

### 7. Scene Regions as areas

What Foundry does:

- A region "does not physically exist in the map". It is a set of shapes, and its
  area is the union of the shapes. A shape can be a hole [KB-REG].
- Shape types are rectangle, circle, ellipse, cone, ring, line, emanation, and
  polygon [KB-REG].
- Behaviors include Teleport Token, Change Level, Pause Game, Execute Script, and
  Toggle Behavior [KB-REG].
- Events include Token Enters, Token Exits, Token Moves In, and Token Starts Turn.
  "Token Enters" does not fire for a token that is already in the region when the
  scene loads [KB-REG].
- The default visibility is "Only on Region Layer when unlocked", so players do not
  see regions by default [KB-REG].

Fit:

- **Level B: fits.** An area is a region with one or more shapes. The current
  harness area is one rectangle in cells (`x`, `y`, `w`, `h` in
  `web/src/lib/protocol.ts`). A polygon or a set of shapes fits a styled render of
  an irregular cave.
- **Phase 7: fits.** Foundry uses the same regions for movement cost and turn events
  on a grid. One shape list serves both phases.
- Area events in the engine are the Foundry behaviors. The engine already has
  triggers (`GLOSSARY.md`). "Party enters area" is a trigger event.

## Comparison with Owlbear Rodeo and MapTool

### Owlbear Rodeo

- Every object on the canvas is an Item with `position`, `rotation`, `scale`,
  `visible`, `locked`, `layer`, `attachedTo`, and free `metadata` [OBR-ITEM].
- Layers include MAP, GRID, PROP, CHARACTER, NOTE, FOG, and RULER [OBR-ITEM].
- The grid has a type (square, two hex types, dimetric, isometric), a `dpi` for one
  cell, and a scale text such as "5ft" [OBR-GRID]. An image has its own grid
  `offset` and `dpi`, so it lines up with the scene grid [OBR-IMG].
- Fog is a set of shapes on the FOG layer. The GM draws a shape around each room,
  then uses "Fill Fog" to hide the rest. "Cut/Uncut" on a shape reveals or hides that
  room (search) [OBR-FOG].
- The GM sees through fog. A preview shows the player view (search) [OBR-FOG].
- Line-of-sight fog is an extension, "Dynamic Fog" (GPL-3.0), that uses walls
  [OBR-REPOS].
- A player has the role GM or PLAYER [OBR-PLR]. Permissions are per layer and per
  action. "CHARACTER_OWNER_ONLY" limits a character to the player who owns it
  [OBR-PERM].

Fit: Owlbear room fog is the nearest match to level B area reveal. Per-image grid
`dpi` and `offset` keep a background image independent of the map units. Both fit
phase 7. Owlbear `metadata` on each item is a place for plugin data, for example a
token condition.

### MapTool

- A map ("Zone" in the code) has a grid, a "units per cell" value, a token list,
  labels, and a vision type of OFF, DAY, or NIGHT [MT-ZONE].
- Tokens sit on one of four layers: TOKEN, GM, OBJECT, and BACKGROUND. The GM layer
  is also named "HIDDEN". Players use the TOKEN layer [MT-ZONE].
- The exposed fog is a vector area in map coordinates. An expose call adds a shape to
  it. With individual fog on, each owned token keeps its own exposed history
  [MT-ZONE] [MT-EXP].
- When vision is OFF, an expose call adds to the shared exposed area [MT-ZONE].
- MapTool has a "GridlessGrid" type [MT-ZONE].

Fit: MapTool shows that a vector "revealed" shape in map space works with and
without vision. With vision OFF it is pure manual reveal, which is level B. With
vision on it is phase 7. One field serves both.

## Patterns that do not fit level B

- Vision fog from walls and light (Foundry core, Owlbear Dynamic Fog, MapTool
  vision). Phase 7.
- Fog as a raster image per user (Foundry). The engine reveals by area id, so a
  list of revealed area ids is the stored fact, and the browser draws it.
- GM canvas build tools (walls, lights, sounds, tiles). The Referee works through
  engine tools.
- A client that hides objects that it already holds. The engine filters the player
  view before it sends it.

## What this means for the map model

These are observations for [Decide the map model (#44)](https://github.com/JeffreyHartman/solo-rpg-toolkit/issues/44)
and the map prototype (#48). They are not decisions.

1. All three VTTs keep one coordinate space per map and put the grid in it as a
   setting. Foundry and MapTool have an explicit gridless type. This supports "units
   plus an optional grid size" on map #40.
2. Foundry measures in image pixels, and a change of grid size moves placed objects.
   Owlbear gives each image its own `dpi` and `offset`. A map unit that does not
   depend on the background image avoids the Foundry problem.
3. Foundry splits Actor from Token, and a token belongs to one map. A party token as
   a placement record (map, area, position) beside the party state matches this.
4. A Foundry region is a list of shapes, and a shape can be a hole. A list of shapes
   per area fits rectangles now and polygons from a styled render later. It is also
   the phase 7 shape for movement cost.
5. Owlbear reveals fog room by room, and MapTool stores a vector exposed area. Both
   fit area reveal. A list of revealed area ids is smaller than both, and the
   browser can draw the fog from it.
6. MapTool keeps the exposed area beside vision, with vision OFF as one mode.
   Phase 7 vision reveal can add to the same "revealed" state with no change to
   the area model.
7. Foundry token fields (`hidden`, `width`, `height`, `elevation`, `texture`,
   `ring`) and Owlbear item `metadata` show room for later token art and
   conditions. A token record with an open slot for appearance and conditions
   matches them.
8. Foundry "Activate" and "Teleport Token" match the active map switch. A stair area
   with a link to an area on another map is the same shape as a Foundry teleport
   region.
9. Foundry v14 levels put several floors in one scene, each with its own fog. The
   harness choice between "one map per level" and "levels in one map" has a
   precedent on each side. Foundry before v14 used one scene per level.
10. Foundry, Owlbear, and MapTool hide objects in the client. The engine can send
    only revealed areas and the tokens in them. Then the prototype has no need for
    a GM view in the player browser.
11. The chat card with a typed payload (Foundry `system` and `type`, dnd5e deltas)
    is the card model for the chat stream. It does not depend on the map model.

## Sources

Foundry VTT (commercial software; docs at foundryvtt.com):

- [KB-SCN] Scenes. https://foundryvtt.com/article/scenes/
- [KB-TOK] Tokens. https://foundryvtt.com/article/tokens/
- [KB-ACT] Actors. https://foundryvtt.com/article/actors/
- [KB-USR] Users and Permissions. https://foundryvtt.com/article/users/
- [KB-JRN] Journal Entries. https://foundryvtt.com/article/journal/
- [KB-CMP] Compendium Packs. https://foundryvtt.com/article/compendium/
- [KB-CHAT] Chat Log. https://foundryvtt.com/article/chat/
- [KB-LAY] Canvas Layers. https://foundryvtt.com/article/canvas-layers/
- [KB-REG] Scene Regions (v14.369). https://foundryvtt.com/article/scene-regions/
- [KB-GLO] Glossary of Terms, read through search results. https://foundryvtt.com/article/glossary/
- [API-SCN] BaseScene (v13). https://foundryvtt.com/api/v13/classes/foundry.documents.BaseScene.html
- [API-TOK] BaseToken (v13). https://foundryvtt.com/api/v13/classes/foundry.documents.BaseToken.html
- [API-CHAT] BaseChatMessage (v13). https://foundryvtt.com/api/v13/classes/foundry.documents.BaseChatMessage.html
- [API-FOG] FogExploration (v13). https://foundryvtt.com/api/v13/classes/foundry.documents.FogExploration.html
- [API-HUD] TokenHUD (v13). https://foundryvtt.com/api/v13/classes/foundry.applications.hud.TokenHUD.html
- [SRCH-FOG] FogManager (v13) and the Fog Weaver package page, read through search
  results. https://foundryvtt.com/api/v13/classes/foundry.canvas.perception.FogManager.html
  and https://foundryvtt.com/packages/fog-weaver
- [REL-12] Release 12.321. https://foundryvtt.com/releases/12.321
- [REL-14] Release 14.359 and 14.353. https://foundryvtt.com/releases/14.359 and
  https://foundryvtt.com/releases/14.353
- [DND5E] `foundryvtt/dnd5e`, MIT, file names under `templates/chat/` and
  `templates/chat/parts/`. https://github.com/foundryvtt/dnd5e

Owlbear Rodeo:

- [OBR-ITEM] `owlbear-rodeo/sdk`, MIT, `src/types/items/Item.ts`. https://github.com/owlbear-rodeo/sdk
- [OBR-GRID] same repo, `src/types/Grid.ts`.
- [OBR-IMG] same repo, `src/types/items/ImageGrid.ts`.
- [OBR-PLR] same repo, `src/types/Player.ts`.
- [OBR-PERM] same repo, `src/types/Permission.ts`.
- [OBR-FOG] Fog docs and the 2.0 dev log, read through search results.
  https://docs.owlbear.rodeo/docs/fog/ and https://blog.owlbear.rodeo/owlbear-rodeo-2-0-dev-log-3/
- [OBR-REPOS] `owlbear-rodeo` GitHub organization: `dynamic-fog` is GPL-3.0.
  https://github.com/owlbear-rodeo/dynamic-fog

MapTool:

- [MT-ZONE] `RPTools/maptool`, AGPL-3.0, `src/main/java/net/rptools/maptool/model/Zone.java`
  on `develop`. https://github.com/RPTools/maptool
- [MT-EXP] same repo, `model/ExposedAreaMetaData.java`.
