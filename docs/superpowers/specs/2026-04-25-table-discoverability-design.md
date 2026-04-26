# Table Discoverability — Design

**Status:** Draft for review
**Date:** 2026-04-25
**Author:** Jeffrey Hartman (with Claude)

## Problem

When the player asks Claude to roll on themed tables beyond the default `action1`/`descriptor1` meaning-pair (e.g., "roll on the creature elements table to expand the quest seed"), Claude has no in-band way to discover what tables exist. Symptoms observed in actual play:

- Claude invents flags that don't exist (`solo-roll table --list`).
- Claude falls back to `find` + `grep` over the repo to enumerate JSON files.
- Even after finding files, Claude has no description metadata — it must guess intent from filename alone.
- Skill prompts don't acknowledge that tables beyond the meaning pair exist or how to combine them.

The discovery instinct is correct. The toolkit gives it nothing to work with.

## Goals

1. A first-class `solo-roll list` subcommand that enumerates available tables with descriptive metadata.
2. A `description` field on each table JSON, treated as the canonical one-line summary of what the table covers.
3. A short "Available tables" section in the `mythic-gme` skill that orients Claude (and humans) without duplicating per-table descriptions.
4. Skill instructions that extend Interpretation discipline to arbitrary table rolls, not just `meaning-pair`.
5. Stop the `ironsworn` skill from auto-substituting Mythic mechanics for Ironsworn-native ones — Mythic stays opt-in.
6. Generalize the `ironsworn-truths` skill's Mythic option so the player can direct it at either a truth or a quest seed.

## Non-goals

- Quickset listing (separate `solo-roll quickset --list` is out of scope; quicksets are fewer and more discoverable already).
- Keyword search / fuzzy match across table contents.
- JSON schema versioning.
- Reworking `display_name` semantics or the dual `entries`/`ranges` schema.
- Adding descriptions to fate-chart or quickset JSON.

## Architecture

### 1. Schema change: optional `description` field

`data/tables/<name>.json` gains an optional `description` field of type `string`. Existing fields untouched.

```json
{
  "name": "elements/creature",
  "display_name": "Mythic 2e Creature Description",
  "description": "Single-word creature traits (Loud, Ancient, Many-eyed). Combine with creatureabilities for monster generation.",
  "dice": "d100",
  "source": "Mythic GME 2e",
  "entries": ["...", "..."]
}
```

`src/solo_roll/tables.py::_validate` accepts:
- `description` absent → OK
- `description` present and is a string → OK
- `description` present and not a string → `TableDataError`

No required-ness. Backfill is a one-time chore but new tables are expected to ship with descriptions; "Adding a table" docs in `CLAUDE.md` will be updated to call this out.

### 2. CLI: `solo-roll list`

New subcommand registered in `cli.py::main` next to `table`/`fate-check`/`meaning-pair`/`quickset`/`roll`.

**Signature:**

```
solo-roll list [PREFIX] [--json] [--data DIR]
```

- `PREFIX` (positional, optional): restrict output to table names starting with `<prefix>`. Examples: `solo-roll list elements`, `solo-roll list mythic`. No prefix → all tables. Trailing slash optional (`elements` and `elements/` equivalent).
- `--json`: emit machine-readable JSON instead of grouped text.
- `--data DIR`: same semantics as other subcommands.

**Discovery rule:** walk `<data_dir>/tables/` recursively, collect every `*.json`, derive name from path relative to `<data_dir>/tables/` minus extension. Files that fail to parse or fail validation are skipped with a single line on stderr (`warning: skipped <path>: <reason>`); exit code stays 0 if at least one table was readable.

**Default output (grouped human-readable):**

```
(top-level)
  action1               d100  100 entries  Mythic 2e Meaning — Actions       — Verb word list for meaning pairs.
  descriptor1           d100  100 entries  Mythic 2e Meaning — Descriptors   — Adverb word list for meaning pairs.
  ...

elements/
  creature              d100  100 entries  Mythic 2e Creature Description    — Single-word creature traits (Loud, ...).
  creatureabilities     d100  100 entries  Mythic 2e Creature Abilities      — Special powers/traits (Element, Flight, ...).
  ...

mythic/
  event-focus           d100  100 entries  Mythic 2e Event Focus             — 12-category event lookup.
```

