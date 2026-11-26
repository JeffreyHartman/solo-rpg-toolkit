"""OSE narrative combat: side initiative, attack throws and damage, with no grid.

State lives in `state["combat"]`, which is None outside a fight:
`{area, outcome, round, phase, first, acted, monsters}`. `phase` is "party" or "monsters".
`monsters` holds `{id, name, hp, max_hp, ac, thac0, damage, status, generic}` where `status` is
"alive", "dead" or "fled".

Stat blocks come from `<data_dir>/bestiary.json`, keyed by monster name. The combat table's
result text names the monsters: the first bestiary key found in it picks the stat block, and
a leading number or number word gives the count. Text with no bestiary key becomes a
generic block (HD 1, AC 9, THAC0 19, 1d6) flagged `generic`.

Monster actions are chosen by another plugin. This module fires `monster_turn` for each
living monster and resolves the `monster_decision` event that answers it.
"""
import json
import re
from pathlib import Path
from typing import Any

from ....character import ability_modifier
from ....dice import parse_dice, roll_dice
from ...errors import IllegalActionError
from ... import party
from ...registry import AUTO, CONFIRM, Action, CommandContext, Event, Registry, Target

__all__ = ["combat_actions", "register"]

GENERIC = {"hd": 1, "ac": 9, "thac0": 19, "damage": "1d6"}
NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
PARTY_AC = 9
MEMBER_THAC0 = ((3, 19), (6, 17), (9, 14), (12, 12), (99, 10))
"""Attack value by level for every class, a simplification of the per-class OSE tables."""


def register(registry: Registry, data_dir: Path) -> None:
    registry.add_state_default("combat", lambda _state: None)
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
    registry.add_trigger("phase_changed", _phase_trigger)
    registry.add_trigger("round_ended", _round_trigger)
    registry.add_trigger("monster_decision", _decision_trigger)
    registry.add_action_provider(combat_actions)


# Starting a fight

def _start_trigger(data_dir: Path):
    def trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
        if state.get("combat"):
            return []
        outcomes = state["encounter"]["current"]["outcomes"]
        outcome = outcomes[event["outcome"]]
        monsters = _monsters(event["monsters"], _bestiary(data_dir), ctx)
        outcome["status"] = "started"
        state["combat"] = {"area": event["area"], "outcome": event["outcome"], "round": 0,
                           "phase": "party", "first": "party", "acted": [], "monsters": monsters}
        names = ", ".join(f"{m['name']} ({m['hp']} HP)" for m in monsters)
        return [{"type": "combat_started", "monsters": monsters, "text": f"Combat begins against {names}."},
                *_initiative(state, ctx)]
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
    combat.update(round=combat["round"] + 1, first=first, phase=first, acted=[])
    side = "The monsters" if first == "monsters" else "The party"
    return [
        {"type": "mechanics", "procedure": "initiative", "dice": "d6", "rolls": [party, monsters],
         "total": party, "result": first, "source": "OSE side initiative",
         "text": f"Round {combat['round']} initiative: party {party}, monsters {monsters}. {side} act first."},
        {"type": "phase_changed", "phase": first, "round": combat["round"],
         "text": f"Round {combat['round']}: {first} act."},
    ]


def _phase_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    combat = state.get("combat")
    if combat is None or event["phase"] != "monsters":
        return []
    out: list[Event] = [
        {"type": "monster_turn", "monster": m["id"], "text": f"{m['name']} {m['id']} acts."}
        for m in combat["monsters"] if m["status"] == "alive"
    ]
    out.append(_side_done(combat, "monsters"))
    return out


def _round_trigger(state: dict[str, Any], event: Event, ctx: CommandContext) -> list[Event]:
    if state.get("combat") is None:
        return []
    return _initiative(state, ctx)


def _side_done(combat: dict[str, Any], side: str) -> Event:
    """The event after a side finishes: the other side's phase, or the end of the round."""
    if side != combat["first"]:
        return {"type": "round_ended", "round": combat["round"], "text": f"Round {combat['round']} ends."}
    other = "party" if side == "monsters" else "monsters"
    combat.update(phase=other, acted=[])
    return {"type": "phase_changed", "phase": other, "round": combat["round"], "text": f"Round {combat['round']}: {other} act."}


# The party's actions

def attack(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """A melee attack throw: d20 plus the STR modifier at or over THAC0 minus the target's AC. A natural 20 hits and a 1 misses."""
    combat = _require_party_turn(state)
    inputs, target = command["inputs"], command["target"]
    member = _readymember(state, combat, inputs["member"])
    monster = _monster(combat, inputs["monster"])
    strength = ability_modifier(member.get("abilities", {}).get("STR", 10), "STR")
    natural = ctx.dice.roll(1, 20)
    hit = natural == 20 or (natural != 1 and natural + strength >= target["value"])
    result = "Hit" if hit else "Miss"
    events: list[Event] = [_card(
        "attack", "d20", [natural], natural + strength, result, "OSE",
        f"{member['name']} attacks {monster['name']} {monster['id']}: rolled {natural + strength}, "
        f"needs {target['value']}. {result}.")]
    if hit:
        events += _damage(monster, member.get("damage", "1d6"), strength, ctx, "monster")
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


def _attack_target(state: dict[str, Any], inputs: dict[str, Any]) -> Target | None:
    combat = _require_combat(state)
    monster = _monster(combat, inputs["monster"])
    member = party.member(state, inputs["member"])
    thac0 = _thac0(member)
    return {"value": thac0 - monster["ac"], "source": f"OSE attack throw: THAC0 {thac0} vs AC {monster['ac']}"}


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
    if monster["status"] != "alive":
        return []
    if event["kind"] == "flee":
        monster["status"] = "fled"
        return [{"type": "monster_fled", "monster": monster["id"], "text": f"{monster['name']} {monster['id']} flees."},
                *_end_if_over(state)]
    if event["kind"] != "attack":
        return [{"type": "monster_acted", "monster": monster["id"], "action": event["action"],
                 "text": f"{monster['name']} {monster['id']}: {event['action']}."}]
    member = party.member(state, event["target"])
    need = monster["thac0"] - member.get("ac", PARTY_AC)
    natural = ctx.dice.roll(1, 20)
    hit = natural == 20 or (natural != 1 and natural >= need)
    result = "Hit" if hit else "Miss"
    card = _card("monster_attack", "d20", [natural], natural, result, "OSE",
                 f"{monster['name']} {monster['id']} attacks {member['name']}: rolled {natural}, needs {need}. {result}.")
    card["target"] = {"value": need, "source": f"OSE attack throw: THAC0 {monster['thac0']} vs AC {member.get('ac', PARTY_AC)}"}
    events = [card]
    if hit:
        events += _damage(member, monster["damage"], 0, ctx, "member")
    return [*events, *_end_if_over(state)]


# Damage and the end of the fight

def _damage(victim: dict[str, Any], notation: str, bonus: int, ctx: CommandContext, side: str) -> list[Event]:
    rolled = roll_dice(parse_dice(notation), ctx.dice)
    amount = max(1, rolled["total"] + bonus)
    victim["hp"] = max(0, victim["hp"] - amount)
    name = victim.get("name")
    label = f"{name} {victim['id']}" if side == "monster" else name
    events: list[Event] = [
        _card("damage", rolled["dice"], rolled["rolls"], amount, f"{amount} damage", "OSE",
              f"{label} takes {amount} damage ({notation}{bonus:+d})." if bonus else f"{label} takes {amount} damage ({notation})."),
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
