"""The campaign folder: where the engine keeps its state and writes into the vault.

Layout under the campaign folder:
  campaign.json          plugin list
  engine/state.json      engine state, written only by the engine
  vault/                 the Obsidian vault, laid out by `vault.create_vault`
  vault/State.md         read-only state note, rewritten after every command
  vault/Sessions/Raw/    one raw log per session
  referee/               the Referee's secret notes, outside the vault
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import CampaignFileError
from .vault import create_vault, write_character_notes, write_state_note

__all__ = ["CampaignPaths", "create_campaign", "load_json", "write_json"]


@dataclass(frozen=True)
class CampaignPaths:
    root: Path

    @property
    def settings(self) -> Path:
        return self.root / "campaign.json"

    @property
    def state(self) -> Path:
        return self.root / "engine" / "state.json"

    @property
    def vault(self) -> Path:
        return self.root / "vault"

    @property
    def state_note(self) -> Path:
        return self.vault / "State.md"

    @property
    def referee(self) -> Path:
        return self.root / "referee"

    def raw_log(self, session: int) -> Path:
        return self.vault / "Sessions" / "Raw" / f"Session {session:03d}.md"

    def is_engine_written(self, resolved: Path) -> bool:
        """True for a vault file that only the engine writes. `resolved` must be a resolved path."""
        vault = self.vault.resolve()
        return resolved == vault / "State.md" or resolved.is_relative_to(vault / "Sessions" / "Raw")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CampaignFileError(f"not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise CampaignFileError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.replace(path)


def create_campaign(
    root: Path,
    plugins: list[str],
    map_data: dict[str, Any],
    start: str,
    party: list[dict[str, Any]],
    name: str | None = None,
) -> Path:
    """Write a new campaign folder with the party in `start`, the only known area.

    It also writes the vault and the referee folder. `name` defaults to the folder name.
    """
    paths = CampaignPaths(Path(root))
    if paths.settings.exists():
        raise CampaignFileError(f"a campaign already exists at {paths.root}")
    areas = {
        area_id: {**area, "known": area_id == start}
        for area_id, area in map_data["areas"].items()
    }
    if start not in areas:
        raise CampaignFileError(f"start area '{start}' is not on the map")
    write_json(paths.settings, {"plugins": list(plugins), "name": name or paths.root.name})
    state = {
        "session": 1,
        "party": {"members": list(party), "area": start},
        "map": {
            "areas": areas,
            "connections": list(map_data.get("connections", [])),
            "open_exits": list(map_data.get("open_exits", [])),
        },
    }
    write_json(paths.state, state)
    create_vault(paths, name or paths.root.name, list(plugins))
    write_state_note(paths, state)
    write_character_notes(paths, state)
    return paths.root
