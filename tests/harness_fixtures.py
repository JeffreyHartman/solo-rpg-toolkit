"""A small hand-made map and a campaign built from it, for harness tests."""
from pathlib import Path

from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import Engine, open_campaign
from solo_roll.harness.plugins import BUILTIN_PLUGINS
from solo_roll.harness.plugins.ose import OsePlugin
from solo_roll.rng import DiceSource, ScriptedDice

HAND_MADE_MAP = {
    "areas": {
        "gate": {"name": "Gatehouse", "x": 0, "y": 4, "w": 4, "h": 3},
        "hall": {"name": "Long Hall", "x": 6, "y": 4, "w": 6, "h": 3},
        "crypt": {"name": "Crypt", "x": 6, "y": 0, "w": 4, "h": 3},
    },
    "connections": [
        {"id": "gate-hall", "a": "gate", "b": "hall", "label": "east arch"},
        {"id": "hall-crypt", "a": "hall", "b": "crypt", "label": "north stair"},
    ],
}

NO_WANDERING_PLUGINS = {**BUILTIN_PLUGINS, "ose": lambda: OsePlugin(wandering=None)}
"""The built-in plugins with no wandering checks, so a move consumes no dice."""


def make_campaign(root: Path) -> Path:
    return create_campaign(
        root / "campaign",
        plugins=["ose"],
        map_data=HAND_MADE_MAP,
        start="gate",
        party=[{"name": "Brannoc"}],
    )


def open_engine(campaign_dir: Path, dice: DiceSource | None = None) -> Engine:
    return open_campaign(campaign_dir, dice or ScriptedDice([]), NO_WANDERING_PLUGINS)
