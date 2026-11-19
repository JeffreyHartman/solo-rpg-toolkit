---
name: ironsworn-truths
description: Use when starting a new Ironsworn campaign and the player wants to lock in the 11 setting truths (Old World, Iron, Legacies, Communities, Leaders, Defense, Mysticism, Religion, Firstborn, Beasts, Horrors). Activates on phrases like "set up truths", "session zero", "establish my Ironsworn world", or when the ironsworn skill notices truths are not yet locked. Walks the player through each truth one at a time, supports picking a stock option, rolling d100, generating fresh options, or shaping the player's own world idea, and saves locked answers to the player's Obsidian vault plus a summary block in the campaign CLAUDE.md.
---

# Ironsworn Truths Skill

You walk the player through locking in the 11 Ironsworn setting truths. Each truth becomes a load-bearing fact for the rest of the campaign — take the time to make answers feel right.

## Reference data

`truths.md` (alongside this file) holds all 11 truths with their three weighted stock options and quest seeds. Read it on demand for the truth currently being decided. Do **not** dump the whole file into chat.

## Path resolution

1. The vault is `./playervault/` in the campaign folder (the current working directory).
2. Truth files live at `./playervault/Lore/Truths/<slug>.md`. Slugs use lowercase hyphenated names: `old-world.md`, `iron.md`, `legacies.md`, `communities.md`, `leaders.md`, `defense.md`, `mysticism.md`, `religion.md`, `firstborn.md`, `beasts.md`, `horrors.md`.
3. Create `./playervault/Lore/Truths/` on the first lock if it does not exist. If `./playervault/` itself is missing, stop and tell the player the campaign was not scaffolded with `solo-campaign`.

## Activation guard (always run first)

When the skill is invoked:

1. List the 11 truth slugs and check which files exist with frontmatter `locked: true`.
2. Report progress to the player: `"X of 11 truths locked."` Name the locked ones.
3. Offer choices:
   - Continue with the first unlocked truth.
   - Jump to a specific truth by name.
   - Revisit a locked truth (edit / replace / view).
   - Exit.

## Per-truth loop

For each truth the player wants to work on:

1. Read the matching `## <Truth Name>` section from `truths.md`. Present the player with:
   - The truth's name and a one-line summary of what this truth shapes (from your own knowledge of Ironsworn — this single line is the only original prose you write here).
   - The three stock options labelled A / B / C with their d100 ranges and option text **quoted verbatim from `truths.md`**. Do not paraphrase, abbreviate, compress, or "tighten" the option text. Copy it character-for-character.
   - The quest seed for each option, also **verbatim from `truths.md`**. Do not summarize the quest seed. If presenting all three quest seeds at once would be too long, show the option text for all three and offer to expand quest seeds on request — but when you do show a quest seed, show it whole.

   **Why verbatim:** the option text is the canonical Ironsworn truth (Shawn Tomkin, CC-BY-4.0) and the player is choosing between *those exact options*. Paraphrase silently changes what they are picking. A "grateful threat" rewritten as "a threat" is the same failure mode as silently dropping a meaning-pair word — convenient for the LLM, lossy for the player.

2. Offer the player these paths:
   - **A / B / C** — pick a stock option as written.
   - **Roll d100** — invoke `solo-roll roll 1d100` and announce which option the result lands in.
   - **Fresh options** — generate three new options grounded in Ironsworn's tone (low fantasy, iron-age, harsh, mythic). Show them with the same shape as the stock options.
   - **Riff on player idea** — the player offers a seed (e.g., "iron is alive and resentful"); you reflect it back as a polished one-paragraph option and an optional quest seed.
   - **Freeform** — the player writes their own answer in prose; you only help with phrasing.
   - **Mythic meaning pair (player-directed)** — *only when `mythic-gme` is loaded*. See "[Mythic 2e graceful coupling](#mythic-2e-graceful-coupling)" below for the full procedure (player picks target: fresh truth, quest seed, or both).

3. **Iterate until lock.** Do not write to disk after one turn. The player may want several rounds of refinement, mixing fresh-options with riffs. Keep the conversation in this loop until they say something equivalent to "lock it."

4. Before locking, ask:
   - Whether the quest seed should be saved (some players opt out at session zero).
   - Whether they want to add freeform notes to the file (campaign-specific lore that does not fit the option text).

5. **Lock procedure** — when the player confirms:
   - Write `./playervault/Lore/Truths/<slug>.md` with the schema below. Overwrite if the file already exists.
   - Regenerate the campaign `CLAUDE.md` summary block (see "Summary block" below).
   - Confirm: `"Locked: <Truth Name>. Y of 11 truths locked."`

