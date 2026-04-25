# Meaning Tables — Customization

Default usage (`solo-roll meaning-pair`, JSON return shape, interpretation guidance) lives in `SKILL.md`. This file documents how to swap in alternative tables.

## Defaults

`solo-roll meaning-pair` reads `action1` and `descriptor1` — d100 word lists shipped with the toolkit, compatible with Mythic GME's meaning system.

## Using Mythic 2e's own tables

If you have the Mythic GME 2e book, populate two files from it:

- `data/tables/mythic/actions.json` — Meaning Tables: Actions (100 entries)
- `data/tables/mythic/descriptions.json` — Meaning Tables: Descriptions (100 entries)

Same JSON schema as `data/tables/action1.json`. Then call:

```bash
solo-roll meaning-pair --tables mythic/actions,mythic/descriptions
```

## Specialized tables

Mythic 2e includes themed meaning tables (Adventure, Combat, Alien, Fantasy, etc.). Add as `data/tables/mythic/meaning-combat.json`, etc. and call with:

```bash
solo-roll meaning-pair --tables mythic/meaning-combat,mythic/meaning-combat-desc
```
