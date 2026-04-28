# Architecture: Ironsworn Skill — Reference Files Not Being Read

## NEW finding (2026-04-27, from transcript analysis)

Tool-call audit of session 3 JSONL (`~/.claude/projects/-home-jeff-rpg-solo-ai-vaults-ironsworn-test1/5497f208-*.jsonl`):

- `skills/ironsworn/SKILL.md` — loaded at session start (auto via Skill tool).
- `skills/ironsworn/moves.md` — **read ONCE, late in the session, only after the journey/Pay-the-Price errors started.** Not consulted before move calls.
- `skills/ironsworn/oracles.md` — **never read at all.**

Conclusion: the reference files are reactive-only. The LLM was running every move call from memory + SKILL.md context, not from the reference files. This means improving `moves.md` text alone will not fix the bugs — the LLM has to actually read it, and currently does not.

## Implications for the other bug files

All four behavior bugs need to be re-read with this in mind:

- `ironsworn-journey-progress-track.md` — fixing journey procedure in `moves.md` is necessary but insufficient. SKILL.md must mandate the read.
- `ironsworn-pay-the-price-procedure.md` — same. Pay the Price procedure in `moves.md` is invisible to the LLM unless triggered to load it.
- `ironsworn-weak-hit-cost-options.md` — cost menus in `moves.md` are invisible by default. LLM improvises costs from SKILL.md outcome text.
- `ironsworn-npc-creation-protocol.md` — if NPC protocol goes in a new `npcs.md`, will hit the same problem.
- `oracle-selection-meaning-pair-vs-elements.md` — oracle selection guide in `oracles.md` will be invisible. Must live in SKILL.md or be explicitly loaded.

## Original observation (still valid)

`skills/ironsworn/SKILL.md` is growing. As of 2026-04-27 it covers:
- Core loop and rolling protocol
- Outcome interpretation
- Live stat tracking (including progress tracks)
- GM principles
- Mythic GME coexistence rules
- Setting truths / session zero
- Solo journaler coexistence rules
- Scene framing
- Vow vault overlay

Risk: long SKILL.md = lower per-section attention. Long monolithic `moves.md` = LLM less willing to load it for one move.

## Proposed structure: per-move files

```
skills/ironsworn/
  SKILL.md                       # core loop + MANDATORY read instructions
  moves/
    face-danger.md
    secure-an-advantage.md
    gather-information.md
    heal.md
    resupply.md
    make-camp.md
    undertake-a-journey.md
    reach-your-destination.md
    pay-the-price.md
    endure-harm.md
    endure-stress.md
    companion-takes-a-hit.md
    sojourn.md
    compel.md
    swear-an-iron-vow.md
    fulfill-your-vow.md
    enter-the-fray.md
    strike.md
    clash.md
    battle.md
    end-the-fight.md
  oracles/
    selecting-an-oracle.md       # meaning-pair vs elements vs fate-check
    yes-no.md
    descriptive-elements.md
    plot-turn.md
  npcs.md                        # NPC creation protocol
  progress-tracks.md             # journey, fight, vow track procedures (cross-cuts moves)
  character-template.md          # already exists
```

Each move file: trigger, stat, all outcomes, full cost menus, follow-on move triggers, narrative principles for that specific move.

## Key change to SKILL.md core loop

```markdown
## Core loop

1. Player describes intent.
2. Identify the triggered move.
3. **Read `moves/<move-slug>.md` BEFORE presenting the roll. Do not run a move from memory — even if you "know" it. The cost menus and procedures live in those files for a reason.**
4. Present the roll using the template.
5. Player reports outcome (miss / weak / strong).
6. **Re-consult the move file for the matching outcome — costs are player choices on weak hits, follow-on moves trigger automatically on misses.**
7. Apply mechanics, narrate, hand back control.
```

The "BEFORE" language is doing the work. Generic "see moves.md for details" lost this session.

## Tradeoffs

**Pro per-move:**
- Smaller scoped read → LLM more likely to actually load it
- Cost menus and procedures all in one focused file per move
- Hard to skip a step when the file is structured as a checklist
- Each move file becomes a unit-testable contract (skill-content tests can verify shape)

**Con per-move:**
- More files to maintain
- SKILL.md must list all move slugs so LLM knows what's available
- File-name slug discipline matters (player says "I'll undertake a journey" → LLM must map to `undertake-a-journey.md`)

**Mitigation for the slug problem:** SKILL.md includes a small move-trigger → file-slug table near the top.

## Why python script for moves is wrong

Considered: `scripts/datasworn_to_moves.py` analogous to `datasworn_to_truths.py`. Reject.

Truths are static data — the converter just reformats. Moves need *prompting* — each move file is a procedure for the LLM, including cost menus, narrative principles, "do not narrate through this," etc. Datasworn JSON has the mechanical text but not the agent prompting. Hand-write per-move files; cross-check mechanical text against datasworn JSON when the reference dump is available, but don't auto-generate.

## Status

**Promoted from observation to actionable.** Per-move file restructure is now the core fix for sub-project 5.6, not a follow-up. Without it, none of the other bug-file fixes will land — the LLM never reads the file.

Recommended sequence:
1. Restructure to per-move files (this bug).
2. Populate journey, Pay the Price, weak-hit costs in those files (other bugs).
3. Add NPC protocol + oracle selection (in their files or SKILL.md per per-file decisions).
4. Add mandatory-read language to SKILL.md core loop.
5. Skill-content test pin asserting each move file exists with required sections.
