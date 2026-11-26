"""The `encounter_check` procedure: a check against the open trap or obstacle, with its DC from the DC table.

The FlexTale DC table gives a modifier that the d20 gets. A roll-under ability check
succeeds when `d20 + modifier <= score`, and a save when `d20 + modifier >= save`, so
the target number shown to the player is the base score or save minus the DC modifier.
"""
from typing import Any

from ....character import ABILITIES
from ...errors import IllegalActionError
from ...registry import CONFIRM, CommandContext, Event, Registry, Target
from ..ose.checks import SAVES

__all__ = ["register"]

AGAINST = list(ABILITIES) + list(SAVES)


def register(registry: Registry) -> None:
    registry.add_procedure(
        "encounter_check",
        encounter_check,
        CONFIRM,
        label="Check against the encounter",
        inputs={
            "member": {"type": "string", "label": "Character"},
            "against": {"type": "string", "label": "Ability or save", "choices": AGAINST},
            "modifier": {"type": "integer", "label": "Modifier added to the d20", "default": 0},
        },
        target=True,
    )
    registry.add_target_source("encounter_check", _dc_target)


def open_challenge(state: dict[str, Any]) -> dict[str, Any] | None:
    """The first trap or obstacle of the current encounter that still waits for a check."""
    current = state.get("encounter", {}).get("current")
    for outcome in (current or {}).get("outcomes", []):
        if outcome["kind"] in ("trap", "obstacle") and outcome["status"] == "open":
            return outcome
    return None


def _score(state: dict[str, Any], inputs: dict[str, Any]) -> tuple[dict[str, Any], int | None]:
    member = next((m for m in state["party"]["members"] if m["name"] == inputs["member"]), None)
    if member is None:
        raise IllegalActionError(f"no party member named '{inputs['member']}'")
    field = "abilities" if inputs["against"] in ABILITIES else "saves"
    return member, member.get(field, {}).get(inputs["against"])


def _dc_target(state: dict[str, Any], inputs: dict[str, Any]) -> Target | None:
    challenge = open_challenge(state)
    if challenge is None:
        return None
    member, base = _score(state, inputs)
    if base is None:
        return None
    dc = challenge["dc"]
    return {
        "value": base - dc["modifier"],
        "source": f"FlexTale DC table {dc['table']}: {dc['modifier']:+d} on the roll, applied to {member['name']}'s {inputs['against']}",
    }


def encounter_check(state: dict[str, Any], command: dict[str, Any], ctx: CommandContext) -> list[Event]:
    challenge = open_challenge(state)
    if challenge is None:
        raise IllegalActionError("no trap or obstacle waits for a check")
    inputs, target = command["inputs"], command["target"]
    member, _ = _score(state, inputs)
    under = inputs["against"] in ABILITIES
    rolls = [ctx.dice.roll(1, 20) for _ in range(1 if challenge["edge"] == 0 else 2)]
    # Advantage keeps the roll that helps: the lower for roll-under, the higher for roll-over.
    helps_low = under == (challenge["edge"] > 0)
    natural = min(rolls) if helps_low else max(rolls)
    total = natural + inputs["modifier"]
    if under:
        success = natural == 1 or (natural != 20 and total <= target["value"])
        need = f"{target['value']} or less"
    else:
        success = total >= target["value"]
        need = f"{target['value']} or more"
    result = "Success" if success else "Failure"
    challenge["status"] = "resolved" if success else "failed"
    return [
        {
            "type": "mechanics", "procedure": "encounter_check", "dice": "d20", "rolls": rolls,
            "total": total, "result": result, "source": "FlexTale",
            "text": f"{member['name']} checks {inputs['against']} against the {challenge['kind']}: rolled {total}, needs {need}. {result}.",
        }
    ]
