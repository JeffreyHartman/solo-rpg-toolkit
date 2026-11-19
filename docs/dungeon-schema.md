# The `dungeon/` contract

A campaign's `dungeon/` directory is the only module-specific content the engine
needs. Everything else in an OSE campaign folder is reusable as-is.

There is no generic PDF-to-rooms converter and there will not be one. Every
publisher lays out a page differently: column counts, whether a designer aside is
a boxed callout or an indent, where the stat blocks live, whether the room key
runs to the last page. Writing one converter per module is an afternoon. What is
worth standardising is the output.

So: per module, write a conversion script against this schema. The engine then
works without modification. `templates/ose/tools/extract_prose.py` dumps any page
range of a multi-column PDF in reading order and is the usual starting point.

## Layout

    dungeon/
    ├── index.json              room number to file lookup
    ├── 00-running-the-tomb.md  the module's front matter, optional
    ├── level-1/
    │   ├── 00-overview.md      level description and zones
    │   └── 01-entrance-hall.md one file per keyed room
    ├── monsters/
    │   └── basilisk.md         one file per creature
    └── map/
        ├── map-05.png          rendered level maps
        ├── exits.json          optional: per-area shape and exits, from the map
        ├── crops/7.png         optional: unfogged crop per area id
        └── build/              optional: the scripts that built the fog map

`exits.json`, `crops/` and `build/` come from the fog-map build in
`docs/fog-map.md`. The referee reads `exits.json` whenever it exists, because
room text often leaves out an exit the map shows.

Room files are named `<zero-padded number>-<slugged name>.md`. The `00-` prefix
is reserved for a level overview, so room numbering starts at 01.

## Room file

```markdown
---
room: 2
name: Guard Tombs
level: 1
pdf_page: 6
dimensions: "1x1 – 10'x10'x8'"
sensory: "Smells like dust, old wood, very faint acid"
monsters: [monsters/skeletons.md]
exits: []
---

# 2: Guard Tombs

The key's own words, verbatim, reflowed into paragraphs. Never paraphrased.

## Designer notes

The author's commentary on how the room is meant to play, if the module has any.
Kept separate so the referee does not narrate it.

## Referee summary

1x1 – 10'x10'x8'

- Terse sensory and contents lines, if the module ships a referee summary.
```

Required frontmatter: `room`, `name`, `level`. Everything else is optional, but
`dimensions` earns its place: the player is drawing the map from the referee's
description, and a referee with no measurement will invent one.

`monsters` is a list of paths relative to `dungeon/`. Modules cite creatures by
print page ("the Basilisk (pg. 18)"), which a referee holding one room file
cannot follow, so the conversion script resolves those to paths.

## Level overview

```markdown
---
level: 3
name: The Lower Tombs
rooms: 22-52
wandering_table: ose/wandering-level-3
wandering_interval_turns: 3
---
```

`wandering_table` names a table in `data/tables/`. When the party changes level,
the referee copies these two fields into the `wandering` block of
`state/clock.json` as:

```json
"wandering": {"table": "ose/wandering-level-3", "interval": 3}
```

`solo-roll turn` reads `table` and `interval`, plus optional `chance` (default 1)
and `die` (default 6). It also accepts `wandering_table` and
`wandering_interval_turns` under their overview names, and exits with an error
when no table is given.

## Monster file

```markdown
---
name: "Basilisk"
pdf_page: 21
found_in: "38: BASILISK HALL"
stats: "as a wyrm or dinosaur"
hit_dice: "7"
armor: "as plate"
move: "1.5x normal"
morale: "8"
damage: "see Attacks"
---

# Basilisk

- **Found In:** 38: BASILISK HALL
- ... the stat line as bullets, then the behaviour text verbatim.
```

`morale` is what `solo-roll check morale --target` takes. `hit_dice` and `damage`
are quoted strings, not numbers, because modules write things like "2 (or 3 if
Sparamantur)" and "1d6. If prolonged contact, 3d6".

## index.json

```json
{"2": {"name": "Guard Tombs", "level": 1, "file": "level-1/02-guard-tombs.md"}}
```

The referee subagent reads this first to turn a room number into a path.

## Fidelity rules for a conversion script

- The key's words, verbatim. Reflow hard-wrapped lines into paragraphs and repair
  hyphenation, but never paraphrase, summarise, or tidy.
- Separate designer commentary from room text. If the referee narrates "Lessons:
  there are deadly traps", the game is over.
- Assert the room count against the module's own key before writing anything. A
  garbled key poisons everything downstream, and it is invisible in play until
  the referee describes a room that does not exist.
- Check the last room and the last room of each level. Both are where a range
  that runs too far swallows the next section.
