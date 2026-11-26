"""The campaign vault: its layout, and the files the engine writes into it.

The engine writes the raw session logs and the read-only `State.md`.
"""
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .registry import Event

if TYPE_CHECKING:
    from .campaign import CampaignPaths

__all__ = [
    "BLOCK_BEGIN",
    "BLOCK_END",
    "FOLDERS",
    "append_raw_log",
    "character_note",
    "create_vault",
    "find_block",
    "write_character_notes",
    "write_state_note",
]

BLOCK_BEGIN = "%% engine:begin %%"
BLOCK_END = "%% engine:end %%"
_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|#^\[\]]')

FOLDERS: dict[str, str] = {
    "Characters": "The party. One note per character: who they are, what they want.",
    "NPCs": "People met. One note per NPC: name, where met, what they want.",
    "Locations": "Places visited or heard of. One note per place.",
    "Threads": "Open leads, quests and mysteries. One note per thread.",
    "Lore & World": "Gods, factions, creatures and history. One note per subject.",
    "Sessions": "One clean note per session, written at End session.",
    "Sessions/Raw": "One raw log per session. The engine writes these; do not edit them.",
}


def append_raw_log(paths: "CampaignPaths", session: int, events: list[Event]) -> None:
    path = paths.raw_log(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# Session {session:03d} raw log\n\n")
        with (path.parent / "_index.md").open("a") as index:
            index.write(f"- [[Sessions/Raw/{path.stem}|{path.stem}]]\n")
    with path.open("a") as log:
        for event in events:
            log.write(f"- {event.get('text') or event['type']}\n")


def write_state_note(paths: "CampaignPaths", state: dict[str, Any]) -> None:
    path: Path = paths.state_note
    path.parent.mkdir(parents=True, exist_ok=True)
    here = state["party"]["area"]
    area_name = state["map"]["areas"][here]["name"]
    dungeon = _dungeon_section(state["dungeon"]) if "dungeon" in state else ""
    members = "\n".join(f"- {m['name']}" for m in state["party"]["members"])
    path.write_text(
        "---\ntype: state\nengine: true\n---\n"
        "# State\n\n"
        "> Written by the engine after every action. Edits here are overwritten.\n\n"
        f"Session: {state['session']}\n"
        f"Position: {area_name}\n\n"
        f"## Party\n\n{members}\n"
        f"{dungeon}"
    )


def _dungeon_section(dungeon: dict[str, Any]) -> str:
    light = ", ".join(
        f"{s['kind']} ({s['bearer']}), {s['turns_left']} turns left" for s in dungeon["light"]
    )
    return (
        "\n## Dungeon\n\n"
        f"Turn: {dungeon['turn']}\n"
        f"Light: {light or 'none (darkness)'}\n"
        f"Turns since rest: {dungeon['turns_since_rest']}\n"
    )


def character_note(paths: "CampaignPaths", name: str) -> Path:
    """The note of the party member called `name`. Characters Obsidian rejects in a name become `-`."""
    return paths.vault / "Characters" / f"{_UNSAFE_NAME.sub('-', name).strip() or 'Unnamed'}.md"


def find_block(text: str) -> tuple[int, int] | None:
    """Return the start and end offsets of the mechanical block, markers included, or None."""
    begin = text.find(BLOCK_BEGIN)
    end = text.find(BLOCK_END, begin + len(BLOCK_BEGIN)) if begin >= 0 else -1
    if end < 0:
        return None
    return begin, end + len(BLOCK_END)


def write_character_notes(paths: "CampaignPaths", state: dict[str, Any]) -> None:
    """Rewrite the mechanical block in each party member's note and keep the rest of the note.

    A missing note is created and linked from `Characters/_index.md`.
    """
    area = state["map"]["areas"][state["party"]["area"]]["name"]
    for member in state["party"]["members"]:
        note = character_note(paths, member["name"])
        block = _mechanical_block(member, area)
        if not note.exists():
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text(_character_note(member["name"], block))
            index = paths.vault / "Characters" / "_index.md"
            with index.open("a") as out:
                out.write(f"- [[{note.stem}]]\n")
            continue
        text = note.read_text()
        span = find_block(text)
        if span is None:
            text = text.rstrip("\n") + "\n\n" + block + "\n"
        else:
            text = text[: span[0]] + block + text[span[1] :]
        note.write_text(text)


def _mechanical_block(member: dict[str, Any], area: str) -> str:
    lines = [f"> - Position: {area}"]
    for key, value in member.items():
        if key != "name":
            lines.append(f"> - {key.replace('_', ' ').capitalize()}: {_plain(value)}")
    body = "\n".join(lines)
    return f"{BLOCK_BEGIN}\n> [!abstract] Mechanics (written by the engine)\n{body}\n{BLOCK_END}"


def _plain(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k} {_plain(v)}" for k, v in value.items())
    if isinstance(value, list):
        return ", ".join(_plain(v) for v in value)
    return str(value)


def _character_note(name: str, block: str) -> str:
    return (
        f"---\nname: {name}\ntype: character\nstatus: active\n---\n"
        f"# {name}\n\n{block}\n\n"
        "## Backstory\n\n## Appearance\n\n## Goals\n"
    )


def create_vault(paths: "CampaignPaths", name: str, plugins: list[str]) -> None:
    """Write the vault layout and make the referee folder.

    Notes that already exist are kept, so the owner's own writing survives a second call.
    """
    paths.referee.mkdir(parents=True, exist_ok=True)
    _write_new(paths.vault / "Home.md", _home(name))
    _write_new(paths.vault / "_Campaign.md", _campaign_note(name, plugins))
    _write_new(paths.vault / "Conventions.md", CONVENTIONS)
    for folder, purpose in FOLDERS.items():
        title = folder.rsplit("/", 1)[-1]
        _write_new(
            paths.vault / folder / "_index.md",
            f"---\ntype: index\nfolder: {folder}\n---\n# {title}\n\n{purpose}\n\n",
        )


def _write_new(path: Path, text: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _index_link(folder: str) -> str:
    return f"[[{folder}/_index|{folder.rsplit('/', 1)[-1]}]]"


def _home(name: str) -> str:
    folders = "\n".join(f"- {_index_link(folder)}" for folder in FOLDERS)
    return (
        "---\ntype: home\nrole: player\nstatus: active\n---\n"
        f"# {name}: Home\n\n"
        "- [[_Campaign|The campaign]]\n"
        "- [[State]]: the engine's live state (read-only)\n"
        "- [[Conventions]]: how the records in this vault are written\n\n"
        f"## Vault map\n\n{folders}\n"
    )


def _campaign_note(name: str, plugins: list[str]) -> str:
    plugin_list = ", ".join(plugins)
    return (
        f"---\ntype: campaign\nname: {name}\nplugins: [{plugin_list}]\nstatus: active\n---\n"
        f"# {name}\n\n"
        f"## The party\n\nSee {_index_link('Characters')}.\n\n"
        f"## Sessions\n\nSee {_index_link('Sessions')}.\n"
    )


CONVENTIONS = """---
type: conventions
---
# Conventions

How the records in this vault are written. The Referee follows these rules, and the owner can change them.

## Folders

- `Characters/`: the party. `type: character`.
- `NPCs/`: one note per person. `type: npc`, `status` (alive, dead, missing, unknown), `met` (the session, for example `Session 001`), `location` (a wikilink), `disposition` (friendly, neutral, hostile, unknown).
- `Locations/`: one note per place. `type: location`, `status` (visited, heard-of), `region`, `first-visit`.
- `Threads/`: one note per lead, quest or mystery. `type: thread`, `status` (open, resolved, abandoned), `started`.
- `Lore & World/`: one note per god, faction, creature or piece of history. `type: lore`, `first_heard`.
- `Sessions/`: one clean note per session, `Session NNN - Title.md`. `type: session`, `session`.
- `Sessions/Raw/`: the engine's raw logs. Read them; never edit them.

## Records

- The note's file name is the record's name, for example `NPCs/Old Mag.md`. Start it with YAML frontmatter that has `name` and `type`, then a `# Name` heading.
- Link records by name with wikilinks: `[[Old Mag]]`, `[[Long Hall]]`. Make a note for every name you link.
- When you make a record, add one line to its folder's `_index.md`: `- [[Name]] - one-line summary`.
- Write what play established. Keep secrets the player has not found (unfound traps, hidden plans) in the referee folder, not here.

## Engine-written parts

- `State.md` and `Sessions/Raw/` are written by the engine.
- Each character note has a mechanical block between `%% engine:begin %%` and `%% engine:end %%`. The engine rewrites it after every action; nobody else edits it.
- Live trackers (HP, AC, slots, torches, rations, coins, position, clocks) stay out of story notes. They live in `State.md` and the mechanical block.
"""
