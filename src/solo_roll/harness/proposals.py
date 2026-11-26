"""Proposals: a procedure with its inputs and target number, waiting for the player to answer.

The engine keeps pending proposals in `state["proposals"]["pending"]`. A
proposal is `{id, procedure, label, inputs, target, reason}`, where `target` is
`{value, source, editable}` or None. `editable` is True when no plugin data gives
the target number, so the target is a proposal input the player can change.
"""
from typing import Any

from .errors import IllegalActionError
from .registry import Procedure, Registry, Target

__all__ = ["ANSWER_VERBS", "ANSWERS", "empty_proposals", "prepare", "proposal_text"]

ANSWERS = ("confirm", "change", "reject")
ANSWER_VERBS = {"confirm": "confirms", "change": "changes", "reject": "rejects"}

SET_BY = {"referee": "the Referee", "player": "the player"}


def empty_proposals() -> dict[str, Any]:
    return {"pending": [], "next_id": 1}


def prepare(
    registry: Registry,
    procedure: Procedure,
    state: dict[str, Any],
    raw: dict[str, Any],
    set_by: str,
    fallback: Target | None = None,
) -> tuple[dict[str, Any], Target | None]:
    """Check the inputs of a procedure and find its target number.

    `set_by` ("referee" or "player") names who gave a `target` input, for the
    target source. `fallback` is the target to keep when no plugin data gives
    one and `raw` has no `target`. Raises `IllegalActionError` for a bad input,
    for a `target` input when plugin data gives the target, and for a missing target.
    """
    raw = dict(raw)
    given = raw.pop("target", None)
    inputs = _check_inputs(procedure, raw)
    if not procedure.target:
        if given is not None:
            raise IllegalActionError(f"{procedure.name} rolls against no target number")
        return inputs, None
    for source in registry.target_sources.get(procedure.name, []):
        found = source(state, inputs)
        if found is not None:
            if given is not None:
                raise IllegalActionError(
                    f"the target number of {procedure.name} comes from {found['source']}, not from an input"
                )
            return inputs, {"value": found["value"], "source": found["source"], "editable": False}
    if given is None and fallback is not None:
        return inputs, dict(fallback)
    if given is None:
        raise IllegalActionError(
            f"{procedure.name} needs a target number: no plugin data gives one, so pass a 'target' input"
        )
    value = _as_int("target", given)
    return inputs, {"value": value, "source": f"proposal input, set by {SET_BY[set_by]}", "editable": True}


def proposal_text(proposal: dict[str, Any]) -> str:
    parts = ", ".join(f"{name} {value}" for name, value in proposal["inputs"].items())
    text = f"Proposal: {proposal['label']}"
    if parts:
        text += f" ({parts})"
    target = proposal.get("target")
    if target:
        text += f", target {target['value']} from {target['source']}"
    return text + f". Reason: {proposal['reason']}"


def _check_inputs(procedure: Procedure, raw: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(raw) - set(procedure.inputs))
    if unknown:
        raise IllegalActionError(f"{procedure.name} has no input {', '.join(unknown)}")
    inputs: dict[str, Any] = {}
    for name, spec in procedure.inputs.items():
        if name in raw:
            value = raw[name]
        elif "default" in spec:
            value = spec["default"]
        else:
            raise IllegalActionError(f"{procedure.name} needs the input '{name}'")
        if spec.get("type") == "integer":
            value = _as_int(name, value)
        else:
            value = str(value)
        if "choices" in spec and value not in spec["choices"]:
            raise IllegalActionError(f"{procedure.name}: {name} must be one of {', '.join(map(str, spec['choices']))}")
        inputs[name] = value
    return inputs


def _as_int(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise IllegalActionError(f"{name} must be a whole number")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise IllegalActionError(f"{name} must be a whole number, got {value!r}") from exc
