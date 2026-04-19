# Chaos Factor (CF)

The Chaos Factor is a dial from 1 to 9 that represents how much the world is in flux relative to the player character's control. It modifies all fate checks and scene tests, and it should be adjusted at the end of every scene.

## Starting value

CF starts at **5** for a fresh campaign, unless the story opens in an unusually stable or unusually chaotic moment.

## Adjustment rule

At the end of every scene, ask: *Did the player come out of that scene more in control of their situation, or less?*

- **More in control** (their plans worked, they neutralized a threat, they built an advantage): **CF -1** (minimum 1).
- **Less in control** (they lost a resource, an enemy advanced, a plan failed, a new complication landed and wasn't resolved): **CF +1** (maximum 9).
- **Genuine mixed result**: no change.

Trust the honest read. If you're hedging to keep CF stable, you're probably hiding from a real shift.

## What CF affects

- **Scene tests**: Higher CF = more likely the next scene is altered or interrupted.
- **Fate checks**: Higher CF shifts the odds toward more extreme outcomes in either direction (yeses get yes-er, nos get no-er at the edges of the likelihood ladder) and increases the chance of random events firing.
- **Random event frequency**: Doubles on a fate check only trigger an event if both dice are ≤ CF. A low CF means events fire only on low doubles; a high CF means most doubles trigger events.

## Feel of different CF values

- **CF 1-2**: Deeply stable. The player's plans unfold mostly as expected. Good for long-term projects, downtime, political intrigue with slow payoffs.
- **CF 3-4**: Everyday uncertainty. Things mostly go as expected but there's texture.
- **CF 5**: Baseline. Balanced between player intent and world pushback.
- **CF 6-7**: Turbulent. The world doesn't sit still. Scenes interrupt. Plans get sideswiped.
- **CF 8-9**: Chaos. Almost nothing happens as expected. Good for disaster sequences, escape scenes, warzones, dream logic. Not a sustainable baseline — if CF is pinned at 8-9 for many scenes, something dramatic should resolve and break the tension down.

## Tracking

Record CF in `dm-notes/mythic-state.md`:

```
# Mythic State
## Chaos Factor: 5 (was 4 last scene, +1 after the ambush)

## History
- Scene 1: CF 5 → 4 (player escaped the ruin intact)
- Scene 2: CF 4 → 5 (camp was raided)
- Scene 3: CF 5 → 6 (wolf companion taken)
```

Keeping this history visible in the DM notes also makes CF shifts feel earned rather than whimsical — the agent can look at the last few scenes and sanity-check itself.
