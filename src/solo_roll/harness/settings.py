"""The campaign settings store: `section -> key -> value`, saved to `settings.json` on every change.

Sections in use: `confirm` (procedure name to confirm level) and `referee`
(`model`, `effort`, and the context `budget` in tokens). The store does
not check values; the owner of each section does that before it calls `set`.
"""
import copy
from pathlib import Path
from typing import Any

from .campaign import load_json, write_json

__all__ = ["CampaignSettings", "REFEREE_DEFAULTS", "REFEREE_EFFORTS", "REFEREE_MODELS"]

REFEREE_MODELS = ("sonnet", "opus", "haiku")
REFEREE_EFFORTS = ("low", "medium", "high", "xhigh", "max")
REFEREE_DEFAULTS: dict[str, Any] = {"model": "sonnet", "effort": "low", "budget": 60_000}


class CampaignSettings:
    def __init__(self, path: Path):
        self._path = Path(path)
        self._data: dict[str, dict[str, Any]] = load_json(self._path) if self._path.exists() else {}

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._data.get(section, {}).get(key, default)

    def section(self, section: str) -> dict[str, Any]:
        return copy.deepcopy(self._data.get(section, {}))

    def set(self, section: str, key: str, value: Any) -> None:
        self._data.setdefault(section, {})[key] = value
        write_json(self._path, self._data)
