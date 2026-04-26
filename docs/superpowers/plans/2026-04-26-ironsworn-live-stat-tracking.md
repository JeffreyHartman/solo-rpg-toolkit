# Ironsworn Live Stat Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Ironsworn skill model update `Character.md` live during play — immediately after every stat change — so the player never manually edits their character sheet.

**Architecture:** Prompt-only. No new Python. Three changes to the toolkit repo (SKILL.md, character-template.md, example-campaign/CLAUDE.md) plus one migration of the active campaign's Character.md to the new callout-block format. The new format uses Obsidian callout blocks (`> [!tip]`, `> [!warning]`, etc.) with simple labeled lines so the model can do reliable single-line string-match edits.

**Tech Stack:** Markdown, Obsidian callout syntax. No Python. No tests (markdown-only — verify by reading the file back after each edit).

---

## File Map

| File | Action | What changes |
|---|---|---|
| `skills/ironsworn/SKILL.md` | Modify | Add `## Live stat tracking` section after `## Interpreting outcomes` |
| `skills/ironsworn/character-template.md` | Rewrite | Full callout-block format (blank template for new campaigns) |
| `example-campaign/CLAUDE.md` | Modify | Session end step 3: remove "update character sheet" (now live) |
| `/home/jeff/rgp/claude/ironsworn-test1-playervault/Character.md` | Rewrite | Migrate Cadoc's sheet to callout format (outside toolkit repo) |

---

## Task 1: Add `## Live stat tracking` to SKILL.md

**Files:**
- Modify: `skills/ironsworn/SKILL.md` (insert after `## Interpreting outcomes` block, before `## Principles for being a good GM here`)

- [ ] **Step 1: Edit SKILL.md — insert the new section**

  Use the Edit tool. `old_string` is the end of Interpreting outcomes through the start of the next section header; `new_string` inserts the new section between them.

  **old_string:**
  ```
  - **Miss**: Pay the price. The situation gets worse. This is NOT always combat damage — often a new complication, an NPC turns against them, a resource is spent, a secret is revealed that they didn't want revealed, a clock ticks down on a vow.

  ## Principles for being a good GM here
  ```

  **new_string:**
  ```
  - **Miss**: Pay the price. The situation gets worse. This is NOT always combat damage — often a new complication, an NPC turns against them, a resource is spent, a secret is revealed that they didn't want revealed, a clock ticks down on a vow.

  ## Live stat tracking

  After **every** move that changes a resource, edit `<PLAYER_VAULT_PATH>/Character.md`
  immediately — never defer to session end. Announce the new value inline as you narrate:
  "Health drops to 3/5." or "Momentum now +6."

  **What to edit:**

  | What changed | Line to find and replace |
  |---|---|
  | Health | `> Health: N/5` |
  | Spirit | `> Spirit: N/5` |
  | Supply | `> Supply: N/5` |
  | Momentum | `> Momentum: +N` or `> Momentum: -N` |
  | Companion health | `> [Companion Name] Health: N/max` |
  | Vow progress | `> **Vow Name** (Rank, 10 boxes): N/10` |
  | Debility gained | `> - [ ] Wounded` → `> - [x] Wounded` |

  **Bounds:** Read the max from the file (`N/max` format). Clamp after applying delta.
  For momentum, the bound is on the `> _Momentum bounds:` line in the Resources callout.
  Never go below −6 or above the stated max.

  **Debility effect on momentum:** When you mark a debility `[x]`, reduce max momentum by 1
  and reset by 1 (floor 0 for both). Update the `> _Momentum bounds:` line immediately.
  If current momentum now exceeds the new max, reduce it to match.

  **Progress tracks:** Rank determines step size when marking progress (Troublesome 3,
  Dangerous 2, Formidable 1, Extreme 0.5, Epic 0.25 — always round to nearest box).
  `Reach a Milestone` / `Mark Progress` triggers the edit. `Fulfill Your Vow` triggers
  resolve, not just a mark.

  ## Principles for being a good GM here
  ```

