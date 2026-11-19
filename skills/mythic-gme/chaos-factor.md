# Chaos Factor — Reference

Starting value, adjustment rule, and `--cf` usage live in `SKILL.md`. This file is the feel guide and the history-tracking pattern.

## What CF affects

- **Scene tests**: higher CF = more likely the next scene is altered or interrupted.
- **Fate checks**: higher CF raises the chance of Yes for every likelihood (Mythic 2e, The Chaos Factor) and makes random events more likely.
- **Random event frequency**: doubles 11 through 99 on a fate check trigger an event only if the repeated digit is ≤ CF. Low CF → events fire only on low doubles; high CF → most doubles trigger events.

## Feel of different CF values

- **CF 1-2**: Deeply stable. Player's plans unfold mostly as expected. Good for long-term projects, downtime, political intrigue with slow payoffs.
- **CF 3-4**: Everyday uncertainty. Things mostly go as expected but there's texture.
- **CF 5**: Baseline. Balanced between player intent and world pushback.
- **CF 6-7**: Turbulent. World doesn't sit still. Scenes interrupt. Plans get sideswiped.
- **CF 8-9**: Chaos. Almost nothing happens as expected. Good for disaster sequences, escape scenes, warzones, dream logic. Not a sustainable baseline — if pinned at 8-9 for many scenes, something dramatic should resolve and break the tension down.

Trust the honest read. If you're hedging the adjustment to keep CF stable, you're probably hiding from a real shift.

## History format

Update `./mythic-state.md` at the end of every scene, not at session end, with one line per scene in `## Scene History`. Visible history makes shifts feel earned rather than whimsical — sanity-check yourself by glancing at the last few entries.

```
# Mythic State
## Chaos Factor: 5 (was 4 last scene, +1 after the ambush)

## Scene History
- Scene 1: CF 5 → 4 (player escaped the ruin intact)
- Scene 2: CF 4 → 5 (camp was raided)
- Scene 3: CF 5 → 6 (wolf companion taken)
```
