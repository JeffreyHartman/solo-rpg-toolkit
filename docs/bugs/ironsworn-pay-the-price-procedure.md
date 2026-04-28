# Bug: Pay the Price — Narrated Away Instead of Resolved as Move

## Observed

**Session 3, ironsworn-test1 — Undertake a Journey miss:**

Player got a miss. LLM ran meaning-pair ("Disrupt — Energetically"), narrated a young Ashveil fighter
hearing the creature mimic his father's voice and taking two steps off the road. A party member grabs
his arm. He doesn't fight. Voice stops. LLM continued narration — situation resolved in prose.

Player: "You're moving on too quickly, on a miss we must PAY THE PRICE. You narrated something that
had no mechanical or narrative price. I think the price should be we have to roll to see if we can
stop him, what would that be?"

LLM then correctly identified Face Danger and handed agency back.

## Root cause

`moves.md` lists "Pay the price" as a miss outcome for every move, and lists what moves it can trigger
(Endure Harm, Endure Stress, etc.), but **Pay the Price is not defined as a move with a procedure**.

There is no instruction saying: STOP. Do not narrate through the consequence. Present the price, then
ask the player what they do or trigger the appropriate follow-on move.

The LLM read "pay the price" as "narrate a bad thing happening" and then wrote through the resolution,
removing player agency entirely.

## What Pay the Price actually is

Pay the Price is a mandatory pause + oracle + move trigger. The procedure:

1. **Determine the price.** Options:
   - Use the oracle ("Disrupt Energetically" etc.) to find the shape of the consequence.
   - Or pick something that makes obvious sense in fiction (injury, supply loss, complication).
2. **State the price concretely.** Name what is happening or about to happen. Do NOT narrate it
   through to resolution.
3. **Stop and hand back control.** The price creates a new situation. Ask what the player does,
   OR if the price demands a roll (someone is in immediate danger, harm must be absorbed, etc.),
   trigger the correct move:
   - Physical danger → **Face Danger** (or Endure Harm if damage is automatic)
   - Emotional/spirit damage → **Endure Stress**
   - Companion hit → **Companion Takes a Hit**
   - Ally/NPC in danger → **Face Danger** to intervene
4. **Do not resolve NPC fate GM-side.** If an NPC is walking into danger, the player decides whether
   to intervene and rolls for it. Don't have another NPC save them in narration.

## Key principle

**The price creates the next scene beat. It does not end it.**

Narrating "she grabs his arm and he stops" is not paying the price — it's erasing it.
The fighter walking toward the wood IS the price. Whether he makes it there is the player's problem.

## Fix needed

Add Pay the Price as an explicit move entry in `skills/ironsworn/moves.md`, before the "Ask the Oracle"
section:

```
## Pay the Price

**Not optional. Not a narration prompt. A move.**

When any move results in a miss:
1. Oracle or obvious fiction: determine what goes wrong.
2. State it. Name the danger or consequence clearly.
3. STOP. Do not narrate the resolution.
4. Trigger the appropriate follow-on move (Face Danger, Endure Harm, Endure Stress, etc.)
   OR hand control back to the player: "What do you do?"

**Never narrate an NPC saving the situation in Pay the Price.**
If the price puts an NPC in danger, the player rolls to intervene — or doesn't.
```

Also add to `SKILL.md` under "Interpreting outcomes":

```
**Miss → Pay the Price is a mandatory stop.** Name the consequence, do not write through it.
The player must have agency over the follow-on. The price creates the next beat; it does not end it.
```

## Files involved

- `skills/ironsworn/moves.md` (or `moves/pay-the-price.md` per architecture restructure) — add Pay the Price as explicit move with procedure
- `skills/ironsworn/SKILL.md` — add note to "Interpreting outcomes" section

## See also

`docs/bugs/ironsworn-skill-architecture.md` — transcript shows `moves.md` was not read before move calls. Pay the Price procedure in `moves.md` is invisible by default. Fix requires per-move file + mandatory-read instruction in SKILL.md core loop.

---

## Status

**FIXED** — commits `b76b358`, `41c594b` (2026-04-27)

`skills/ironsworn/moves/pay-the-price.md` created with explicit STOP procedure. Initial commit had "choose one" ambiguous about who chooses — blind test caught agent choosing unilaterally. Second commit (41c594b) changed Step 1 to present all three options to the player and wait for their choice. Verified passing in blind session test v2.
