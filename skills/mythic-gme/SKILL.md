---
name: mythic-gme
description: Use for Mythic Game Master Emulator mechanics — fate checks (yes/no oracle weighted by Chaos Factor), scene tests (did the scene proceed as expected, get altered, or get interrupted), event focus rolls, and Chaos Factor tracking. Activate WHENEVER the player asks a yes/no question during play, a new scene is about to begin, a random event is triggered, or the agent needs structured unpredictability to avoid defaulting to the most predictable narrative path. Pairs well with any RPG system skill (Ironsworn, PF2e, etc.) — Mythic sits on top as the pacing/oracle layer.
---

# Mythic Game Master Emulator (2e) Skill

Mythic is by Tana Pigeon / Word Mill Games. This skill encodes the *mechanics and procedural flow* of running Mythic 2e. **Specific lookup tables (Meaning Tables, full Event Focus percentages, etc.) are copyrighted content from the Mythic 2e book — populate `meaning-tables.md` and `event-focus.md` from your own copy.** The scaffolding here will work immediately; the tables marked `[POPULATE FROM BOOK]` are where you plug in the real data.

## Why this layer exists

LLMs, left alone, write the most predictable story available. Mythic breaks that by forcing the narrative to react to *external* randomness rather than whatever the model's next-token prediction wants. When you use this skill faithfully, you will repeatedly produce developments the agent would *never* have invented on its own — and then have to justify them. That friction is the whole point.

## Chaos Factor

The Chaos Factor (CF) is the world's current volatility, 1 (very stable, predictable) to 9 (utter chaos). It starts at **5** by default.

- **After a scene where the player is in control / things went their way**: CF -1 (minimum 1).
- **After a scene where the player lost control / things went against them**: CF +1 (maximum 9).
- Track CF in `dm-notes/mythic-state.md` session to session.

The CF modifies fate checks, scene tests, and event frequency.

## Scene Test (run at the start of every scene)

When the player proposes / agrees to a new scene:
1. Ask yourself: *What does the player reasonably expect this scene to be?* Write it down in one sentence in dm-notes.
2. Roll 1d10.
   - If the roll is **≤ current CF**, the scene is NOT as expected.
     - If the roll is **even**: **Altered scene** — one element of the expected setup is different. (Who's there, what they want, where it is, what just happened.) Resolve by Meaning Table roll if you need help: "what's different?"
     - If the roll is **odd**: **Interrupt scene** — the expected scene doesn't happen; something intrudes instead. Roll a **Random Event** (see below) to see what.
   - If the roll is **> CF**, the scene proceeds as expected. Narrate.

## Fate Check (yes/no questions)

Whenever the player asks a yes/no question about the world, or the agent has a question that needs a binary answer, use a Fate Check instead of guessing.

### Steps
1. Pick a **likelihood** for "yes" before rolling. The standard ladder:
   - Has to be / No way
   - Near sure thing / Impossible
   - Very likely / Very unlikely
   - Likely / Unlikely
   - 50/50
2. Roll 2d10. Read them as percentile (e.g. a 3 and a 7 → 37). Also note each individual die.
3. Look up the likelihood row against the current CF in `fate-check.md` to get two thresholds: an **Exceptional Yes cap** and a **Yes cap**.
4. Result:
   - Roll ≤ Exceptional Yes cap → **Exceptional Yes** (very strongly yes, with emphasis)
   - Roll ≤ Yes cap → **Yes**
   - Roll > Yes cap but not in Exceptional No range → **No**
   - Roll in Exceptional No range → **Exceptional No** (very strongly no, with emphasis)
5. **Random Event check** (doubles): if both d10s came up the same value AND that value is ≤ CF, a random event fires in addition to the Yes/No answer. (Example: CF 6, you rolled 4/4 → event fires. CF 3, you rolled 7/7 → no event.)

Announce rolls and reasoning to the player: *"Fate check, Likely, CF 5 — rolled 2d10: 4 and 4. That's 44 — Yes. And doubles under CF means a random event fires. Let me roll focus…"*

## Random Event (when triggered)

A random event is a disruption — something happens that the narrative wasn't aiming at.

1. Roll 1d100 on the **Event Focus** table (see `event-focus.md`) to get what *kind* of event.
2. Roll on the **Meaning Tables** (Action + Description, see `meaning-tables.md`) to get texture.
3. Interpret the combination in the current context. The focus tells you "who/what is this about"; the meaning pair tells you the *shape* of the event. Bend interpretation toward the existing fiction — don't force a left turn if a subtle shift makes more sense.

Examples of interpretation:
- Focus "NPC Action" + Meaning "Betray / Secret" → An NPC the player trusts acts on a hidden agenda that's now partly visible.
- Focus "Remote Event" + Meaning "Advance / Enemy" → Somewhere the player isn't, an enemy faction moves forward on their plans. The player may learn of this via rumor or evidence.
- Focus "New NPC" + Meaning "Seek / Information" → A new character arrives looking for something (or someone).

## Detail Check (describing things)

When the player asks for a descriptor the agent doesn't have pre-set ("what does the smuggler's face look like?" "what's unusual about this shrine?"), roll the Meaning Tables (Action + Description) and interpret.

## Saving state between sessions

The agent should write and update `dm-notes/mythic-state.md`:
```
# Mythic State
- Chaos Factor: 5
- Current scene: [expected setup, one sentence]
- Last scene outcome: [in control / out of control]
- Notable threads (Mythic "Threads List"): 
  - ...
- Notable NPCs (Mythic "Characters List"):
  - ...
```

Mythic's Threads and Characters lists are canonical — when they exist, you can also roll on them during scene tests and events (e.g. Event Focus "Thread / Character" → pick from these lists randomly).

## When NOT to use Mythic

- Inside-a-scene micro-mechanics where the system skill (Ironsworn, etc.) already has a move — let that system resolve it.
- When the player explicitly narrates a scene themselves (authorial control). Mythic is for *uncertainty*, not for overriding the player's fiction.

## Reference files
- `fate-check.md` — the fate chart with likelihood × CF thresholds
- `event-focus.md` — d100 categories for random events *(structure — populate from book)*
- `meaning-tables.md` — Action + Description d100 tables *(structure — populate from book)*
- `chaos-factor.md` — CF tracking rules and examples
