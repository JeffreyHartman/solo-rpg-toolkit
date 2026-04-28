# Bug: Undertake a Journey — Collapsed to Single Roll

## Observed

**Session 3, ironsworn-test1 — travel to Redgate:**

Failure cascade from the transcript:

1. Player reported "Undertake a Journey: strong hit!" without specifying rank.
2. LLM marked progress but narrated the treeline mile as a waypoint AND implied near-arrival at Redgate — framing it as though one roll could complete the journey.
3. LLM assigned Dangerous rank because the treeline felt dangerous — wrong. Journey rank = difficulty/distance of the trip, not encounter hazards along the way. 3-hour local road = Troublesome.
4. Player asked "we're 2/10 and arrived at Redgate?" — LLM admitted mess, offered options.
5. Player said "not going to roll Reach Your Destination yet, let's say we're halfway." LLM set progress to 5/10 — wrong. Player meant they had made partial progress; one Troublesome strong hit = 3 ticks = 3/10. "Halfway" was spatial context, not a box count.
6. Player corrected: "it's 3 progress." LLM updated to 3/10.

## What the rules say

Undertake a Journey is a **progress track move**, not a "roll to succeed" move.

Correct flow:
1. Create a journey progress track (rank based on distance/difficulty).
2. Each roll of Undertake a Journey **marks progress** based on rank:
   - Troublesome: 3 boxes, Dangerous: 2 boxes, Formidable: 1 box, Extreme: 0.5, Epic: 0.25
3. Strong hit → mark progress + no trouble. Weak hit → mark progress but trouble (lose supply, face danger, etc.).
   Miss → do NOT mark progress; pay the price instead.
4. When enough progress is marked (player chooses to stop), roll **Reach Your Destination** using the progress
   track score (filled boxes), not a stat. This resolves the journey.

A "Likely" or "short" journey at Dangerous rank still needs several rolls before it's done.
One strong hit does not mean you teleport there.

## Root cause

The skill's `## Progress tracks are sacred` principle is present but the specific Undertake a Journey
flow isn't spelled out step-by-step in `SKILL.md` or `moves.md`. The LLM apparently treated Undertake
a Journey like a Face Danger roll (pass = success) rather than a progress-marking move.

## Expected behavior

When Undertake a Journey triggers:
1. Announce: creating a journey progress track. Ask rank (or determine from fiction).
2. Create a Thread or note the track in Character.md Vows callout (journey tracks live there).
3. Each roll marks progress per rank rules. Narrate the leg of the journey, then stop: "What do you do
   as you travel? / Do you press on or camp?" — player decides when to attempt Reach Your Destination.
4. Only on Reach Your Destination (using progress score) does the journey resolve.
5. On miss at Reach Your Destination → something goes wrong at the destination; you still arrive but
   pay a price.

## Fix needed

Add explicit journey flow to `skills/ironsworn/moves.md` under Undertake a Journey:

```
**This is a progress track move.** Do not resolve the journey on a single roll.
1. Create the track (rank = difficulty of journey).
2. Each roll: strong hit or weak hit → mark progress (+ weak hit cost). Miss → do NOT mark; pay the price.
3. When player chooses to resolve: roll Reach Your Destination using progress score.
```

And add a note to `SKILL.md` general principles:

```
**Journey = multiple rolls.** Undertake a Journey marks progress; Reach Your Destination resolves it.
A single Undertake a Journey roll does not end the journey, even on a strong hit.
```

## Files involved

- `skills/ironsworn/moves.md` (or `moves/undertake-a-journey.md` per architecture restructure) — add explicit step-by-step
- `skills/ironsworn/SKILL.md` — add principle note to progress tracks section AND mandate read of move file before rolling

## See also

`docs/bugs/ironsworn-skill-architecture.md` — transcript shows `moves.md` was not read before move calls. Fixing this file's text alone will not help unless the LLM actually loads it. Per-move file restructure + mandatory-read language in SKILL.md is the prerequisite.

---

## Status

**FIXED** — commit `b76b358` (2026-04-27)

`skills/ironsworn/moves/undertake-a-journey.md` created with explicit progress track procedure: rank setup before first roll, progress-per-rank table, "do NOT mark progress on miss", "one roll ≠ one journey" note, hand-back-to-player language after each waypoint. Verified passing in blind session test.
