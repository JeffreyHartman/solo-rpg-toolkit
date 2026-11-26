"""The Referee adapter interface and the parts every adapter shares."""
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

from .events import RefereeEvent

__all__ = ["Referee", "TurnInput", "turn_prompt"]


@dataclass(frozen=True)
class TurnInput:
    player_input: str
    snapshot: dict[str, Any]
    prompt: str


class Referee(Protocol):
    """One Referee conversation for one campaign.

    `turn` reads a fresh state snapshot from the engine, sends it with the
    player's input, and yields `events.RefereeEvent`s until a `done` event.
    """

    def turn(self, player_input: str) -> AsyncIterator[RefereeEvent]: ...

    async def close(self) -> None: ...


def turn_prompt(player_input: str, snapshot: dict[str, Any]) -> str:
    """The user message for one turn: the state snapshot, then the player's input."""
    return f"<state>\n{json.dumps(snapshot, indent=2)}\n</state>\n\n{player_input}"
