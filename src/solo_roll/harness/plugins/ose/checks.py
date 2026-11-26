"""OSE ability checks and saving throws as procedures that roll a d20 against a target number.

The target comes from the character's `abilities` or `saves` in the engine
state when the character has them; otherwise it is a proposal input.
"""
from typing import Any

from ....character import ABILITIES, SAVES
from ... import party
from ...registry import CONFIRM, CommandContext, Event, Registry, Target

__all__ = ["SAVES", "register"]

MEMBER = {"type": "string", "label": "Character"}
MODIFIER = {"type": "integer", "label": "Modifier added to the d20", "default": 0}


def register(registry: Registry) -> None:
    registry.add_procedure(
        "ability_check",
        ability_check,
        CONFIRM,
        label="Ability check",
        inputs={"member": MEMBER, "ability": {"type": "string", "label": "Ability", "choices": list(ABILITIES)},
                "modifier": MODIFIER},
        target=True,
    )
    registry.add_target_source("ability_check", _score_target("abilities", "ability", "{name}'s {key} score"))
    registry.add_procedure(
        "saving_throw",
        saving_throw,
        CONFIRM,
        label="Saving throw",
        inputs={"member": MEMBER, "save": {"type": "string", "label": "Save", "choices": list(SAVES)},
                "modifier": MODIFIER},
        target=True,
    )
    registry.add_target_source("saving_throw", _score_target("saves", "save", "{name}'s save vs {key}"))


def ability_check(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """OSE optional rule: d20 plus modifier at or under the score succeeds; a natural 1 always succeeds and a 20 always fails."""
    inputs, target = command["inputs"], command["target"]
    member = party.member(state, inputs["member"])
    natural = ctx.dice.roll(1, 20)
    total = natural + inputs["modifier"]
    success = natural == 1 or (natural != 20 and total <= target["value"])
    result = "Success" if success else "Failure"
    return [_card("ability_check", natural, total, result,
                  f"{member['name']} checks {inputs['ability']}: rolled {total}, needs {target['value']} or less. {result}.")]


def saving_throw(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    """d20 plus modifier at or over the save target succeeds."""
    inputs, target = command["inputs"], command["target"]
    member = party.member(state, inputs["member"])
    natural = ctx.dice.roll(1, 20)
    total = natural + inputs["modifier"]
    result = "Success" if total >= target["value"] else "Failure"
    return [_card("saving_throw", natural, total, result,
                  f"{member['name']} saves vs {inputs['save']}: rolled {total}, needs {target['value']} or more. {result}.")]


def _score_target(field: str, input_name: str, source: str):
    def find(state: dict[str, Any], inputs: dict[str, Any]) -> Target | None:
        member = party.member(state, inputs["member"])
        key = inputs[input_name]
        value = member.get(field, {}).get(key)
        if value is None:
            return None
        return {"value": value, "source": source.format(name=member["name"], key=key)}

    return find


def _card(procedure: str, natural: int, total: int, result: str, text: str) -> Event:
    return {
        "type": "mechanics",
        "procedure": procedure,
        "dice": "d20",
        "rolls": [natural],
        "total": total,
        "result": result,
        "source": "OSE",
        "text": text,
    }
