# [CAMPAIGN NAME]

A solo Old-School Essentials game with Claude Code as referee. Open this folder
in Claude Code and play. Open `playervault/` in Obsidian, never the root: the
root holds the dungeon key, and Obsidian search would spoil it.

## Before the first session

1. Convert the module into `dungeon/` against the schema in the toolkit's
   `docs/dungeon-schema.md`. Write one conversion script per module;
   `tools/extract_prose.py` dumps a PDF page range in reading order.
2. Fill in `module.md`: levels, room ranges, wandering tables, tone.
3. Add the module's own tables to `data/tables/`, such as its wandering monster
   table.
4. Roll the party, 3d6 down the line. Fill `playervault/Character.md` and
   `state/party.json`, and set marching order.
5. Set `state/clock.json` to the starting level and the party's light.

## How it is built

- `module.md` is the only file that knows which adventure this is.
- `dungeon/` is the key. A `PreToolUse` hook blocks the main session from reading
  it. The `referee` subagent reads it and returns only what the party perceives.
- `rules/` is the OSE procedure, module-independent.
- `state/clock.json` and `state/party.json` are injected into every message by a
  `UserPromptSubmit` hook, so the referee cannot lose the clock.
- `solo-roll turn` runs the whole dungeon turn in one call: clock, light, rest,
  wandering check, and on a hit the encounter, distance, surprise, and reaction.
- `.claude/output-styles/referee.md` sets the voice, with
  `keep-coding-instructions: false` so the engineering system prompt is gone.
