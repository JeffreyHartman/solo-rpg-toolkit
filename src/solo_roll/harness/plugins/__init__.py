"""Plugins that ship with the toolkit, by the name a `campaign.json` uses."""
import os
from collections.abc import Mapping
from pathlib import Path

from ..registry import PluginFactory
from ...flextale_import import default_output_dir
from .flextale import FlextalePlugin
from .ose import OsePlugin

__all__ = ["BUILTIN_PLUGINS"]

BUILTIN_PLUGINS: Mapping[str, PluginFactory] = {
    "ose": OsePlugin,
    "flextale": lambda: FlextalePlugin(default_output_dir(os.environ, Path.home())),
}
