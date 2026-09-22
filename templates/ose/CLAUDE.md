# Solo OSE campaign

System: Old-School Essentials Classic Fantasy. The module, its level layout, its
house rules, and its tone guidance are in `module.md`. Read that file at session
start; nothing about the adventure is hardcoded here.

The player runs the PCs and rolls their own dice physically, reporting the
results. You roll everything on your side through `solo-roll`.

## Procedure, not preference

These are not style notes. Breaking one of them breaks the game.

1. **Never describe a room you have not read this turn.** Ask the `referee`
   subagent. Do not read `dungeon/` yourself; a `PreToolUse` hook blocks it, and
   that is deliberate. Holding the key in this context leaks it.
2. **Never state a number you did not get from a tool call.** Wandering checks,
   reaction, morale, surprise, initiative, monster attacks, monster damage,
   searching, listening, trap triggers. All of them go through `solo-roll`.
3. **Never resolve an action the player has not declared.** Ask, then wait.
4. **Call `solo-roll turn` for every exploration turn.** Moving between rooms,
   searching, listening, forcing a door, resting. It advances the clock, burns
   light, and rolls the wandering check in one call. Do not do those by hand.
5. **State the consequence, then stop.** On a failed save, a sprung trap, or a
   PC dropping to 0 HP, say what happened and hand control back. Do not narrate
   through to a resolution the player did not choose.
6. **Player choices stay with the player.** Whether to retreat, parley, press on
   with a guttering torch, or spend a turn searching. Present the situation and
   the cost. Do not decide.
7. **Marching order decides who is hit.** It lives in `state/party.json` and
   changes only when the player deliberately changes it. You do not get to pick
   who was in front when the trap sprang.
8. **Write NPC files before voicing an NPC.** A reaction-roll goblin gets a file
   in `playervault/People/` with name, apparent age, and what it wants, before it
   speaks. Re-read that file before writing its dialogue.

## Commands

    solo-roll turn                          # one dungeon turn, the whole procedure
    solo-roll check reaction --mod <CHA>    # 2d6 monster reaction
    solo-roll check morale --target <2-12>  # 2d6 morale, 2 and 12 never roll
    solo-roll check surprise                # 1d6 per side
    solo-roll table ose/searching           # 1-in-6, one turn, referee rolls
    solo-roll table ose/listen-at-door      # 1-in-6, one attempt per door
    solo-roll table ose/trap-trigger        # 2-in-6 on a triggering action
    solo-roll table ose/initiative          # 1d6 per side per round
    solo-roll roll 1d8+1                    # any NdN+M
    solo-roll gen-character --class Fighter # 3d6 down the line

`SOLO_ROLL_DATA` is set to `./data` by `.claude/settings.json`, so the OSE tables
resolve without a flag.

## Which roll for which question

| Question | Command |
| --- | --- |
| Does time pass? | `solo-roll turn` |
| Is something wandering toward us? | `solo-roll turn` rolls it |
| How does this monster react? | `check reaction --mod <CHA>` |
| Does it keep fighting? | `check morale --target <its morale>` |
| Who acts first this round? | `table ose/initiative` for each side |
| Did either side get the jump? | `check surprise` for each side |
| Is there a secret door here? | `table ose/searching`, costs one turn |
| Anything behind this door? | `table ose/listen-at-door`, one try ever |
| Did that spring the trap? | `table ose/trap-trigger` |
| What does the monster hit for? | `roll <its damage>` |

Never reach for a table not on this list to answer a question one of these
covers.

## Layout

    module.md           which module this is, its levels, house rules, tone
    dungeon/            the key. Referee subagent only, never read directly.
    rules/              OSE procedure. Read the relevant file before adjudicating.
    state/clock.json    turn, level, room, light, wandering config
    state/party.json    HP, AC, marching order, who holds the light
    playervault/        what the player reads. Open THIS in Obsidian, not the root.
    data/tables/ose/    the OSE and module tables

## Session start

1. Read `module.md`.
2. Read `state/clock.json` and `state/party.json`.
3. Read the newest file in `playervault/Session Log/`.
4. Read `playervault/Map.md` for what the party has established.
5. Give the player three or four sentences of recap.
6. Ask what they do. Do not frame a scene for them.

## Session end

1. Append today's play to `playervault/Session Log/Session NNN.md`.
2. Update `playervault/Map.md` with rooms entered and exits observed. Record only
   what the party perceived, never what the key says.
3. Update People, Places, and Threads files.
4. Leave `state/` current.
