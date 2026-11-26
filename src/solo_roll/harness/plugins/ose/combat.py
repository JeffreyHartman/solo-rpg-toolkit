"""OSE narrative combat: side initiative, attack throws and damage, with no grid.

State lives in `state["combat"]`, which is None outside a fight:
`{area, outcome, round, phase, first, acted, monsters}`. `outcome` is the index of the encounter outcome behind the fight, or None for a wandering encounter. `phase` is "party" or "monsters".
`monsters` holds `{id, name, hp, max_hp, ac, thac0, damage, status, generic}` where `status` is
"alive", "dead" or "fled".

Stat blocks come from `<data_dir>/bestiary.json`, keyed by monster name. The combat table's
result text names the monsters: the first bestiary key found in it picks the stat block, and
a leading number or number word gives the count. Text with no bestiary key becomes a
generic block (HD 1, AC 9, THAC0 19, 1d6) flagged `generic`.

This module fires `monster_turn` for each living monster and resolves the `monster_decision`
event that answers it. When a plugin triggers on `monster_turn` (the FlexTale Simple AI), it
decides. When none does, the monsters' turns wait in `combat["waiting"]` until the Referee picks
each one's action with the `monster_action` command (ADR 0004).
"""
import json
import re
from pathlib import Path
from typing import Any

from ....character import UNARMORED_AC, ability_modifier
from ....dice import parse_dice, roll_dice
from ...edits import edit_card
from ...errors import IllegalActionError
from ... import party
from ...registry import AUTO, CONFIRM, Action, CommandContext, Event, Registry, Target

__all__ = [
    "ASCENDING_AC", "DEFAULT_DAMAGE", "OPTIONAL_RULES", "VARIABLE_WEAPON_DAMAGE", "attack_bonus",
    "attack_target", "attack_throw", "combat_actions", "register", "weapon_damage",
]

GENERIC = {"hd": 1, "ac": 9, "thac0": 19, "damage": "1d6"}
NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
ASCENDING_AC = "ascending_ac"
VARIABLE_WEAPON_DAMAGE = "variable_weapon_damage"
OPTIONAL_RULES = (ASCENDING_AC, VARIABLE_WEAPON_DAMAGE)
"""The optional rules a campaign can choose. Each is a campaign setting in section `ose`, "on" or "off"."""
RULE_LABELS = {ASCENDING_AC: "Ascending Armour Class", VARIABLE_WEAPON_DAMAGE: "Variable Weapon Damage"}
DEFAULT_DAMAGE = "1d6"
MEMBER_THAC0 = ((3, 19), (6, 17), (9, 14), (12, 12), (99, 10))
"""Attack value by level for every class, a simplification of the per-class OSE tables."""


def register(registry: Registry, data_dir: Path) -> None:
    registry.add_state_default("combat", lambda _state: None)
    for rule in OPTIONAL_RULES:
        registry.add_setting("ose", rule, RULE_LABELS[rule], ["off", "on"], "off")
    registry.add_procedure("initiative", initiative, AUTO, label="Roll initiative")
    registry.add_procedure(
        "attack", attack, CONFIRM, label="Attack", target=True,
        inputs={"member": {"type": "string", "label": "Attacker"},
                "monster": {"type": "string", "label": "Monster id"}},
    )
    registry.add_target_source("attack", _attack_target)
    registry.add_procedure(
        "special_action", special_action, CONFIRM, label="Special action",
        inputs={"member": {"type": "string", "label": "Character"},
                "description": {"type": "string", "label": "What the character does"}},
    )
    registry.add_trigger("combat_encounter", _start_trigger(Path(data_dir)))
    registry.add_trigger("wandering_encounter", _wandering_trigger(Path(data_dir)))
    registry.add_trigger("phase_changed", _phase_trigger(registry))
    registry.add_command("monster_action", monster_action)
    registry.add_trigger("hp_changed", _hp_trigger)
    registry.add_trigger("monsters_done", _monsters_done_trigger)
    registry.add_trigger("round_ended", _round_trigger)
    registry.add_trigger("monster_decision", _decision_trigger)
    registry.add_action_provider(combat_actions)


# Starting a fight

