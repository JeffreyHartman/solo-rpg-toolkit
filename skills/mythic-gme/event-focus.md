# Event Focus

When a random event fires (from a fate check returning `random_event_triggered: true` or an Interrupt Scene from the scene test), roll the Event Focus table to determine what type of event it is.

## Roll it

```
solo-roll table mythic/event-focus
```

Returns JSON: `{"table": "mythic/event-focus", "display_name": "Random Event Focus", "dice": "d100", "roll": 42, "result": "NPC Action"}`

The `result` field is the event focus. Then roll `solo-roll meaning-pair` to get the specific Action + Description that shapes the event.

## d100 Ranges

| d100 | Focus |
|------|-------|
| 1–5 | Remote Event |
| 6–10 | Ambiguous Event |
| 11–20 | New NPC |
| 21–40 | NPC Action |
| 41–45 | NPC Negative |
| 46–50 | NPC Positive |
| 51–55 | Move Toward A Thread |
| 56–65 | Move Away From A Thread |
| 66–70 | Close A Thread |
| 71–80 | PC Negative |
| 81–85 | PC Positive |
| 86–100 | Current Context |

## What each focus means

**Remote Event** — Something happens elsewhere, away from the current scene. Has no direct bearing on the PC right now, but may be relevant later. Think of it as world-building or foreshadowing.

**Ambiguous Event** — Something vague and unclear happens. The meaning-pair gives shape to it, but the exact nature may not become clear until later.

**New NPC** — A new character enters the story. Roll meaning-pair for their initial impression, then name them.

**NPC Action** — An existing NPC from your Characters List does something. Pick the most active or relevant one, or roll randomly from the list.

**NPC Negative** — Something bad happens to an NPC. Not necessarily caused by the PC — the world is acting on them.

**NPC Positive** — Something good happens to an NPC.

**Move Toward A Thread** — Progress on one of your active Threads. Which one? The most pressing, or roll randomly from the Threads List.

**Move Away From A Thread** — A Thread becomes harder, more obscured, or more complicated.

**Close A Thread** — A Thread resolves — for good or ill. It may close in an unexpected way.

**PC Negative** — Bad fortune for the player character. Not from an NPC action — the world itself is pushing back.

**PC Positive** — Good fortune for the player character.

**Current Context** — The scene itself intensifies or shifts. Something about the current situation changes.
