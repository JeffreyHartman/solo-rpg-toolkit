"""Which map areas the fog-of-war viewer shows.

The viewer (`map/index.html` in an OSE campaign) polls `state/revealed.js` with a
fresh script tag, because a page opened from file:// cannot fetch JSON.
"""
import json
import re
from pathlib import Path

__all__ = ["RevealError", "load_revealed", "reveal", "hide"]

PREFIX = "window.REVEALED = "


class RevealError(Exception):
    """Raised when an area id is unknown or the map is not installed."""


def _sort_key(area_id: str) -> tuple:
    return (0, int(area_id), "") if area_id.isdigit() else (1, 0, area_id)


def load_revealed(path: Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    body = path.read_text().strip().removeprefix(PREFIX).rstrip(";").strip()
    data = json.loads(body)
    if isinstance(data, dict):
        data = [i for ids in data.values() for i in ids]
    return sorted({str(i) for i in data}, key=_sort_key)


def _write(path: Path, ids: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PREFIX + json.dumps(ids) + ";\n")


def _known_ids(areas_path: Path) -> set[str]:
    areas_path = Path(areas_path)
    if not areas_path.exists():
        raise RevealError(f"no map installed: {areas_path} not found")
    return {str(a["id"]) for a in json.loads(areas_path.read_text())["areas"]}


def reveal(path: Path, areas_path: Path, ids: list[str]) -> dict:
    known = _known_ids(areas_path)
    unknown = [i for i in ids if i not in known]
    if unknown:
        raise RevealError(f"unknown area id: {', '.join(unknown)}")
    current = load_revealed(path)
    added = sorted({i for i in ids if i not in current}, key=_sort_key)
    already = sorted({i for i in ids if i in current}, key=_sort_key)
    revealed = sorted(set(current) | set(ids), key=_sort_key)
    _write(path, revealed)
    return {"revealed": revealed, "added": added, "already": already}


def hide(path: Path, ids: list[str]) -> dict:
    revealed = [i for i in load_revealed(path) if i not in set(ids)]
    _write(path, revealed)
    return {"revealed": revealed}
