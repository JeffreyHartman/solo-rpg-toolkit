"""A small hand-made map and a campaign built from it, for harness tests."""
from pathlib import Path

from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import Engine, open_campaign
from solo_roll.harness.plugins import builtin_plugins
from solo_roll.rng import DiceSource, ScriptedDice

BUILTIN_PLUGINS = builtin_plugins(Path("/nonexistent/flextale-data"))
"""The shipped plugins, with a FlexTale data folder that does not exist. Tests that roll FlexTale tables replace it."""

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


def make_campaign(root: Path) -> Path:
    return create_campaign(
        root / "campaign",
        plugins=["ose"],
        map_data=HAND_MADE_MAP,
        start="gate",
        party=[{"name": "Brannoc"}],
    )


def open_engine(campaign_dir: Path, dice: DiceSource | None = None) -> Engine:
    return open_campaign(campaign_dir, dice or ScriptedDice([]), BUILTIN_PLUGINS)
