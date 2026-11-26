"""Plugins that ship with the toolkit, by the name a `campaign.json` uses."""
from pathlib import Path

from ..registry import PluginFactory
from .flextale import FlextalePlugin
from .ose import OsePlugin
from .ose.combat import OPTIONAL_RULES

__all__ = ["builtin_plugins"]


def builtin_plugins(flextale_data: Path, ose_data: Path) -> dict[str, PluginFactory]:
    """The shipped plugin factories. `flextale_data` is the folder the FlexTale importer wrote."""
    return {
        "ose": lambda: OsePlugin(ose_data, optional_rules=OPTIONAL_RULES),
        "flextale": lambda: FlextalePlugin(flextale_data),
    }
