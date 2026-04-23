# Meaning Tables

Two tables — **Action** and **Description** — rolled together to produce a word pair the agent interprets in context.

## Command

```bash
solo-roll meaning-pair
```

Returns:
```json
{
  "action":      {"table": "action1", "roll": 87, "result": "Succeed"},
  "description": {"table": "descriptor1", "roll": 100, "result": "Yieldingly"}
}
```

Interpret the pair (`action` + `description`) in current fictional context. First natural reading wins. Re-interpret broadly before re-rolling — Mythic explicitly encourages stretching. Re-rolls are rare.

## Default tables

`solo-roll meaning-pair` uses the `action1` and `descriptor1` tables by default. These are d100 word lists included with this toolkit (100 action words, 100 descriptor words). They're compatible with Mythic GME's meaning system.

## Using Mythic 2e's own tables

If you have the Mythic GME 2e book, you can populate two files from it:
- `data/tables/mythic/actions.json` — Meaning Tables: Actions (100 entries)
- `data/tables/mythic/descriptions.json` — Meaning Tables: Descriptions (100 entries)

Use the same JSON schema as `data/tables/action1.json`. Then call:

```bash
solo-roll meaning-pair --tables mythic/actions,mythic/descriptions
```

## Specialized tables

Mythic 2e includes themed meaning tables (Adventure, Combat, Alien, Fantasy, etc.). Add them as `data/tables/mythic/meaning-combat.json`, etc. and call with `--tables mythic/meaning-combat,mythic/meaning-combat-desc`.