- Top-level group rendered as `(top-level)` so its absence of prefix is unambiguous.
- Within each group, alpha order.
- Column widths derived from longest in current output (per group). Plain spaces, no Unicode box drawing.
- `entry_count` derives from `len(entries)` for flat tables and `sum(max - min + 1 for ranges)` for ranged tables.
- If `description` absent: render `—` (em dash) in description column.

**`--json` output:**

```json
{
  "tables": [
    {
      "name": "action1",
      "display_name": "Mythic 2e Meaning — Actions",
      "dice": "d100",
      "description": "Verb word list for meaning pairs.",
      "entry_count": 100
    },
    ...
  ]
}
```

- Tables sorted: top-level first, then directories alpha, then alpha within each. Single flat array, agent can group from the `name` field (presence of `/`).
- `description` field always present in output; value is `null` if absent in source JSON.

**Errors:**
- Missing data dir → `error: data dir not found: <path>` on stderr, exit 1.
- Missing `tables/` subdir → empty list, exit 0 (consistent with "no tables yet").
- Empty `tables/` tree → empty list, exit 0.
- Prefix matches nothing → empty list, exit 0.

**No `dice` filter, no `min/max entries` filter, no search by `display_name`.** YAGNI; can add later if real use surfaces.

### 3. Backfill descriptions

One-time pass writing `description` into every existing table JSON:

- `data/tables/action1.json`, `action2.json`, `descriptor1.json`, `descriptor2.json` — meaning-pair word lists.
- `data/tables/elements/*.json` — 47 themed tables. Descriptions derived from existing `display_name` + Mythic 2e domain knowledge (e.g., `creature` = "single-word creature traits", `crypticmessage` = "fragments and oblique phrasings for omens, dreams, or coded notes").
- `data/tables/mythic/event-focus.json` — already-known event-focus categories.

Tables whose meaning is unclear from `display_name` alone get a description that names the Mythic 2e source section + a brief contextualization. None should be left blank.

This backfill ships in the same PR as the schema and CLI changes so the `solo-roll list` command is useful from day one.

### 4. `mythic-gme/SKILL.md` additions

Two new sections inserted after the existing **Detail Check / Meaning Pair** section, before **Interpretation discipline**.

#### 4a. "Available tables" section

Short prose orientation. Rough draft:

> ## Available tables
>
> The toolkit ships a library of Mythic 2e themed tables in addition to the default meaning pair. Top-level tables (`action1`, `descriptor1`) are the canonical meaning-pair word lists. The `elements/` directory holds 47 themed lookup tables for creatures, civilizations, locations, magic, omens, and more. The `mythic/` directory holds GME mechanics tables (event focus, etc.).
>
> **To discover what's available, run `solo-roll list`** (or `solo-roll list <prefix>` to scope, e.g., `solo-roll list elements`). Each entry shows dice, entry count, display name, and a one-line description.
>
> **Useful combinations:**
> - `elements/creature` + `elements/creatureabilities` — flesh out a monster or horror.
> - `elements/city` + `elements/civilization` — generate a settlement with culture.
> - `elements/dungeon` + `elements/dungeontrap` — populate a delve with hazards.
> - `elements/characterappearance` + `elements/characterpersonality` — shape an NPC quickly.
>
> These are starting points; combine any tables that fit the moment.

#### 4b. "Using arbitrary tables" section

Extends Interpretation discipline beyond `meaning-pair`. Rough draft:

> ## Using arbitrary tables
>
> When the player asks for color or detail beyond a single meaning pair (creature description, location flavor, magic-item quirks), find candidate tables with `solo-roll list [prefix]`, then roll each chosen table:
>
> ```bash
> solo-roll table elements/creature
> solo-roll table elements/creatureabilities
> ```
>
> **Apply the same Interpretation discipline as meaning-pair:**
> - Roll first, interpret after.
> - Announce every result verbatim — quote the words from each JSON output exactly.
> - Every rolled word counts. Don't silently drop a result because it's awkward; dissonance is a feature.
> - If a result is genuinely forced, name the word and the reason explicitly before discarding.
>
> The toolkit's discipline rules are not specific to `meaning-pair`. They apply any time the dice produce words you must integrate into the fiction.