6. Ask whether to continue with the next unlocked truth or stop for now.

### Per-truth output schema

```markdown
---
locked: true
truth: <slug>           # e.g. old-world, iron, legacies — matches the filename without `.md`
source: classic/truths/<datasworn_id>   # e.g. classic/truths/old_world (underscores, not hyphens — matches the upstream Datasworn id)
chosen_option: <A|B|C|custom>
---

# <Truth Name>

<one-paragraph locked answer in the player's voice>

## Quest seed

<quest seed prose, or omit this entire section if the player opted out>

## Notes

<freeform notes, or omit this entire section if empty>
```

`chosen_option` is `A`, `B`, or `C` if the answer is the stock option text verbatim; `custom` otherwise (rolled-and-rewritten, riff, freeform, or fresh option).

## Summary block in campaign `CLAUDE.md`

Maintain a single fenced block at the end of `<campaign>/CLAUDE.md`. The block always lists all 11 truths in book order — unlocked ones render as `_(not yet locked)_`.

```markdown
<!-- BEGIN: ironsworn-truths-summary -->
## Setting Truths

- **The Old World**: <one-line locked summary>
- **Iron**: _(not yet locked)_
- **Legacies**: <one-line locked summary>
- **Communities**: _(not yet locked)_
- **Leaders**: _(not yet locked)_
- **Defense**: _(not yet locked)_
- **Mysticism**: _(not yet locked)_
- **Religion**: _(not yet locked)_
- **Firstborn**: _(not yet locked)_
- **Beasts**: _(not yet locked)_
- **Horrors**: _(not yet locked)_

(Full prose: `<vault>/Lore/Truths/`. Re-run `ironsworn-truths` skill to revise.)
<!-- END: ironsworn-truths-summary -->
```

**Update procedure** on every lock:
1. Re-read all 11 truth files in the vault. For each locked file, derive a one-line summary (≤ 100 chars): take the text before the first period or the first paragraph break, whichever comes first. If neither produces a summary that fits ≤ 100 chars, ask the player: "Give me a one-line summary of this truth for the campaign CLAUDE.md."
2. Search `<campaign>/CLAUDE.md` for `<!-- BEGIN: ironsworn-truths-summary -->` ... `<!-- END: ironsworn-truths-summary -->`. Replace the entire block (including fences) with the regenerated version. If the start fence is absent, append the block at the end of the file.

The block's purpose: every future session loads campaign `CLAUDE.md`, so locked summaries are always in the LLM's context without re-reading the vault.

## Re-entry on a locked truth

If the player picks a truth that is already `locked: true`:

1. Show the current locked answer + quest seed + notes.
2. Offer three actions:
   - **Edit** — keep the lock, allow tweaking notes / quest seed / wording. Save back, regenerate summary block.
   - **Replace** — clear the file and restart the per-truth loop. Warn that downstream session notes may reference the previous answer.
   - **View** — read-only display, no changes.

## Mythic 2e graceful coupling

If `mythic-gme` skill is loaded — detected by either (a) `mythic-gme` appearing in the active skills list shown to you by the harness, (b) a prior invocation of `solo-roll meaning-pair` or `solo-roll fate-check` in this session, or (c) the campaign `CLAUDE.md` listing it as an active skill — include this option in the per-truth menu:

> **Mythic meaning pair (player-directed)** — invoke `solo-roll meaning-pair` once. Before rolling, ask the player which target: a fresh truth/option, a quest seed for the chosen option, or both. Announce both words verbatim and apply the [Interpretation discipline](../mythic-gme/SKILL.md#interpretation-discipline) from the `mythic-gme` skill — roll one pair first, use both words (dissonance is a feature), and only roll a second pair or discard a word *explicitly* if the first reading is genuinely forced.

If `mythic-gme` is not loaded, do **not** mention this option. Never auto-load it. Never substitute it for the standard A/B/C/Roll/Fresh/Riff/Freeform paths unless the player asks for it.

## Boundaries

- Never silently overwrite a locked truth. Always go through the re-entry flow.
- Never invent attribution or licensing language. The reference file already credits Shawn Tomkin and CC-BY-4.0.
- Do not generate quest seeds longer than ~3 sentences — they should hint, not script the campaign.
- Stay out of play. This skill runs at session zero (or revisits between sessions). Do not start scenes or invoke other Ironsworn moves while in the truth-locking loop.
