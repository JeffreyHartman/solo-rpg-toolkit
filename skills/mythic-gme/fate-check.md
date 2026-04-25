# Fate Check — Threshold Reference

Command syntax and likelihood keys live in `SKILL.md`. This file is the threshold math grid the CLI uses internally — kept here for human inspection and verification.

## Yes thresholds

`solo-roll fate-check` rolls a d100 and compares to the `yes_threshold` for the given likelihood × CF cell. Roll ≤ threshold = Yes.

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

- **Exceptional Yes**: roll ≤ ⌊yes_threshold ÷ 5⌋
- **Exceptional No**: roll ≥ 101 − ⌈(100 − yes_threshold) ÷ 5⌉

CLI computes both automatically and returns `exceptional: true/false`.
