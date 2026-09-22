---
name: journaler
description: Write and update the player vault. Use at session end, and whenever the party meets someone, learns a place's name, or opens a question worth tracking. Covers the file formats for Session Log, People, Places, Threads, and Map.
---

# Journaler

Everything written here is what the player knows. Never write a fact the party
has not established in play, even when the key says otherwise.

Vault root is `./playervault/`. That folder, not the campaign root, is what opens
in Obsidian.

## Session Log/Session NNN.md

Zero-padded sequential, not dated filenames. The date goes in frontmatter.

```markdown
---
played: 2026-09-21
turns: 14-31
---

# Session 003

Narrative account of the delve, in the player's own frame. What they tried, what
it cost, what they learned.

## Turn log

- Turn 14: level 1, room 12, light 3 turns remaining
```

The Stop hook appends the turn log lines. Write the narrative above them.

## People/<Name>.md

Write the file before the NPC speaks, not after.

```markdown
---
name: Gribbit
kind: fungus goblin
apparent_age: hard to tell, small and quick
met: Session 003, room 47
disposition: Neutral, uncertain (reaction 7)
---

# Gribbit

What it looks like. What it wants. What it has said, in its own words.
```

Re-read this file before writing that NPC's dialogue again. An NPC voiced from
memory drifts.

## Places/<Name>.md

One file per named location the party can describe, not per room number. Record
what they saw, with dimensions if they measured.

## Threads/<Question>.md

An open question the party is chasing. Required sections:

```markdown
## What we know
## What we suspect
## Progression
## Resolution
```

Close a thread by filling Resolution. Do not delete it.

## Map.md

One line per room entered: number, name as the party knows it, dimensions, exits
observed. Append only. Never list an exit the party has not perceived, and never
correct the player's understanding from the key.

## Links

Use `[[wikilinks]]` between vault files. Obsidian resolves them.
