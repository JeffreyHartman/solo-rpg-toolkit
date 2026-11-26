"""The campaign folder: where the engine keeps its state and writes into the vault.

Layout under the campaign folder:
  campaign.json          plugin list
  engine/state.json      engine state, written only by the engine
  vault/State.md         read-only state note, rewritten after every command
  vault/Sessions/Raw/    one raw log per session
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import CampaignFileError

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

    def raw_log(self, session: int) -> Path:
        return self.vault / "Sessions" / "Raw" / f"Session {session:03d}.md"


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
) -> Path:
    """Write a new campaign folder with the party in `start`, the only known area."""
    paths = CampaignPaths(Path(root))
    if paths.settings.exists():
        raise CampaignFileError(f"a campaign already exists at {paths.root}")
    areas = {
        area_id: {**area, "known": area_id == start}
        for area_id, area in map_data["areas"].items()
    }
    if start not in areas:
        raise CampaignFileError(f"start area '{start}' is not on the map")
    write_json(paths.settings, {"plugins": list(plugins)})
    write_json(
        paths.state,
        {
            "session": 1,
            "party": {"members": list(party), "area": start},
            "map": {"areas": areas, "connections": list(map_data.get("connections", []))},
        },
    )
    return paths.root