def _start_trigger(data_dir: Path):
    def trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
        if state.get("combat"):
            return []
        monsters = _monsters(event["monsters"], _bestiary(data_dir), ctx)
        if event.get("outcome") is not None:
            state["encounter"]["current"]["outcomes"][event["outcome"]]["status"] = "started"
        state["combat"] = {"area": event["area"], "outcome": event.get("outcome"), "round": 0,
                           "phase": "party", "first": "party", "acted": [], "monsters": monsters}
        names = ", ".join(f"{m['name']} ({m['hp']} HP)" for m in monsters)
        return [{"type": "combat_started", "monsters": monsters, "text": f"Combat begins against {names}."},
                *_initiative(state, ctx)]
    return trigger


def _wandering_trigger(data_dir: Path):
    """A wandering encounter starts a fight in the party's area, with no encounter outcome behind it."""
    start = _start_trigger(data_dir)

    def trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
        return start(state, {"area": state["party"]["area"], "outcome": None, "monsters": event["monster"]}, ctx)
    return trigger


def _bestiary(data_dir: Path) -> dict[str, dict[str, Any]]:
    path = data_dir / "bestiary.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _monsters(text: str, bestiary: dict[str, dict[str, Any]], ctx: CommandContext) -> list[dict[str, Any]]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    count = 1
    if words and words[0].isdigit():
        count, words = int(words[0]), words[1:]
    elif words and words[0] in NUMBER_WORDS:
        count, words = NUMBER_WORDS[words[0]], words[1:]
    lowered = text.lower()
    key = next((k for k in bestiary if k in lowered), None)
    stats = bestiary[key] if key else GENERIC
    name = key or " ".join(words) or "monster"
    monsters = []
    for number in range(1, count + 1):
        hp = max(1, sum(ctx.dice.roll(1, 8) for _ in range(stats["hd"])))
        monsters.append({"id": f"m{number}", "name": name, "hp": hp, "max_hp": hp, "ac": stats["ac"],
                         "thac0": stats["thac0"], "damage": stats["damage"], "status": "alive",
                         "generic": key is None})
    return monsters


# Initiative and phases

