# Design: Ironsworn Live Stat Tracking

**Date:** 2026-04-26  
**Status:** Approved

## Problem

During play the model announces stat changes ("take −2 health", "momentum now +6") but does not write them to `Character.md`. The player must manually update their Obsidian vault after every narrated change. This breaks flow and creates drift risk if the player misses an update.

## Approach

Prompt-only. No new Python code. Redesign `Character.md` to use Obsidian callout blocks with simple labeled lines, then add a `## Live stat tracking` section to `skills/ironsworn/SKILL.md` that instructs the model to call `Edit` on the file immediately after every stat change.

**Why not a CLI subcommand:** The added maintenance surface and coupling aren't worth it for this use case. The model performs reliably given locked format + explicit instructions. Momentum edge cases (debility interactions) are handled in the prompt.

## Character.md Format

### Stats (unchanged — never modified during play)

```markdown
## Stats

| Edge | Heart | Iron | Shadow | Wits |
|------|-------|------|--------|------|
| 1    | 2     | 1    | 2      | 3    |
```

### Resources — green `[!tip]` callout

```markdown
> [!tip] Resources
> Health: 4/5
> Spirit: 5/5
> Supply: 5/5
> Momentum: +5
> _Momentum bounds: max 10, reset +2_
```

Each line is uniquely prefixed `> ` — reliable single-line string match for Edit.  
Momentum bounds line is updated when debilities are marked.

### Debilities — yellow `[!warning]` callout

```markdown
> [!warning] Debilities
> - [ ] Wounded
> - [ ] Shaken
> - [ ] Unprepared
> - [ ] Encumbered
> - [ ] Maimed
> - [ ] Corrupted
> - [ ] Cursed
> - [ ] Tormented
```

Obsidian renders these as interactive checkboxes. LLM edits `[ ]` → `[x]`.  
On marking any debility, also update the Momentum bounds line (see tracking rules below).

### Vows — teal `[!abstract]` callout

```markdown
> [!abstract] Vows
> **Background Vow** (Dangerous, 10 boxes): 2/10
> _"I swear to find my nephew, or know his fate..."_
```

Progress is numeric only (`N/X`). Rank and box count on same line for model context.  
No visual block chars — avoids block-counting errors.

### Assets — purple `[!example]` callout

```markdown
> [!example] Assets
>
> **Hound — Bran** *(large grey wolfhound)*
> Bran Health: 3/4
> - [x] **Sharp:** When you Gather Information using Bran's senses, add +1 and take +1 momentum on a hit.
> - [ ] **Ferocious:** When you Strike or Clash alongside Bran and score a hit, inflict +1 harm or take +1 momentum.
> - [ ] **Loyal:** When you Endure Stress in the company of Bran, add +1.
>
> **Wayfinder**
> - [x] When you Undertake a Journey, take +1 momentum on a strong hit...
> - [ ] When you Secure an Advantage by scouting ahead, add +1 and take +1 momentum on a hit.
> - [ ] When you Swear an Iron Vow to guide someone, reroll any dice...
>
> **Slayer**
> - [x] When you Gather Information tracking a beast or horror, or Secure an Advantage readying for a fight against them, add +1 and take +1 momentum on a hit.
> - [ ] When you Swear an Iron Vow to slay a beast or horror, reroll any dice...
> - [ ] When you slay a beast or horror (at least formidable), take a trophy and choose one...
```

`> Bran Health: N/4` is uniquely matchable.  
Asset ability checkboxes use `[x]`/`[ ]` — Obsidian-clickable for manual advancement between sessions.

### Bonds — gray `[!quote]` callout

```markdown
> [!quote] Bonds
> - Mara — Ashveil; Cadoc's sister, Cian's mother
> - Dunmore circle — home community
> - Fen — fellow messenger; mutual road-debt
```

No in-session editing needed. Reference only.

### Experience (plain — no callout)

```markdown
## Experience
Unspent: 0 | Spent: 0
```

Only changes on Fulfill Your Vow. No callout needed.

## SKILL.md Addition

New section inserted after `## Interpreting outcomes`:

```markdown
## Live stat tracking

After **every** move that changes a resource, edit `<PLAYER_VAULT_PATH>/Character.md`
immediately — never defer to session end. Announce the new value inline as you narrate:
"Health drops to 3/5." or "Momentum now +6."

**What to edit:**

| What changed | Line to find and replace |
|---|---|
| Health | `> Health: N/5` |
| Spirit | `> Spirit: N/5` |
| Supply | `> Supply: N/5` |
| Momentum | `> Momentum: +N` or `> Momentum: -N` |
| Companion health | `> [Companion Name] Health: N/max` |
| Vow progress | `> **Vow Name** (Rank, X boxes): N/X` |
| Debility gained | `> - [ ] Wounded` → `> - [x] Wounded` |

**Bounds:** Read the max from the file (`N/max` format). Clamp after applying delta.
For momentum, the bound is on the `> _Momentum bounds:` line in the Resources callout.
Never go below −6 or above the stated max.

**Debility effect on momentum:** When you mark a debility `[x]`, reduce max momentum by 1
and reset by 1 (floor 0 for both). Update the `> _Momentum bounds:` line immediately.
If current momentum now exceeds the new max, reduce it to match.

**Progress tracks:** Rank determines step size when marking progress (Troublesome 3,
Dangerous 2, Formidable 1, Extreme 0.5, Epic 0.25 — always round to nearest box).
`Reach a Milestone` / `Mark Progress` triggers the edit. `Fulfill Your Vow` triggers
resolve, not just a mark.
```

## Files Changed

| File | Change |
|---|---|
| `skills/ironsworn/SKILL.md` | Add `## Live stat tracking` section after `## Interpreting outcomes` |
| `skills/ironsworn/character-template.md` | Full rewrite to callout format |
| `example-campaign/CLAUDE.md` | Remove "update character sheet at session end" from session procedures |

## One-Time Migration

Cadoc's sheet at `/home/jeff/rgp/claude/ironsworn-test1-playervault/Character.md` (note: path has typo `rgp` not `rpg` — pre-existing) must be rewritten to the callout format. This is outside the toolkit repo; no git history.

## Out of Scope

- `skills/ironsworn/moves.md` — no changes
- `skills/ironsworn/oracles.md` — no changes
- `skills/mythic-gme/` — unaffected
- Python CLI (`src/solo_roll/`) — no changes
- Test suite — no changes (markdown-only)
