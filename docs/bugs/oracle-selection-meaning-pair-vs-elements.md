# Bug: Oracle Selection — Meaning Pair Used for Scene Description

## Observed

**Session 3, ironsworn-test1:**

Player asked for a description of a journey waypoint. LLM rolled `solo-roll meaning-pair`, got
"Action: Fight — Description: Busily", and narrated a combat work party around a crossroads marker.

Player correction: "meaning-pair is for events, I just wanted a description of the waypoint! Roll on
some tables for DESCRIPTIVE elements, not actions!"

LLM then correctly switched to `elements/terrain`, `elements/location`, `elements/sound`.

## Root cause

No explicit guidance in either skill on *when* to use which oracle type. The LLM defaulted to
meaning-pair as a general "I need inspiration" tool, but meaning-pair is semantically wrong for
descriptive atmosphere.

## Oracle type guide (what the skill should say)

| Situation | Correct oracle |
|---|---|
| Random event content: what happens? | `solo-roll meaning-pair` (action + description) |
| Fate check interpretation: yes/no + nuance | `solo-roll fate-check` |
| Scene description: what does a place feel/look/sound like? | `elements/terrain`, `elements/location`, `elements/sound`, `elements/smell`, `elements/descriptor` |
| NPC name needed | `solo-roll table ironsworn/names` or similar |
| Plot complication / event focus | `elements/plottwist` or `solo-roll meaning-pair` |

Meaning-pair = **what happens**. Elements tables = **what something is like**.

## Fix needed

Add a short oracle-selection guide to `skills/mythic-gme/SKILL.md` (or `skills/ironsworn/oracles.md`).
Something like:

```
**Choosing an oracle:**
- Need to know WHAT HAPPENS (event, random event content, plot twist)? → meaning-pair
- Need to know YES/NO about a fact? → fate-check
- Need to describe how something LOOKS/FEELS/SOUNDS? → elements/ tables (terrain, location, sound, smell, descriptor)
- Don't use meaning-pair for atmosphere or description — its action+description pair reads as events, not sensory detail.
```

## Files involved

- `skills/mythic-gme/SKILL.md` — add oracle selection guide
- OR `skills/ironsworn/oracles.md` — if ironsworn oracle guidance lives there

## See also

`docs/bugs/ironsworn-skill-architecture.md` — transcript shows `oracles.md` was NEVER read during the session. Putting oracle selection guidance in `oracles.md` will not work; it must live in SKILL.md (always loaded) or in a small `oracles/selecting-an-oracle.md` file with a mandatory-read trigger in SKILL.md.
