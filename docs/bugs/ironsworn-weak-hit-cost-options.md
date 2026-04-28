# Bug: Weak Hit Costs — Not Presented as Player Choice

## Observed

**Session 3, ironsworn-test1 — Face Danger, weak hit:**

Player got weak hit. LLM narrated its own cost ("the codeword slipped, creature now knows Idris's name,
no additional stat hit") and moved on. Player had to intervene: "On a weak hit you succeed but must
choose from one of 4 options. I will Endure Stress."

Separately: LLM also docked -1 momentum for the upstream journey miss, in addition to the Face Danger
cost. Player caught this: "It doesn't say take away momentum, it just says Pay the Price, which I did
by triggering Face Danger." LLM admitted double-dip and corrected to +6.

## Two bugs, one incident

### Bug A: Weak hit cost is a player choice, not GM narration

On a weak hit the player succeeds AND pays a cost. The cost is a **player decision from a menu**, not
a GM-selected narrative consequence. The LLM must:
1. Confirm the weak hit and that the action succeeds.
2. Present the cost options.
3. Wait for player to choose.
4. Apply mechanically.

Never choose a cost unilaterally and narrate it closed.

### Bug B: "Pay the Price" = one price, not price + momentum drain

When a move says "miss: Pay the Price," the price is whatever the follow-on move or consequence is.
Do NOT also deduct momentum, supply, or any other resource separately unless that IS the chosen price.

Journey miss → "Pay the Price" → Face Danger triggered = price paid. Full stop.
No additional momentum penalty on top.

## Face Danger weak hit cost options (from Ironsworn rulebook)

Present these when Face Danger results in a weak hit:

1. **You are delayed, lose advantage, or face a complication.** (Narrative setback, no stat change.)
2. **Suffer -1 supply.**
3. **Suffer -1 momentum now and -1 more at next roll.** (Or similar momentum cost per edition.)
4. **Endure Harm or Endure Stress** (player's choice which fits fiction) for -1 health or -1 spirit.

*Note: The exact option wording should be verified against the Ironsworn rulebook PDF. The above is
a reconstruction. Populate from the book before implementing the fix.*

## Broader pattern

This is likely not Face Danger-specific. Most adventure moves have a weak hit "at a cost" with options.
The skill should document the cost menu for each move that has one, so the LLM can present them
rather than improvising.

Priority moves to document with full cost options:
- Face Danger
- Secure an Advantage
- Undertake a Journey (weak hit: mark progress but lose supply / face peril / etc.)
- Compel
- Any move where the current entry just says "at a cost"

## Fix needed

1. `skills/ironsworn/moves.md` — expand each weak hit entry to list the actual cost options.
2. `skills/ironsworn/SKILL.md` — add to "Interpreting outcomes": "Weak hit costs are player choices.
   Present the menu. Do not narrate a cost without player selecting it."
3. `skills/ironsworn/moves.md` — add note under Pay the Price: "One price per miss. Do not stack
   additional resource penalties on top of the triggered move."

## Open question: Pay the Price — LLM stops, or LLM triggers?

User is torn. Two options:

**Option A — LLM stops:** Oracle determines the consequence shape. LLM names it. Player decides what
move (if any) handles it. Good: player agency, GM doesn't railroad. Bad: breaks flow every miss.

**Option B — LLM triggers:** Oracle determines shape, LLM selects the obvious follow-on move (Face
Danger for immediate peril, Endure Harm for damage, etc.) and presents it. Player rolls. Good: faster.
Bad: LLM might pick wrong move.

Recommendation: **Option B with explicit move selection stated aloud.** LLM says "This is Face Danger"
before asking for the roll — player can correct if wrong. Don't silently apply a consequence.

## Files involved

- `skills/ironsworn/moves.md` (or per-move files under `moves/` per architecture restructure) — cost options per move, Pay the Price double-dip note
- `skills/ironsworn/SKILL.md` — weak hit costs are player choices

## See also

`docs/bugs/ironsworn-skill-architecture.md` — transcript shows `moves.md` was read once, late. Cost menus added to `moves.md` will be invisible until SKILL.md mandates a read of the relevant move file before every roll. Per-move file restructure makes the read cheaper and more likely.
