"""Typed exceptions for the harness. Only entry points translate them."""

__all__ = [
    "HarnessError",
    "CampaignFileError",
    "PluginError",
    "UnknownCommandError",
    "IllegalActionError",
]


class HarnessError(Exception):
    """Base class for every harness error."""


class CampaignFileError(HarnessError):
    """A campaign folder or one of its files is missing or invalid."""


class PluginError(HarnessError):
    """A plugin is unknown or registers something that clashes."""


class UnknownCommandError(HarnessError):
    """No plugin handles the command type."""


class IllegalActionError(HarnessError):
    """The command is known but the current state does not allow it."""