- [ ] **Step 2: Read SKILL.md back and verify**

  Confirm:
  - `## Live stat tracking` appears between `## Interpreting outcomes` and `## Principles for being a good GM here`
  - The table renders with correct pipe alignment
  - No surrounding sections lost or mangled

- [ ] **Step 3: Commit**

  ```bash
  git add skills/ironsworn/SKILL.md
  git commit -m "feat(ironsworn): add live stat tracking section to SKILL.md"
  ```

---

## Task 2: Rewrite `character-template.md`

**Files:**
- Modify: `skills/ironsworn/character-template.md` (full rewrite)

- [ ] **Step 1: Write the new content**

  Replace entire file content with:

  ````markdown
  # Character Template

  Copy into `Character.md` at `$PLAYER_VAULT_PATH/Character.md` and fill in. The model reads and edits this file live during play — keep the format exactly as shown.

  ---

  ## Basics

  **Name:**  
  **Look:** (short physical description — 1-2 sentences)  
  **Background:** (who they were before the vow)

  ---

  ## Stats

  | Edge | Heart | Iron | Shadow | Wits |
  |------|-------|------|--------|------|
  |      |       |      |        |      |

  *(Assign 3, 2, 2, 1, 1)*

  ---

  > [!tip] Resources
  > Health: 5/5
  > Spirit: 5/5
  > Supply: 5/5
  > Momentum: +2
  > _Momentum bounds: max 10, reset +2_

  ---

  > [!warning] Debilities
  > - [ ] Wounded
  > - [ ] Shaken
  > - [ ] Unprepared
  > - [ ] Encumbered
  > - [ ] Maimed
  > - [ ] Corrupted
  > - [ ] Cursed
  > - [ ] Tormented

  *(Each checked debility reduces Momentum max and reset by 1, floor 0)*

  ---

  > [!abstract] Vows
  > **[Vow Name]** ([Rank], 10 boxes): 0/10
  > _"[The sworn text.]"_

  *(Step size on Mark Progress — Troublesome: 3, Dangerous: 2, Formidable: 1, Extreme: 0.5, Epic: 0.25)*

  ---

  > [!example] Assets
  >
  > **[Asset Name]**
  > - [x] [First ability — unlocked at start]
  > - [ ] [Second ability]
  > - [ ] [Third ability]
  >
  > *(For companion assets add a health line before abilities: `[Companion Name] Health: N/max`)*

  ---

  > [!quote] Bonds
  > - [Person/community — relationship note]
  > - [Person/community — relationship note]
  > - [Person/community — relationship note]

  ---

  ## Experience

  Unspent: 0 | Spent: 0

  ---

  ## Notes

  *(Signature items, scars, quirks)*
  ````

- [ ] **Step 2: Read back and verify**

  Confirm:
  - Five callout sections present (`[!tip]`, `[!warning]`, `[!abstract]`, `[!example]`, `[!quote]`)
  - Every callout line starts with `> `
  - Stats table still present above the callouts (unchanged during play)
  - No leftover content from old template

- [ ] **Step 3: Commit**

  ```bash
  git add skills/ironsworn/character-template.md
  git commit -m "feat(ironsworn): rewrite character-template to callout-block format"
  ```

---

## Task 3: Update `example-campaign/CLAUDE.md` session procedure

**Files:**
- Modify: `example-campaign/CLAUDE.md` (session end procedure, step 3)

- [ ] **Step 1: Edit session end step 3**

  **old_string:**
  ```
  3. Update character sheet, NPC files, thread files.
  ```

  **new_string:**
  ```
  3. Update NPC files and thread files. Character sheet stats are updated live during play — at session end only update non-stat changes (bonds forged, assets advanced, experience spent).
  ```

- [ ] **Step 2: Read back and verify**

  Confirm the session end procedure reads coherently and the live-update note is present.

- [ ] **Step 3: Commit**

  ```bash
  git add example-campaign/CLAUDE.md
  git commit -m "feat(campaign): reflect live stat updates in session end procedure"
  ```

---

## Task 4: Migrate Cadoc's Character.md

**Files:**
- Rewrite: `/home/jeff/rgp/claude/ironsworn-test1-playervault/Character.md`

