"""The Referee adapter interface and the parts every adapter shares."""
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

from ..campaign import CampaignPaths
from ..vault import session_note
from .events import RefereeEvent

__all__ = ["Referee", "TurnInput", "session_opening", "turn_prompt"]


@dataclass(frozen=True)
class TurnInput:
    player_input: str
    snapshot: dict[str, Any]
    prompt: str
    conversation: int = 1


class Referee(Protocol):
    """The Referee of one campaign, one conversation per session.

    `turn` reads a fresh state snapshot from the engine, sends it with the
    player's input, and yields `events.RefereeEvent`s until a `done` event.
    The first turn of each conversation also sends `session_opening`.
    """

    def turn(self, player_input: str) -> AsyncIterator[RefereeEvent]: ...

    async def close(self) -> None: ...

    async def new_session(self) -> None:
        """End the conversation. The next turn starts a new one from the engine state and the vault."""

    async def set_model(self, model: str) -> None:
        """Use `model` from the next turn on, in the same conversation."""

    async def set_effort(self, effort: str) -> None:
        """Use `effort` from the next turn on, in the same conversation."""

    async def compact(self) -> None:
        """Summarize the conversation now. The harness never compacts unless the player asks."""

    async def context_usage(self) -> int | None:
        """Tokens in the current conversation, or None before its first turn."""


def turn_prompt(player_input: str, snapshot: dict[str, Any], opening: str | None = None) -> str:
    """The user message for one turn: the session opening on a conversation's first turn, the state snapshot, then the player's input."""
    head = f"<session>\n{opening}\n</session>\n\n" if opening else ""
    return f"{head}<state>\n{json.dumps(snapshot, indent=2)}\n</state>\n\n{player_input}"


def session_opening(paths: CampaignPaths, session: int) -> str:
    """What the first turn of a conversation tells the Referee: it remembers nothing, so it reads the vault."""
    reads = ["`Home.md`", "`_Campaign.md`"]
    earlier = [n for n in (session_note(paths, s) for s in range(session - 1, 0, -1)) if n is not None]
    if earlier:
        reads.append(f"`{earlier[0].relative_to(paths.vault).as_posix()}`")
    elif session > 1:
        reads.append("the raw logs in `Sessions/Raw/`")
    return (
        f"Session {session} starts. This is a new conversation: you remember nothing from earlier sessions. "
        f"Before you narrate, learn the story from the vault: read {', '.join(reads)}, "
        "and follow their links to the records you need."
    )
