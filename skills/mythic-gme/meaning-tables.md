# Meaning Tables

Two d100 tables — **Action** and **Description** — rolled together to produce an evocative word pair that the agent interprets in context.

> **This file is intentionally not populated.** The Meaning Tables (Actions Table 1 and Descriptions Table 1 in the Mythic GME 2e book, plus the specialized Meaning Tables) are copyrighted content. Populate them from your copy of the book here, or point this skill at your own files.

## Interim fallback: use Ironsworn oracles

If the `ironsworn` skill is also loaded and these tables are not yet populated, the agent should use Ironsworn's **Action + Theme** oracle as a functional substitute (see `ironsworn/oracles.md`). It's not a perfect one-for-one with Mythic's Meaning Tables, but it serves the same role — a random word pair the narrator interprets into meaning.

## Format for populating

```
## Action (d100)
1. [Word]
2. [Word]
...
100. [Word]

## Description (d100)
1. [Word]
2. [Word]
...
100. [Word]
```

## Specialized Meaning Tables

Mythic 2e includes additional themed meaning tables (Adventure, Combat, Alien, Fantasy, etc.) for specialized flavor. If you want them here, add them as `meaning-tables-combat.md`, `meaning-tables-fantasy.md`, etc. and reference them in `SKILL.md` so the agent knows when to use which.

## How the agent should use these

1. Roll 1d100 on Action, 1d100 on Description.
2. State both words out loud: *"Action: Advance. Description: Old."*
3. Interpret the pair in the current fictional context. First natural reading wins.
4. If the pair is genuinely nonsensical in context, re-interpret broadly before re-rolling — Mythic explicitly encourages stretching interpretation. Re-rolls are allowed but should be rare.
