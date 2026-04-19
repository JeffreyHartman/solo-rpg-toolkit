# Fate Check Chart

Roll 2d10 read as d100 (00-99). Cross-reference **Likelihood** (row) with current **Chaos Factor** (column) to find the thresholds.

- Number shown = "Yes" threshold (roll ≤ this is Yes).
- Exceptional Yes = roll ≤ (Yes threshold ÷ 5), rounded down.
- Exceptional No = roll ≥ (100 - ((100 - Yes threshold) ÷ 5)), rounded up.
- Doubles (e.g. 3/3, 7/7) where both dice ≤ Chaos Factor → **Random Event** also fires.

> **Note**: The values below match Mythic 2e's fate chart logic but you should cross-check against your copy of the book — I've reproduced them to function; they are not guaranteed identical to every cell in the official chart. If you want exact fidelity, overwrite this file with your book's values.

## Fate Chart (Yes threshold)

| Likelihood           | CF1 | CF2 | CF3 | CF4 | CF5 | CF6 | CF7 | CF8 | CF9 |
|----------------------|----:|----:|----:|----:|----:|----:|----:|----:|----:|
| Has to be            |  85 |  90 |  92 |  94 |  95 |  96 |  97 |  98 |  99 |
| Near sure thing      |  75 |  82 |  85 |  88 |  90 |  92 |  94 |  96 |  98 |
| Very likely          |  65 |  72 |  76 |  80 |  85 |  88 |  92 |  94 |  96 |
| Likely               |  50 |  58 |  65 |  72 |  75 |  82 |  85 |  88 |  92 |
| 50/50                |  25 |  35 |  45 |  50 |  50 |  55 |  65 |  75 |  85 |
| Unlikely             |  10 |  15 |  20 |  25 |  25 |  32 |  40 |  45 |  50 |
| Very unlikely        |   5 |   8 |  12 |  15 |  15 |  18 |  25 |  30 |  35 |
| Near impossible      |   3 |   5 |   7 |  10 |  10 |  12 |  15 |  20 |  25 |
| No way               |   1 |   2 |   3 |   5 |   5 |   7 |  10 |  15 |  20 |

## Quick-read process

Example: **Likelihood = Likely, CF = 5, rolled 2d10 showing 4 and 3 → 43**

- Yes threshold at CF 5, Likely = 75.
- Exceptional Yes threshold = 75 / 5 = 15.
- Exceptional No threshold = 100 - ((100 - 75) / 5) = 100 - 5 = 95, so rolls ≥ 95 are Exceptional No.
- 43 ≤ 75, but > 15 → **Yes** (not exceptional).
- Dice were 4 and 3 (not doubles) → no random event.

Example: **Likelihood = 50/50, CF = 7, rolled 5 and 5 → 55**

- Yes threshold = 65. 55 ≤ 65 → **Yes**.
- Dice are doubles (5/5). 5 ≤ CF 7 → **Random event also fires.**

## When in doubt about likelihood

Lean toward 50/50 unless there's real reason to shift. Over-tuning likelihood to match what you want defeats the purpose. If you'd be happy with either answer, go 50/50.
