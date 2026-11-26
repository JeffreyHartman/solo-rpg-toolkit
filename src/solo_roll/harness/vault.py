"""Engine-written vault files: the raw session log and the read-only `State.md`."""
from pathlib import Path
from typing import Any

from .campaign import CampaignPaths
from .registry import Event

__all__ = ["append_raw_log", "write_state_note"]


def append_raw_log(paths: CampaignPaths, session: int, events: list[Event]) -> None:
    path = paths.raw_log(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# Session {session:03d} raw log\n\n")
    with path.open("a") as log:
        for event in events:
            log.write(f"- {event.get('text') or event['type']}\n")


def write_state_note(paths: CampaignPaths, state: dict[str, Any]) -> None:
    path: Path = paths.state_note
    path.parent.mkdir(parents=True, exist_ok=True)
    here = state["party"]["area"]
    area_name = state["map"]["areas"][here]["name"]
    members = "\n".join(f"- {m['name']}" for m in state["party"]["members"])
    path.write_text(
        "---\ntype: state\nengine: true\n---\n"
        "# State\n\n"
        "> Written by the engine after every action. Edits here are overwritten.\n\n"
        f"Session: {state['session']}\n"
        f"Position: {area_name}\n\n"
        f"## Party\n\n{members}\n"
    )
