# Fate Check Reference

> Fate checks are run via `solo-roll fate-check` — this file is a human-readable reference. The CLI handles all math.

## Command

```bash
solo-roll fate-check --likelihood <key> --cf <N>
```

## Likelihood keys

| Natural language | `--likelihood` key |
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

## Yes thresholds (reference)

The table below shows the `yes_threshold` value for each likelihood × CF combination. Roll a d100 (via `dice` field in CLI output): ≤ yes_threshold = Yes; > yes_threshold = No.

| Likelihood | CF1 | CF2 | CF3 | CF4 | CF5 | CF6 | CF7 | CF8 | CF9 |
|---|---|---|---|---|---|---|---|---|---|
| certain | 50 | 65 | 75 | 85 | 90 | 95 | 99 | 99 | 99 |
| nearly_certain | 35 | 50 | 65 | 75 | 85 | 90 | 95 | 99 | 99 |
| very_likely | 25 | 35 | 50 | 65 | 75 | 85 | 90 | 95 | 99 |
| likely | 15 | 25 | 35 | 50 | 65 | 75 | 85 | 90 | 95 |
| 50_50 | 10 | 15 | 25 | 35 | 50 | 65 | 75 | 85 | 90 |
| unlikely | 5 | 10 | 15 | 25 | 35 | 50 | 65 | 75 | 85 |
| very_unlikely | 1 | 5 | 10 | 15 | 25 | 35 | 50 | 65 | 75 |
| nearly_impossible | 1 | 1 | 5 | 10 | 15 | 25 | 35 | 50 | 65 |
| impossible | 1 | 1 | 1 | 5 | 10 | 15 | 25 | 35 | 50 |

Source: Mythic GME 2e.

## Exceptional outcomes

- **Exceptional Yes**: roll ≤ yes_threshold ÷ 5 (floor)
- **Exceptional No**: roll ≥ 101 − ⌈(100 − yes_threshold) ÷ 5⌉

The CLI computes these automatically and returns `exceptional: true/false` in the output.

## Random event

Fires when both dice match AND each die ≤ CF. The CLI returns `random_event_triggered: true` when this occurs.
