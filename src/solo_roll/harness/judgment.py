"""Judgment calls: a step in a procedure that needs a human decision.

A procedure handler raises one by returning `judgment_request(...)` as its last
event. The engine then either keeps a pending card in `state["judgments"]["pending"]`
and waits for the player, or, when the campaign setting gives the category to the
Referee, logs the suggestion as the decision with its reason. Either way the
engine runs the handler again with `command["judgment"] = {"category", "answer",
"data"}`, so the handler continues from the answer.

A pending card is `{id, category, question, suggestion, reason, options, resume}`.
`resume` is `{procedure, inputs, target, data}`, or None for a call the Referee
raised on its own.
"""
from typing import Any

from .registry import Event

__all__ = [
    "ASK",
    "JUDGMENT_OWNERS",
    "OWNER_LABELS",
    "REFEREE",
    "empty_judgments",
    "judgment_request",
    "judgment_text",
]

ASK = "ask"
"""Owner of a category where the player answers each judgment call."""

REFEREE = "referee"
"""Owner of a category where the Referee decides and the log records its reason."""

JUDGMENT_OWNERS = (ASK, REFEREE)

OWNER_LABELS = {ASK: "ask me", REFEREE: "Referee decides"}


def empty_judgments() -> dict[str, Any]:
    return {"pending": [], "next_id": 1}


def judgment_request(
    category: str,
    question: str,
    *,
    suggestion: str,
    reason: str,
    options: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> Event:
    """Ask the engine for a judgment call. Return it as the last event of a procedure handler.

    `suggestion` is the answer the Referee would give and `reason` says why. It
    is the card's suggestion and, when the Referee decides the category, the
    logged decision. `options` limits the answers. `data` comes back to the handler
    in `command["judgment"]["data"]`, so keep it JSON-ready.
    """
    return {
        "type": "judgment_request",
        "category": category,
        "question": question,
        "suggestion": suggestion,
        "reason": reason,
        "options": list(options or []),
        "data": dict(data or {}),
        "text": question,
    }


def judgment_text(card: dict[str, Any]) -> str:
    return f"Judgment call ({card['category']}): {card['question']} The Referee suggests: {card['suggestion']}."
