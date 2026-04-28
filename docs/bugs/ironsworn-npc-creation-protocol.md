# Bug: NPC Creation — Missing Demographics + Behavioral Application

## Observed

**Session 1 / ironsworn-test1:**
- Cian (`People/Cian.md`) has `Age: Around seven` in the file.
- During play, the LLM had Cian deliver dialogue in adult cadence/vocabulary. A 7-year-old who just experienced
  something traumatic doesn't speak like a composed adult — he'd be terse, fragmented, possibly nonverbal.
- Fen's NPC file was created without a gender field. The player defaulted to mentally reading Fen as male.
  Gender was assigned later.

## Root cause

Two separate failures:

1. **Creation gap:** NPC files don't consistently get all demographic fields filled on creation.
   Age and gender are sometimes left blank or approximated.
2. **Application gap:** Even when demographics exist in the file, the LLM doesn't appear to be reading
   and applying them when writing NPC dialogue and behavior.

## Expected behavior

When a new NPC is introduced (whether named in advance or improvised during play):

1. **Immediately create or update their `People/<Name>.md` file** with:
   - Name
   - Age or age range (child / teen / young adult / middle-aged / elderly, or specific if known)
   - Gender / pronouns
   - Relation to PC
   - Circle (if known)
   - One-paragraph physical/behavioral impression
   - First appearance note

2. **Apply demographics when writing NPC voice.** Before writing any NPC dialogue or action:
   - Check their file for age and any noted personality traits.
   - A 7-year-old traumatized child → short sentences, maybe silence, maybe a single strange phrase.
     Not adult analysis.
   - An elderly council member → different cadence than a young warrior.

## Fix needed

Add an NPC creation checklist to `skills/ironsworn/SKILL.md` (or a new `skills/ironsworn/npcs.md`
reference file) with explicit required fields and a reminder to apply demographics to dialogue/behavior.

Something like:

```
### When a new NPC appears
1. Create `<PLAYER_VAULT_PATH>/People/<Name>.md` immediately.
2. Fill: Name, Age/range, Gender/pronouns, Relation, Circle (if known), brief impression.
3. Before writing their dialogue or action, re-read their file — age and personality are constraints,
   not decoration. A child does not speak like an adult. A taciturn soldier does not monologue.
```

## Files involved

- `skills/ironsworn/SKILL.md` — add NPC creation protocol
- Optionally: `skills/ironsworn/npcs.md` — extracted NPC reference (see architecture note)

## See also

`docs/bugs/ironsworn-skill-architecture.md` — if NPC protocol lives in a separate `npcs.md`, transcript evidence suggests it will not be read on demand. Either keep this in SKILL.md (always loaded), or add explicit "before creating an NPC, read `npcs.md`" trigger language.
