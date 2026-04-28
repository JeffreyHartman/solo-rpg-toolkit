# Endure Harm

**Trigger:** You face physical damage.

## Harm Amounts by Rank

When a foe or hazard causes harm, the amount is determined by rank:

| Rank | Harm | Examples |
|---|---|---|
| Troublesome | 1 | Minor foe attack, painful injury, tiring effort |
| Dangerous | 2 | Skilled foe or deadly creature, nasty injury, demanding effort |
| Formidable | 3 | Exceptional foe or mighty creature, serious injury, exhausting effort |
| Extreme | 4 | Overwhelming monster/beast attack, grievous injury, debilitating effort |
| Epic | 5 | Legendary foe of mythic power, horrific injury, consuming effort |

**Weapon harm (when you inflict on foes):** Deadly weapon (sword, axe, spear, bow) = 2 harm. Unarmed or improvised weapon (shield, stick, club, staff, rock) = 1 harm. Moves may add additional harm on top.

**Mechanics before rolling:**
1. Suffer -health equal to harm amount (foe's rank, or appropriate to the situation).
2. If health drops to 0, suffer -momentum equal to any remaining -health (the overflow).
3. Update Character.md immediately before rolling.

**Roll:** +health or +Iron, whichever is higher.

---

## Strong Hit

**Player chooses one:**
1. Shake it off: If health > 0, suffer **-1 momentum** in exchange for **+1 health**.
2. Embrace the pain: Take **+1 momentum**.

## Weak Hit

You press on. No additional effect.

## Miss

Suffer **-1 momentum** additionally.

If health is at 0, mark **Wounded** or **Maimed** (if currently unmarked). If both are already marked, roll d100 on the table below.

---

## Endure Harm Table (d100) — health at 0, both debilities marked

| Roll | Result |
|---|---|
| 1–10 | The harm is mortal. **Face Death** → `moves/face-death.md` |
| 11–20 | You are dying. Heal within an hour or two, or **Face Death** → `moves/face-death.md` |
| 21–35 | You are unconscious and out of action. Come back in an hour or two — unless a foe finishes you: **Face Death** |
| 36–50 | Reeling, fighting to stay conscious. Any vigorous activity before resting: roll on this table again first. |
| 51–100 | Battered but still standing. |

---

**Debility tracking:** When you mark Wounded or Maimed `[x]`, reduce max momentum by 1 and reset by 1. Update the `_Momentum bounds:` line in Character.md immediately.
