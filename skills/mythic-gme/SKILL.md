---
name: mythic-gme
description: Oracle mechanics for yes/no questions, scene tests, random events, and chaos factor tracking. Use whenever the player asks a yes/no question, frames a new scene, or a random event needs resolving. All dice are rolled via the `solo-roll` CLI — never generate numbers yourself.
---

# Mythic GME 2e Skill

This skill wires the Mythic Game Master Emulator into your solo RPG session. Every die roll goes through `solo-roll` — no LLM-invented numbers.

## Using the CLI

All random operations use `solo-roll`. Run each command as a Bash tool call and parse the JSON output.

**Never generate dice numbers yourself.** If you're tempted to say "I'll roll a 7", use the CLI instead.

---

## Chaos Factor (CF)

CF is a 1–9 dial tracking narrative volatility. Starts at **5**.

At scene end, ask: did the player come out more in control or less?
- More in control (plans worked, threat neutralized): **CF − 1** (min 1)
- Less in control (resource lost, complication unresolved): **CF + 1** (max 9)
- Genuine mixed result: no change

Track CF in `dm-notes/mythic-state.md`. Pass it as `--cf N` to every CLI fate check.

See `chaos-factor.md` for CF feel guide and examples.

---

## Scene Test

Run at the start of every Expected Scene.

```bash
solo-roll roll d10
```

Output: `{"dice": "d10", "roll": N}`

| Roll | Result |
|------|--------|
| roll > CF | **Expected Scene** — proceed as planned |
| roll ≤ CF, odd (1,3,5,7,9) | **Altered Scene** — something changes; reframe the opening |
| roll ≤ CF, even (2,4,6,8) | **Interrupt Scene** — full Random Event fires instead |

For an **Interrupt Scene**, run the full [Random Event](#random-event) procedure below.

For an **Altered Scene**, reframe the scene in the next-most-expected way. Use `solo-roll meaning-pair` if you need inspiration for what changes.

---

## Fate Check

When a yes/no question arises, choose a likelihood that reflects how likely a Yes is, then run:

```bash
solo-roll fate-check --likelihood <key> --cf <N>
```

Replace `<N>` with the current Chaos Factor.

### Likelihood keys

| Player says… | Use `--likelihood` |
|---|---|
| Certain / Has to be | `certain` |
| Nearly Certain | `nearly_certain` |
| Very Likely | `very_likely` |
| Likely | `likely` |
| 50/50 | `50_50` |
| Unlikely | `unlikely` |
| Very Unlikely | `very_unlikely` |
| Nearly Impossible | `nearly_impossible` |
| Impossible / No way | `impossible` |

### Output fields

```json
{
  "likelihood": "likely",
  "cf": 5,
  "yes_threshold": 65,
  "exceptional_yes_cap": 13,
  "exceptional_no_floor": 94,
  "dice": [4, 3],
  "roll": 43,
  "outcome": "yes",
  "exceptional": false,
  "random_event_triggered": false
}
```

- **outcome**: `exceptional_yes` | `yes` | `no` | `exceptional_no`
- **exceptional**: `true` when outcome is exceptional_yes or exceptional_no
- **random_event_triggered**: `true` when both dice match AND each die ≤ CF → run [Random Event](#random-event)

### Announcing results

After the roll:
1. State the outcome and whether it was exceptional
2. If `random_event_triggered: true`, run the Random Event procedure
3. Interpret in fictional context

---

## Random Event

Fires when:
- A fate check returns `random_event_triggered: true`
- A scene test produces an Interrupt Scene

**Step 1 — Event Focus:**

```bash
solo-roll table mythic/event-focus
```

Output: `{"result": "NPC Action"}` (one of 12 categories)

**Step 2 — Event Meaning:**

```bash
solo-roll meaning-pair
```

Output: `{"action": {"result": "Betray"}, "description": {"result": "Ancient"}}`

**Step 3 — Interpret:**

Combine focus + word pair in current fictional context. First natural reading wins. The focus tells you WHAT kind of event; the word pair tells you HOW or WHAT specifically.

Example: Focus = "NPC Action", Action = "Betray", Description = "Ancient" → an NPC you trusted is revealed to have ties to the old enemy faction.

See `event-focus.md` for descriptions of each focus category.

---

## Detail Check / Meaning Pair

When you need descriptive detail, flavor, or an answer to a non-binary question:

```bash
solo-roll meaning-pair
```

Interpret the word pair (`action` + `description`) in context. You don't need a full random event — just use the pair as a creative prompt.

---

## State Tracking

Keep `dm-notes/mythic-state.md` updated:

```markdown
# Mythic State
## Chaos Factor: 5

## Threads List
- Find the missing merchant
- Expose the corrupt guard captain

## Characters List
- Kesta Ulfhild (smith, Stonebeck)
- Captain Rorik (city guard)

## Scene History
- Scene 1: CF 5 → 4 (player escaped cleanly)
- Scene 2: CF 4 → 5 (ambush cost supplies)
```

At session start: read this file to restore CF and active threads/characters.

---

## When NOT to use Mythic

- Inside system-specific moves (Ironsworn progress tracks, PF2e skill checks) — use the system's own mechanics
- Player-authored scenes where no randomness is needed
- Narrative beats the player explicitly declares as certain

---

## Reference files

- `chaos-factor.md` — CF adjustment rules and feel guide
- `fate-check.md` — Reference table of all yes_threshold values (human-readable; CLI handles the math)
- `event-focus.md` — Event focus categories with descriptions
- `meaning-tables.md` — How the meaning-pair tables work and how to customize them
