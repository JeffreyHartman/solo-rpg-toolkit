"""Plugins that ship with the toolkit, by the name a `campaign.json` uses."""
from collections.abc import Mapping

from ..registry import PluginFactory
from .ose import OsePlugin

__all__ = ["BUILTIN_PLUGINS"]

BUILTIN_PLUGINS: Mapping[str, PluginFactory] = {"ose": OsePlugin}
