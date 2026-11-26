"""The folder of saved campaigns: list them, create one, open one.

Each campaign is a subfolder named by an id made from its name.
"""
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..rng import DiceSource
from .campaign import CampaignPaths, create_campaign, load_json
from .engine import Engine, open_campaign
from .errors import CampaignFileError, PluginError
from .referee.base import Referee
from .registry import PluginFactory

__all__ = ["Library", "RefereeFactory"]

KINDS = ("ruleset", "generator", "module")

RefereeFactory = Callable[[Engine, CampaignPaths], Referee | None]
"""Builds the Referee for an opened campaign."""

START_MAP = {"areas": {"start": {"name": "Entrance", "x": 0, "y": 0, "w": 4, "h": 3}}}
GENERATOR_EXITS = [
    {"id": f"start-{side}", "area": "start", "side": side, "label": f"{label} exit"}
    for side, label in (("n", "North"), ("e", "East"), ("s", "South"), ("w", "West"))
]


class Library:
    def __init__(
        self,
        root: Path,
        factories: Mapping[str, PluginFactory],
        dice: Callable[[], DiceSource],
        referee_factory: RefereeFactory | None = None,
    ):
        self.root = Path(root)
        self._factories = factories
        self._dice = dice
        self._referee_factory = referee_factory

    def installed(self) -> dict[str, list[str]]:
        """The installed plugin names, by kind."""
        by_kind: dict[str, list[str]] = {kind: [] for kind in KINDS}
        for name, factory in sorted(self._factories.items()):
            by_kind.setdefault(factory().kind, []).append(name)
        return by_kind

    def campaigns(self) -> list[dict[str, Any]]:
        found = []
        for folder in sorted(self.root.iterdir()) if self.root.is_dir() else []:
            paths = CampaignPaths(folder)
            if not paths.settings.exists():
                continue
            settings = load_json(paths.settings)
            state = load_json(paths.state)
            found.append(
                {
                    "id": folder.name,
                    "name": settings.get("name", folder.name),
                    "plugins": settings.get("plugins", []),
                    "members": [m["name"] for m in state["party"]["members"]],
                    "session": state["session"],
                }
            )
        return found

    def create(self, name: str, ruleset: str, generators: list[str], module: str | None = None) -> str:
        """Create a campaign with an empty party and return its id. Plugins must be installed and of the right kind."""
        name = name.strip()
        campaign_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not campaign_id:
            raise CampaignFileError("a campaign needs a name")
        installed = self.installed()
        chosen = [(ruleset, "ruleset"), *[(g, "generator") for g in generators]]
        if module:
            chosen.append((module, "module"))
        for plugin, kind in chosen:
            if plugin not in installed[kind]:
                raise PluginError(f"'{plugin}' is not an installed {kind} (installed: {', '.join(installed[kind]) or 'none'})")
        map_data = {**START_MAP, "open_exits": GENERATOR_EXITS if generators else []}
        create_campaign(
            self.root / campaign_id, [name_ for name_, _ in chosen], map_data, "start", party=[], name=name
        )
        return campaign_id

    def open(self, campaign_id: str) -> tuple[Engine, Referee | None]:
        folder = self.root / campaign_id
        if "/" in campaign_id or campaign_id.startswith(".") or not CampaignPaths(folder).settings.exists():
            raise CampaignFileError(f"no campaign '{campaign_id}'")
        engine = open_campaign(folder, self._dice(), self._factories)
        referee = self._referee_factory(engine, CampaignPaths(folder)) if self._referee_factory else None
        return engine, referee
