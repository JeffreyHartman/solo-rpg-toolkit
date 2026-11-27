# Wakes decide when the Referee takes a turn

A direct action (ADR 0003) gets no Referee turn unless its events include a wake: an event that the engine, a procedure, or a trigger emits with a reason when the world must answer. For example, a move into an unexplored area wakes the Referee, and a wandering-monster check wakes it only when the roll finds a monster. We chose events over a "Referee follows" flag on each procedure because the result decides, not the procedure: a move to an empty known area and a move to an area with a goblin are the same command. We chose them over a button for each action because the player would then decide the pace of the world.

## Consequences

- The server sets an `actor` on each command: `player` for the UI, `referee` for a Referee tool. The client cannot set it. The engine refuses a player command that changes anything outside the party, and refuses a procedure whose `starters` do not include the actor.
- Each procedure declares its `starters`: `player`, `referee`, or both. The default is both.
- The engine owns the party token move. It checks the connection, the active map, and any block that the ruleset adds. A ruleset adds the cost of a move through the `moved` trigger. A move into an unexplored area is a direct action. The engine reveals the area and emits a wake. A move into an area that holds a token that is not a party token also emits a wake.
- A direct action with no wake shows only its mechanics card. The Referee does not narrate it. The player can type free text or click "Ask the Referee" at any time.
- Each field of the character schema has one edit kind: `free` (name, description, notes; logged, no card), `correction` (scores, HP, items, gold; a "Player edit" card with the old value, the new value, and an optional reason), or `derived` (calculated by the ruleset; nobody edits it). No field is locked to procedures only.
- The state holds a cursor at the last event that the Referee saw. At the start of each Referee turn, the harness puts a digest of the events after the cursor before the player input, then moves the cursor. If a session ends with unseen events, the first turn of the next session gets the digest after the recap.
- The engine refuses every direct action while a Referee turn runs, and the UI disables them. A change in the middle of a turn can make the narration or a Referee tool call act on old state.