Note: this file is outside the toolkit repo — no git history. The path has a pre-existing typo (`rgp` not `rpg`).

- [ ] **Step 1: Write the migrated character sheet**

  Replace entire file content with:

  ```markdown
  # Cadoc

  **Look:** Young, wiry and weathered. Moves with deliberate caution. A scar on his face that never quite fully heals.

  **Background:** Messenger for Dunmore circle — carrying word and negotiating between communities. Encountered something in the dark between circles. The scar is what it left behind.

  ---

  ## Stats

  | Edge | Heart | Iron | Shadow | Wits |
  |------|-------|------|--------|------|
  | 1    | 2     | 1    | 2      | 3    |

  ---

  > [!tip] Resources
  > Health: 5/5
  > Spirit: 4/5
  > Supply: 5/5
  > Momentum: +5
  > _Momentum bounds: max 10, reset +2_

  ---

  > [!warning] Debilities
  > - [ ] Wounded
  > - [ ] Shaken
  > - [ ] Unprepared
  > - [ ] Encumbered
  > - [ ] Maimed
  > - [ ] Corrupted
  > - [ ] Cursed
  > - [ ] Tormented

  ---

  > [!abstract] Vows
  > **Background Vow** (Dangerous, 10 boxes): 0/10
  > _"I swear to find my nephew, or know his fate — and keep my sister safe from whatever haunts these villages."_

  ---

  > [!example] Assets
  >
  > **Hound — Bran** *(large grey wolfhound)*
  > Bran Health: 3/4
  > - [x] **Sharp:** When you *Gather Information* using Bran's keen senses to track your quarry or investigate a scene, add +1 and take +1 momentum on a hit.
  > - [ ] **Ferocious:** When you *Strike* or *Clash* alongside Bran and score a hit, inflict +1 harm or take +1 momentum.
  > - [ ] **Loyal:** When you *Endure Stress* in the company of Bran, add +1.
  >
  > **Wayfinder**
  > - [x] When you *Undertake a Journey*, take +1 momentum on a strong hit. If you burn momentum to improve your result, also take +1 momentum after you reset.
  > - [ ] When you *Secure an Advantage* or *Gather Information* by carefully surveying the landscape or scouting ahead, add +1 and take +1 momentum on a hit.
  > - [ ] When you *Swear an Iron Vow* to safely guide someone on a perilous journey, you may reroll any dice. When you *Fulfill Your Vow* and mark experience, take +1 experience.
  >
  > **Slayer**
  > - [x] When you *Gather Information* by tracking a beast or horror, or when you *Secure an Advantage* by readying yourself for a fight against them, add +1 and take +1 momentum on a hit.
  > - [ ] When you *Swear an Iron Vow* to slay a beast or horror, you may reroll any dice. When you *Fulfill Your Vow* and mark experience, take +1 experience.
  > - [ ] When you slay a beast or horror (at least formidable), you may take a trophy and choose one: Power a ritual (reroll any dice once for a ritual move) or Prove your worth (reroll any dice once when you *Sojourn*).

  ---

  > [!quote] Bonds
  > - Mara — Ashveil circle; Cadoc's sister, Cian's mother
  > - Dunmore circle — home, the people who trusted him
  > - Fen — fellow messenger from another circle; mutual road-debt

  ---

  ## Experience

  Unspent: 0 | Spent: 0

  ---

  ## Notes

  No iron blade. Carries a copper knife, a hunting spear, and a short bow.
  Bran is large enough to be unsettling in a doorway.
  ```

- [ ] **Step 2: Read back and verify**

  Confirm:
  - Five callout sections with correct callout types
  - Resources match last known state from session log: Health 5/5, Spirit 4/5, Supply 5/5, Momentum +5
  - Bran Health 3/4 present in Assets callout
  - Vow progress at 0/10 (Dangerous)
  - All three unlocked abilities marked `[x]` (Sharp, Wayfinder first, Slayer first)
  - All locked abilities marked `[ ]`

- [ ] **Step 3: No commit** — this file is outside the toolkit repo. No git action needed.