### 5. `ironsworn/SKILL.md` changes

**Replace lines 40-48** (the entire "When Mythic GME skill is also loaded" section) with:

> ## When Mythic GME skill is also loaded
>
> If `mythic-gme` is loaded, do **NOT** substitute its mechanics for Ironsworn's native ones. Mythic mechanics (Scene Test, Fate Check, Event Focus, Chaos Factor) are opt-in tools the player invokes explicitly — for example, "run a scene test", "roll a fate check on whether the guard noticed me", "use Mythic for this event". Default behavior stays Ironsworn-native: Ask the Oracle for yes/no, Ironsworn oracles for inspiration, Ironsworn pacing. Do not surface Mythic mechanics unprompted, and do not pre-empt an Ironsworn move with a Mythic equivalent.

**Remove line 71** ("If Mythic is loaded, run a Scene Test first") from the "Scene framing" section. The numbered steps renumber accordingly (1, 2, 3 instead of 1, 2, 3, 4).

### 6. `ironsworn-truths/SKILL.md` change

**Replace the "Mythic 2e graceful coupling" section (lines 129-135)** with:

> ## Mythic 2e graceful coupling
>
> If `mythic-gme` skill is loaded — detected by either (a) `mythic-gme` appearing in the active skills list shown to you by the harness, (b) a prior invocation of `solo-roll meaning-pair` or `solo-roll fate-check` in this session, or (c) the campaign `CLAUDE.md` listing it as an active skill — include this option in the per-truth menu:
>
> > **Mythic meaning pair (player-directed)** — invoke `solo-roll meaning-pair` once. Before rolling, ask the player which target: a fresh truth/option, a quest seed for the chosen option, or both. Announce both words verbatim and apply the [Interpretation discipline](../mythic-gme/SKILL.md#interpretation-discipline) from the `mythic-gme` skill — roll one pair first, use both words (dissonance is a feature), and only roll a second pair or discard a word *explicitly* if the first reading is genuinely forced.
>
> If `mythic-gme` is not loaded, do **not** mention this option. Never auto-load it. Never substitute it for the standard A/B/C/Roll/Fresh/Riff/Freeform paths unless the player asks.

The per-truth menu in step 2 of the per-truth loop (lines 44-49) gains a sixth bullet referencing this section, but the canonical wording lives in this graceful-coupling block to avoid drift.

## Testing

### `tests/test_tables.py`

Three new cases:
- `description` absent → loader OK.
- `description` present and string → loader OK, value preserved.
- `description` present and non-string (int, list) → `TableDataError`.

### `tests/test_cli.py`

Four new cases for `solo-roll list`:
- No prefix, no `--json`: human output groups, sorted, every shipped table appears.
- Prefix `elements`: only elements/* tables appear, none from top-level or `mythic/`.
- `--json`: parses as JSON, has `tables` array, each entry has all five fields. Test fixture deliberately includes one table without a `description` field to confirm `null` rendering; all in-tree tables ship with descriptions, so a no-fixture run produces no nulls.
- Custom `--data` pointing at `tmp_path` with two synthetic tables: confirms data-dir override works.

Plus one degenerate case: missing `tables/` subdir → empty list, exit 0.

### No skill-content tests

Skill markdown is text. Manual review on the diff covers it.

## Migration / rollout

Single PR. Order of changes within the PR matters for review but not for runtime:

1. `tables.py` schema validator update + tests.
2. Backfill `description` into all existing table JSON files.
3. `cli.py` `_cmd_list` + parser registration + tests.
4. `CLAUDE.md` "Adding a table" section updated to require `description`.
5. `mythic-gme/SKILL.md` two new sections.
6. `ironsworn/SKILL.md` Mythic-coupling rewrite + line 71 removal.
7. `ironsworn-truths/SKILL.md` Mythic-coupling refinement.

No data migration in users' campaign vaults. No CLI flag removal. Backwards compatible.

## Open questions

None at design time. Resolve during implementation if surfaced.

## Out of scope (future work)

- `solo-roll quickset --list` if quickset count grows.
- Keyword search across table contents (`solo-roll list --grep horror`).
- Promoting `description` to required (after all in-tree tables have one, can tighten validator).
- `solo-roll table` rendering `description` in output JSON for parity.
