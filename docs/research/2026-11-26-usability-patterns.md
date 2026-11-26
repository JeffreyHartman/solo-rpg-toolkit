# Usability patterns for the chat stream, cards, input, panels, and map

Date: 2026-11-26

Ticket: [Research: usability patterns for chat, map, and panels](https://github.com/JeffreyHartman/solo-rpg-toolkit/issues/24)

Map: [Phase 2 map: The table](https://github.com/JeffreyHartman/solo-rpg-toolkit/issues/40)

Question: which patterns from well-made AI chat apps, virtual tabletops, and solo RPG
apps fix the problems of the [first delve playtest](../playtests/2026-11-26-first-delve.md)?

## Method and limits

- Sources are public docs, design guides, and source code. Each claim has a source
  tag. The [Sources](#sources) section lists the links.
- The study did not log in to any site. It did not open any app.
- The Augur facts come from the [Augur study](https://github.com/JeffreyHartman/solo-rpg-toolkit/blob/research/augur-player-flows/docs/research/2026-11-26-augur-player-flows.md)
  on the `research/augur-player-flows` branch [AUGUR], and from its local screenshots
  (`s17`, `s71`, `s84`). The repo holds no screenshots of other apps.
- The Owlbear Rodeo docs site blocks automated reads. The fog claims for Owlbear Rodeo
  come from the search index excerpt of its fog page [OBR-FOG], from a first-party dev
  log [OBR-DEV3], and from the SDK source [OBR-SDK]. Treat the [OBR-FOG] claims as
  less certain.
- OpenAI has no help page for the Enter key that the study found. The study uses the
  AI Elements docs [AIE-INPUT] and the Foundry docs [FVTT-CHAT] for that pattern.
- The note lists patterns. It makes no decisions. The standing choices of map #40 stay
  in force: the chat stream is the roll log, cards have a cards-only filter, one
  markdown panel shows rules and records, and panels dock.

## Playtest problems

The playtest note lists these problems. The pattern sections refer to them by code.

| Code | Problem |
|---|---|
| P1 | The chat does not scroll to new output while the player is at the bottom. |
| P2 | The input is one line. The player cannot see a long message. |
| P3 | Turns have no separation. The player cannot see where a turn starts. |
| P4 | The chat panel is small. The player cannot resize it or move it. |
| P5 | The Referee writes agent notes ("my tools cannot add a light source") in the story text. |
| P6 | A rules citation is plain text. The player wants to click it and read the rule in a panel. |
| P7 | The Referee names an arch to the east. The map does not show it. |
| P8 | Roll results are hard to find later (from the Augur study: toasts do not persist). |

## Chat stream

### C1. Stick to the bottom, and let the reader break the stick

- **Where:** `use-stick-to-bottom` keeps a container at the newest content while
  content streams. The reader cancels the stick when they scroll up [STB]. The AI
  Elements `Conversation` component "automatically scrolls to the bottom" and shows a
  scroll button "when not at the bottom" [AIE-CONV]. Its props name a `StickToBottom`
  context, so it uses that library [AIE-CONV].
- **Details:** The library uses `ResizeObserver` to see content growth, and it also
  keeps the stick when content shrinks. It uses a spring animation, because a fixed
  duration does not suit text that streams in at different sizes [STB].
- **Fixes:** P1.
- **Note on the current code:** `ChatPanel.svelte` scrolls in an `$effect` that reads
  `game.chat.length` and `game.chat.at(-1)`. Streamed text goes into
  `entry.text += event.text` in `socket.svelte.ts`. The effect does not read
  `entry.text`, so a text delta does not run it. The effect also scrolls when the
  reader has scrolled up.

### C2. A "jump to latest" button when the reader is not at the bottom

- **Where:** AI Elements `ConversationScrollButton` [AIE-CONV]. Foundry's chat log
  has a `scrollBottom` method that also scrolls a popped-out chat window [FVTT-CHATLOG].
- **Fixes:** P1. The reader reads old turns and returns with one click.

### C3. One visual block per turn, with a sender mark

- **Where:** AI Elements `Message` takes a `from` prop (`user`, `assistant`, or
  `system`). User messages have a "secondary background". Assistant messages are
  "full-width" and flat [AIE-MSG]. Foundry shows each message with its speaker (the
  character or token), and a delete control on each message [FVTT-CHAT].
- **Fixes:** P3. The player message and the Referee turn have different shapes, so the
  start of each turn is clear.

### C4. Actions on the latest reply only

- **Where:** The AI Elements example shows Retry and Copy only on the latest assistant
  message [AIE-MSG].
- **Fixes:** P3 (less clutter in old turns).

### C5. A message type for out-of-character text

- **Where:** Foundry has `/ic`, `/ooc`, `/emote`, and `/whisper`. An out-of-character
  message shows "outlined in the player's color" [FVTT-CHAT]. A whisper goes only to
  the listed users [FVTT-CHAT].
- **Fixes:** P5. The engine can tag a Referee note as out-of-character, and the stream
  can draw it in a different style from story text.

### C6. Hidden reasoning behind a click

- **Where:** The Claude app shows an expandable "Thinking" section above the reply. It
  holds a "thought process summary". A timer shows while the model works [CLAUDE-THINK].
  The AI Elements `Reasoning` component opens "during streaming" and closes "when
  finished". Its trigger label can show the duration [AIE-REASON].
- **Fixes:** P5. Agent notes about the harness (for example a missing tool) go in a
  closed block. The player opens it only when they want to.
- **Note on the current code:** `ChatPanel.svelte` already renders an `ooc` entry as a
  closed `<details>` with the label "Out-of-character note".

### C7. The roll log is the chat stream, with a filter

- **Where:** Foundry keeps every roll as a chat message in one log. The GM can export
  the log to a text file [FVTT-CHAT]. Foundry has no core filter. The Custom Chat Tabs
  package adds a tab bar above the log: All (always present), Pinned, IC, OOC,
  Mechanics, Rolls, Scene, and Whispers [FVTT-TABS]. The Augur shows each roll as a toast that
  does not persist, and the journal does not record rolls [AUGUR].
- **Fixes:** P8. This matches the map #40 choice: every roll is a card in the stream,
  kept across sessions, with a cards-only filter.

## Cards

### K1. A collapsed roll that expands to show each die

- **Where:** Foundry shows a roll collapsed. A click on the roll shows each die result.
  A second click collapses it [FVTT-CHAT]. The Augur roll toast shows the dice faces,
  the result word ("Missed"), and a Push button (`s84`) [AUGUR].
- **Fixes:** P3, P8. The card shows the result first and the dice on demand.

### K2. Collapse the long text, keep the buttons

- **Where:** The dnd5e system for Foundry has a client setting "Collapse Item Cards in
  Chat". The card description is collapsed by default. The setting "does not affect the
  presence of the buttons on the chat card" [DND5E-SET].
- **Fixes:** P3. Long rule text does not push the story off the screen, and the card
  actions stay one click away.

### K3. A card that opens a source in a panel

- **Where:** Foundry Map Notes pin a journal page to a map. A click on the pin opens the
  page [FVTT-JOURNAL]. A GM can "Show Players" a journal page, which brings it "to the
  forefront of their screen" [FVTT-JOURNAL]. Foundry can pop a chat message out into
  its own window when the game system allows it [FVTT-CHAT].
- **Fixes:** P6. A citation on a card is a link. A click opens the cited rule in the
  markdown panel (the map #40 choice).

### K4. Pop out a card for quick reference

- **Where:** Foundry: right-click on a message, then "Pop Out Message" [FVTT-CHAT].
- **Fixes:** P8. A card that the player needs again (for example a light timer) stays
  on screen.

## Input

### I1. A text area that grows with its text, up to a limit

- **Where:** AI Elements `PromptInput`: the text area "adjusts height based on content",
  with a minimum and a maximum height [AIE-INPUT]. In CSS, `field-sizing: content` makes
  a `<textarea>` grow in height, then show a scrollbar at its height limit. MDN marks it
  "Baseline 2026, newly available" [MDN-FIELD]. MDN says: do not set a fixed `height`
  with it. Set `min-height` and `max-height` [MDN-FIELD].
- **Fixes:** P2.

### I2. Enter sends, Shift+Enter adds a line

- **Where:** AI Elements `PromptInput` [AIE-INPUT]. Foundry chat: "Pressing Enter will
  send a written message", and Shift+Enter adds a line [FVTT-CHAT].
- **Fixes:** P2.

### I3. Up arrow recalls the last message

- **Where:** Foundry chat [FVTT-CHAT].
- **Fixes:** P2 (a player can fix a typo and send again).

### I4. The send button shows the turn state

- **Where:** AI Elements `PromptInputSubmit` takes a `status` of `submitted`,
  `streaming`, or `error` and changes its icon [AIE-INPUT]. The Claude app shows a
  timer while the model thinks [CLAUDE-THINK].
- **Fixes:** P3. The player sees that a Referee turn is in progress and when it ends.

## Panels and docking

### D1. Each panel picks a dock: left, center, or right

- **Where:** The Augur: each panel has a layout button beside its close button, with
  Left Panel, Center Panel, and Right Panel (`s17`). Two panels can be open, one on each
  side, and the map stays visible between them (`s71`) [AUGUR].
- **Fixes:** P4. A simple dock choice, with no drag, gives the chat a larger place.

### D2. Pop a sidebar tab out into its own window

- **Where:** Foundry: every sidebar tab can render as a pop-out [FVTT-TAB]. A right-click
  on a tab opens the pop-out [FVTT-SIDEBAR11]. The sidebar tracks its open pop-outs
  [FVTT-SIDEBAR13].
- **Fixes:** P4. The player can move the chat to a free window.

### D3. A dock library with tabs, splits, floats, pop-outs, and a saved layout

- **Where:** dockview has tab groups, drag-and-drop docking, floating groups, pop-out
  windows, and layout serialization. The core package is plain TypeScript with zero
  dependencies and an MIT license [DOCKVIEW].
- **Fixes:** P4. Serialization gives the saved layout that #16 asks for.

### D4. One tree of all records

- **Where:** The Augur Browser panel is a tree of the journal, locations, and their
  children. "+" makes a new item. Drag and drop changes the order (`s71`) [AUGUR].
  Foundry keeps journal entries in a sidebar directory [FVTT-JOURNAL].
- **Fixes:** P6. The list of known maps and the vault records can share one tree, and a
  click opens the record in the markdown panel.

### D5. Panels collapse to a small handle

- **Where:** The Augur panels have a "<" button at the bottom that hides the panel body
  (`s17`, `s71`) [AUGUR].
- **Fixes:** P4. The player hides a panel and does not lose its place.

## Map

### M1. Door icons with a visible state

- **Where:** Foundry draws a door icon on the map. Players and GMs see it. A door is
  closed, open, locked, or secret. A closed door "blocks movement, sight, and sounds".
  A player clicks the icon to open or close the door. A locked door "plays a rattling
  sound instead of opening". Players never see a secret door icon [FVTT-WALLS].
- **Fixes:** P7. A known exit that is closed shows as a door icon. The player sees the
  arch before they open it.

### M2. Explored, unexplored, and visible are three states

- **Where:** Foundry Fog Exploration saves what each user has explored. An "Unexplored
  Color" tints unexplored areas, and an "Explored Color" tints explored areas. Areas
  that a token sees now have no tint [FVTT-SCENES]. Foundry v14 adds a shared fog mode:
  an area that one member sees is revealed for the whole group [FVTT-V14].
- **Fixes:** P7. The map tells "known but not here" apart from "here now".

### M3. Fog as shapes that the GM turns on and off

- **Where:** Owlbear Rodeo 2.0 fog uses "an infinite fog plane" and is "pixel
  accurate", so a fog shape has any shape. A GM turns a fog shape off to show what is
  below it [OBR-DEV3]. In single layer mode, fog shapes do not overlap, which makes it
  fast to fog rooms side by side. "Fill Fog" covers the rest of the map [OBR-FOG].
- **Fixes:** P7. This matches area-by-area reveal in `docs/fog-map.md`: one fog shape
  per area.

### M4. A fixed layer order

- **Where:** The Owlbear Rodeo SDK lists layers in this order: `MAP`, `GRID`,
  `DRAWING`, `PROP`, `MOUNT`, `CHARACTER`, `ATTACHMENT`, `NOTE`, `TEXT`, `RULER`, `FOG`,
  `POINTER`, `POST_PROCESS`, `CONTROL`, `POPOVER` [OBR-SDK]. The Augur Map Settings has
  layers with visible, locked, selectable, and order controls [AUGUR].
- **Fixes:** P7. Fog sits above tokens and notes, and controls (for example door icons)
  sit above fog.

### M5. One active map for all, with a separate viewed map

- **Where:** Foundry: "The same scene is active for all users." Each user can also view
  a different scene. A GM activates a scene and pulls all users to it. Players with a
  token on the scene start centered on their token [FVTT-SCENES]. The Augur center
  toolbar has a main-map button and a back button (`s71`) [AUGUR].
- **Fixes:** none in the playtest. It is an input for the active-map switch on the
  staircase (map #40 destination). The glossary term is Active map, not scene.

### M6. Notes pinned to the map

- **Where:** Foundry Map Notes. Visibility follows the permission of the journal entry
  [FVTT-JOURNAL].
- **Fixes:** P6. A pin on an area opens its record in the markdown panel.

## Inputs for the visual direction prototype (#49)

These are observations, not decisions.

- The scroll fault (P1) has a cause in the current code. The scroll effect does not
  read the streamed text, and it does not check whether the reader is at the bottom.
  Pattern C1 fixes both. The prototype needs a long streamed turn to show it.
- Every chat app that the study read gives the player turn and the AI turn different
  shapes (C3). The prototype can show one player block, one Referee block, and the
  cards between them.
- The hidden note (C5, C6) exists in the current code as a closed `<details>`. The
  prototype can show it next to the story text to judge how much it stands out.
- Cards in Foundry and dnd5e show the result first, and the detail on a click (K1, K2).
  The buttons stay visible when the detail is collapsed.
- A growing text area (I1) needs a `max-height`. With no limit, a long message pushes
  the stream up.
- The Augur keeps the map visible between two side panels (D1). The current harness
  floats panels over the map in fixed places. The prototype can compare both.
- A dock library (D3) gives a saved layout. A fixed left, center, right choice (D1)
  gives less, but it needs no drag code.
- Foundry draws doors as icons with four states (M1). The current `MapView.svelte` draws
  an exit as a circle, and it has no closed state.
- Foundry uses three fog states, and Owlbear Rodeo uses fog shapes (M2, M3). The
  prototype can show unexplored, explored, and current area in three tints.
- The Augur roll toast shows dice faces (`s84`). A dice graphic on a card is a choice
  for #3 and #49.

## Sources

| Tag | Source |
|---|---|
| AIE-CONV | AI Elements, Conversation: <https://elements.ai-sdk.dev/components/conversation> |
| AIE-INPUT | AI Elements, Prompt Input: <https://elements.ai-sdk.dev/components/prompt-input> |
| AIE-MSG | AI Elements, Message: <https://elements.ai-sdk.dev/components/message> |
| AIE-REASON | AI Elements, Reasoning: <https://elements.ai-sdk.dev/components/reasoning> |
| AUGUR | The Augur study, branch `research/augur-player-flows`: <https://github.com/JeffreyHartman/solo-rpg-toolkit/blob/research/augur-player-flows/docs/research/2026-11-26-augur-player-flows.md> |
| CLAUDE-THINK | Claude Help Center, extended thinking: <https://support.claude.com/en/articles/10574485-using-extended-thinking> |
| DND5E-SET | Foundry dnd5e system settings: <https://hackmd.io/@foundryvtt-dnd5e/SkjrEUTlK> |
| DOCKVIEW | dockview README: <https://github.com/mathuo/dockview> |
| FVTT-CHAT | Foundry VTT, Chat: <https://foundryvtt.com/article/chat/> |
| FVTT-CHATLOG | Foundry VTT API v12, ChatLog: <https://foundryvtt.com/api/v12/classes/client.ChatLog.html> |
| FVTT-JOURNAL | Foundry VTT, Journal: <https://foundryvtt.com/article/journal/> |
| FVTT-SCENES | Foundry VTT, Scenes: <https://foundryvtt.com/article/scenes/> |
| FVTT-SIDEBAR11 | Foundry VTT API v11, Sidebar: <https://foundryvtt.com/api/v11/classes/client.Sidebar.html> |
| FVTT-SIDEBAR13 | Foundry VTT API v13, Sidebar: <https://foundryvtt.com/api/v13/classes/foundry.applications.sidebar.Sidebar.html> |
| FVTT-TAB | Foundry VTT API, AbstractSidebarTab: <https://foundryvtt.com/api/classes/foundry.applications.sidebar.AbstractSidebarTab.html> |
| FVTT-TABS | Custom Chat Tabs package: <https://foundryvtt.com/packages/custom-chat-tabs> |
| FVTT-V14 | Foundry VTT release 14.359: <https://foundryvtt.com/releases/14.359> |
| FVTT-WALLS | Foundry VTT, Walls: <https://foundryvtt.com/article/walls/> |
| MDN-FIELD | MDN, `field-sizing`: <https://developer.mozilla.org/en-US/docs/Web/CSS/field-sizing> |
| OBR-DEV3 | Owlbear Rodeo 2.0 Dev Log 3: <https://blog.owlbear.rodeo/owlbear-rodeo-2-0-dev-log-3/> |
| OBR-FOG | Owlbear Rodeo docs, Fog (search index excerpt only): <https://docs.owlbear.rodeo/docs/fog/> |
| OBR-SDK | Owlbear Rodeo SDK, `Item.ts`: <https://github.com/owlbear-rodeo/sdk/blob/main/src/types/items/Item.ts> |
| STB | use-stick-to-bottom README: <https://github.com/stackblitz-labs/use-stick-to-bottom> |