def initiative(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """Roll a d6 for each side. The higher side acts first; on a tie the party acts first."""
    _require_combat(state)
    return _initiative(state, ctx)


def _initiative(state: dict[str, Any], ctx: CommandContext) -> list[Event]:
    combat = state["combat"]
    party, monsters = ctx.dice.roll(1, 6), ctx.dice.roll(1, 6)
    first = "monsters" if monsters > party else "party"
    combat.update(round=combat["round"] + 1, first=first, phase=first, acted=[], waiting=[])
    side = "The monsters" if first == "monsters" else "The party"
    return [
        {"type": "mechanics", "procedure": "initiative", "dice": "d6", "rolls": [party, monsters],
         "total": party, "result": first, "source": "OSE side initiative",
         "text": f"Round {combat['round']} initiative: party {party}, monsters {monsters}. {side} act first."},
        {"type": "phase_changed", "phase": first, "round": combat["round"],
         "text": f"Round {combat['round']}: {first} act."},
    ]


def _phase_trigger(registry: Registry):
    def trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
        combat = state.get("combat")
        if combat is None or event["phase"] != "monsters":
            return []
        living = [m for m in combat["monsters"] if m["status"] == "alive"]
        if registry.triggers.get("monster_turn"):
            out: list[Event] = [
                {"type": "monster_turn", "monster": m["id"], "text": f"{m['name']} {m['id']} acts."} for m in living
            ]
            return [*out, {"type": "monsters_done", "text": "The monsters have acted."}]
        combat["waiting"] = [m["id"] for m in living]
        return [
            {"type": "monster_turn", "monster": m["id"], "referee": True,
             "text": f"{m['name']} {m['id']} acts: the Referee picks its action with monster_action."}
            for m in living
        ]
    return trigger


def monster_action(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """The Referee's choice for a waiting monster: `kind` attack (at `target`), flee, or other.

    The `monster_decision` trigger resolves it, so an attack rolls with the engine's dice and the
    campaign's attack rules. The monsters' side ends when no monster is left waiting.
    """
    combat = _require_combat(state)
    monster_id = str(command.get("monster") or "")
    if monster_id not in combat.get("waiting", []):
        raise IllegalActionError(f"monster '{monster_id}' is not waiting for the Referee to act")
    monster = _monster(combat, monster_id)
    reason = str(command.get("reason") or "").strip()
    if not reason:
        raise IllegalActionError("a monster action needs a reason")
    kind = command.get("kind")
    if kind not in ("attack", "flee", "other"):
        raise IllegalActionError(f"kind must be attack, flee or other, got {kind!r}")
    action = str(command.get("action") or "").strip() or str(kind)
    target = str(command.get("target") or "") if kind == "attack" else None
    who = f"{monster['name']} {monster['id']}"
    if target is not None:
        member = party.member(state, target)
        if member.get("hp", 1) <= 0:
            raise IllegalActionError(f"{target} is down")
        did = f"{who} attacks {target}: {action}"
    else:
        did = f"{who} {'flees' if kind == 'flee' else 'acts'}: {action}"
    combat["waiting"].remove(monster_id)
    decision: Event = {"type": "monster_decision", "monster": monster_id, "kind": kind, "action": action,
                       "target": target, "text": f"{who} chooses: {action}."}
    return [edit_card(did, reason), decision, *_waiting_done(combat)]


def _waiting_done(combat: dict[str, Any]) -> list[Event]:
    """`monsters_done` once no living monster waits for the Referee."""
    alive = {m["id"] for m in combat["monsters"] if m["status"] == "alive"}
    combat["waiting"] = [m for m in combat.get("waiting", []) if m in alive]
    if combat["phase"] != "monsters" or combat["waiting"]:
        return []
    return [{"type": "monsters_done", "text": "The monsters have acted."}]


def _hp_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    """An edit that takes a member or a monster to 0 HP drops it, as damage does."""
    combat = state.get("combat")
    if event["hp"] > 0 or combat is None:
        return []
    if event["side"] == "monster":
        monster = _monster(combat, event["who"])
        monster["status"] = "dead"
        label = f"{monster['name']} {monster['id']}"
        events: list[Event] = [{"type": "monster_down", "monster": monster["id"], "text": f"{label} is dead."}]
    else:
        events = [{"type": "member_down", "member": event["who"], "text": f"{event['who']} falls."}]
    waited = bool(combat.get("waiting"))
    ended = _end_if_over(state)
    if ended or not waited:
        return [*events, *ended]
    return [*events, *_waiting_done(combat)]


def _monsters_done_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    combat = state.get("combat")
    return [] if combat is None else [_side_done(combat, "monsters")]


def _round_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    if state.get("combat") is None:
        return []
    return _initiative(state, ctx)


def _side_done(combat: dict[str, Any], side: str) -> Event:
    """The event after a side finishes: the other side's phase, or the end of the round."""
    if side != combat["first"]:
        return {"type": "round_ended", "round": combat["round"], "text": f"Round {combat['round']} ends."}
    other = "party" if side == "monsters" else "monsters"
    combat.update(phase=other, acted=[], waiting=[])
    return {"type": "phase_changed", "phase": other, "round": combat["round"], "text": f"Round {combat['round']}: {other} act."}


# The party's actions

def attack(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """A melee attack throw: d20 plus the STR modifier at or over THAC0 minus the target's AC. A natural 20 hits and a 1 misses."""
    combat = _require_party_turn(state)
    inputs, target = command["inputs"], command["target"]
    member = _readymember(state, combat, inputs["member"])
    monster = _monster(combat, inputs["monster"])
    strength = ability_modifier(member.get("abilities", {}).get("STR", 10), "STR")
    thac0 = _thac0(member)
    rules = optional_rules(ctx)
    throw = attack_throw(rules, thac0, monster["ac"], strength, ctx)
    natural, total, result = throw["natural"], throw["total"], "Hit" if throw["hit"] else "Miss"
    events: list[Event] = [_card(
        "attack", "d20", [natural], total, result, "OSE",
        f"{member['name']} attacks {monster['name']} {monster['id']}: rolled {total}, "
        f"needs {target['value']}. {result}.")]
    if throw["hit"]:
        notation, is_default = weapon_damage(rules, member)
        events += _damage(monster, notation, strength, ctx, "monster", is_default)
    events += _finish_party_action(state, combat, member)
    return events


def special_action(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """A non-attack action that takes the member's turn. Any effect runs through other procedures."""
    combat = _require_party_turn(state)
    member = _readymember(state, combat, command["inputs"]["member"])
    what = command["inputs"]["description"]
    event: Event = {"type": "special_action", "member": member["name"], "description": what,
                    "text": f"{member['name']}: {what}"}
    return [event, *_finish_party_action(state, combat, member)]


def _finish_party_action(state: dict[str, Any], combat: dict[str, Any], member: dict[str, Any]) -> list[Event]:
    combat["acted"].append(member["name"])
    ended = _end_if_over(state)
    if ended:
        return ended
    waiting = [m for m in party.standing(state) if m["name"] not in combat["acted"]]
    return [] if waiting else [_side_done(combat, "party")]


def _attack_target(state: dict[str, Any], inputs: dict[str, Any], ctx: CommandContext) -> Target | None:
    combat = _require_combat(state)
    monster = _monster(combat, inputs["monster"])
    member = party.member(state, inputs["member"])
    return attack_target(optional_rules(ctx), _thac0(member), monster["ac"], f"AC {monster['ac']}")


def optional_rules(ctx: CommandContext) -> frozenset[str]:
    """The optional rules the campaign settings turn on. A campaign with no setting uses none."""
    if ctx.settings is None:
        return frozenset()
    return frozenset(rule for rule in OPTIONAL_RULES if ctx.settings.get("ose", rule, "off") == "on")


def attack_bonus(rules: frozenset[str], thac0: int) -> int:
    """The attack bonus of an attacker with this THAC0: 19 minus THAC0 under ascending AC, 0 otherwise."""
    return 19 - thac0 if ASCENDING_AC in rules else 0


def attack_target(rules: frozenset[str], thac0: int, ac: int, defender: str | None = None) -> Target:
    """The number an attack throw must reach. Descending AC: THAC0 minus AC. Ascending AC: 19 minus AC.

    `ac` is the defender's descending AC, which is how every stat block and character stores it.
    Any attacker can use it, so a Referee-driven monster attack shares the rule. `defender` names
    the defender in the descending source text; the ascending source names the bonus and the AC.
    """
    if ASCENDING_AC in rules:
        bonus = attack_bonus(rules, thac0)
        return {"value": 19 - ac,
                "source": f"OSE attack throw, ascending AC: attack bonus {bonus:+d} vs ascending AC {19 - ac}"}
    return {"value": thac0 - ac,
            "source": f"OSE attack throw: THAC0 {thac0} vs {defender or f'AC {ac}'}"}


def attack_throw(rules: frozenset[str], thac0: int, ac: int, modifier: int, ctx: CommandContext) -> dict[str, Any]:
    """Roll a d20 attack throw. `modifier` is the ability modifier. A natural 20 hits and a natural 1 misses.

    Returns `{natural, total, need, hit}`; `total` includes the attack bonus under ascending AC.
    """
    natural = ctx.dice.roll(1, 20)
    total = natural + modifier + attack_bonus(rules, thac0)
    need = attack_target(rules, thac0, ac)["value"]
    return {"natural": natural, "total": total, "need": need,
            "hit": natural == 20 or (natural != 1 and total >= need)}


def weapon_damage(rules: frozenset[str], member: dict[str, Any]) -> tuple[str, bool]:
    """The damage die of a character's attack and whether it is the default.

    Under variable weapon damage the die comes from `member["weapon"]["damage"]`; with no weapon
    data, or without the rule, the attack uses `DEFAULT_DAMAGE`. The flag is True only when the
    rule asked for a weapon die and none was found.
    """
    if VARIABLE_WEAPON_DAMAGE not in rules:
        return DEFAULT_DAMAGE, False
    die = (member.get("weapon") or {}).get("damage")
    return (die, False) if die else (DEFAULT_DAMAGE, True)


def combat_actions(state: dict[str, Any]) -> list[Action]:
    combat = state.get("combat")
    if not combat or combat["phase"] != "party":
        return []
    return [
        {"id": f"attack:{member['name']}:{monster['id']}",
         "label": f"{member['name']} attacks {monster['name']} {monster['id']} ({monster['hp']} HP)",
         "command": {"type": "procedure", "name": "attack",
                     "inputs": {"member": member["name"], "monster": monster["id"]}}}
        for member in party.standing(state) if member["name"] not in combat["acted"]
        for monster in combat["monsters"] if monster["status"] == "alive"
    ]


# The monsters' actions

def _decision_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    combat = state.get("combat")
    if combat is None:
        return []
    monster = _monster(combat, event["monster"])
    if event["kind"] == "flee":
        monster["status"] = "fled"
        return [{"type": "monster_fled", "monster": monster["id"], "text": f"{monster['name']} {monster['id']} flees."},
                *_end_if_over(state)]
    if event["kind"] != "attack":
        return [{"type": "monster_acted", "monster": monster["id"], "action": event["action"],
                 "text": f"{monster['name']} {monster['id']}: {event['action']}."}]
    member = party.member(state, event["target"])
    ac = member.get("ac", UNARMORED_AC)
    rules = optional_rules(ctx)
    throw = attack_throw(rules, monster["thac0"], ac, 0, ctx)
    natural, need, hit = throw["natural"], throw["need"], throw["hit"]
    result = "Hit" if hit else "Miss"
    card = _card("monster_attack", "d20", [natural], throw["total"], result, "OSE",
                 f"{monster['name']} {monster['id']} attacks {member['name']}: rolled {throw['total']}, needs {need}. {result}.")
    card["target"] = attack_target(rules, monster["thac0"], ac, f"{member['name']}'s AC {ac}")
    events = [card]
    if hit:
        events += _damage(member, monster["damage"], 0, ctx, "member")
    return [*events, *_end_if_over(state)]


# Damage and the end of the fight

def _damage(victim: dict[str, Any], notation: str, bonus: int, ctx: CommandContext, side: str,
            is_default: bool = False) -> list[Event]:
    rolled = roll_dice(parse_dice(notation), ctx.dice)
    amount = max(1, rolled["total"] + bonus)
    victim["hp"] = max(0, victim["hp"] - amount)
    name = victim.get("name")
    default = ", default die, no weapon data" if is_default else ""
    label = f"{name} {victim['id']}" if side == "monster" else name
    events: list[Event] = [
        _card("damage", rolled["dice"], rolled["rolls"], amount, f"{amount} damage", "OSE",
              f"{label} takes {amount} damage ({notation}{bonus:+d}{default})." if bonus else f"{label} takes {amount} damage ({notation}{default})."),
        {"type": "damage", "target": victim["id"] if side == "monster" else name, "amount": amount,
         "hp": victim["hp"], "text": f"{label} has {victim['hp']} HP left."},
    ]
    if victim["hp"] == 0:
        if side == "monster":
            victim["status"] = "dead"
            events.append({"type": "monster_down", "monster": victim["id"], "text": f"{label} is dead."})
        else:
            events.append({"type": "member_down", "member": name, "text": f"{name} falls."})
    return events


def _end_if_over(state: dict[str, Any]) -> list[Event]:
    """Close the fight when no monster is alive (victory) or no member is standing (defeat)."""
    combat = state["combat"]
    if not party.standing(state):
        result = "defeat"
    elif not any(m["status"] == "alive" for m in combat["monsters"]):
        result = "victory"
    else:
        return []
    if combat["outcome"] is not None:
        state["encounter"]["current"]["outcomes"][combat["outcome"]]["status"] = "resolved"
    state["combat"] = None
    return [{"type": "combat_ended", "result": result, "text": f"Combat ends: {result}."}]


# Lookups

def _require_combat(state: dict[str, Any]) -> dict[str, Any]:
    combat = state.get("combat")
    if combat is None:
        raise IllegalActionError("there is no combat")
    return combat


def _require_party_turn(state: dict[str, Any]) -> dict[str, Any]:
    combat = _require_combat(state)
    if combat["phase"] != "party":
        raise IllegalActionError("it is not the party's turn in combat")
    return combat


def _readymember(state: dict[str, Any], combat: dict[str, Any], name: str) -> dict[str, Any]:
    member = party.member(state, name)
    if member.get("hp", 1) <= 0:
        raise IllegalActionError(f"{name} is down")
    if name in combat["acted"]:
        raise IllegalActionError(f"{name} has already acted this round")
    return member


def _monster(combat: dict[str, Any], monster_id: str) -> dict[str, Any]:
    for monster in combat["monsters"]:
        if monster["id"] == monster_id:
            if monster["status"] != "alive":
                raise IllegalActionError(f"monster {monster_id} is {monster['status']}")
            return monster
    raise IllegalActionError(f"no monster '{monster_id}' in this fight")


def _thac0(member: dict[str, Any]) -> int:
    if "thac0" in member:
        return member["thac0"]
    level = member.get("level", 1)
    return next(value for top, value in MEMBER_THAC0 if level <= top)


def _card(procedure: str, dice: str, rolls: list[int], total: int, result: str, source: str, text: str) -> Event:
    return {"type": "mechanics", "procedure": procedure, "dice": dice, "rolls": rolls,
            "total": total, "result": result, "source": source, "text": text}
