"""The FlexTale generator plugin: explores an open exit by rolling the map generator table."""
from pathlib import Path
from typing import Any

from ....tables import TableNotFoundError, roll_table
from ...errors import FlextaleDataError, IllegalActionError
from ...mapstate import area
from ...registry import Action, CommandContext, Event, Registry
from . import checks, encounters, simple_ai, treasure
from .tabledata import CONTEXTS

__all__ = ["FlextalePlugin"]

MAP_TABLE = "quickstart/map-generator-a"
AREA_W, AREA_H, GAP = 4, 3, 2
OPPOSITE = {"n": "s", "s": "n", "e": "w", "w": "e"}


REFEREE_GUIDE = """## Generator: FlexTale

- When the party explores a new area, the engine rolls what it holds. Read `encounter.current` in the state and describe exactly that: do not add traps, obstacles, secrets or monsters.
- A trap or obstacle with status `open` waits for a check. Propose `encounter_check` for the character; the engine sets the target number from the DC table.
- Monsters act through the engine's Simple AI. Never decide what a monster does or how much damage it deals.
- Treasure comes only from the `treasure` procedure, and it changes the inventory in the state.
"""


class FlextalePlugin:
    name = "flextale"
    kind = "generator"

    def __init__(self, data_dir: Path, ruleset: str = "osr"):
        """`data_dir` holds the imported tables. `ruleset` is the importer's suffix for per-ruleset tables."""
        self._data_dir = Path(data_dir)
        self._ruleset = ruleset

    def register(self, registry: Registry) -> None:
        registry.add_command("explore", self._explore)
        registry.add_action_provider(_explore_actions)
        registry.add_referee_guide(REFEREE_GUIDE)
        checks.register(registry)
        treasure.register(registry, self._data_dir, self._ruleset)
        simple_ai.register(registry, self._data_dir)
        registry.add_state_default("encounter", encounters.initial_encounter)
        registry.add_setting("difficulty", "context", "Difficulty context", CONTEXTS, "A")
        registry.add_trigger("area_revealed", encounters.reveal_trigger(self._data_dir, self._ruleset))
        registry.add_trigger("turn", encounters.rest_trigger(self._data_dir, self._ruleset))
        registry.add_trigger("moved", encounters.backtrack_trigger(self._data_dir, self._ruleset))

    def _explore(
        self, state: dict[str, Any], command: dict[str, Any], ctx: CommandContext
    ) -> list[Event]:
        if state.get("combat"):
            raise IllegalActionError("the party cannot explore during combat")
        here = state["party"]["area"]
        exits = state["map"].setdefault("open_exits", [])
        used = next(
            (e for e in exits if e["id"] == command.get("exit") and e["area"] == here), None
        )
        if used is None:
            raise IllegalActionError(f"no unexplored exit '{command.get('exit')}' in '{here}'")
        try:
            rolled = roll_table(MAP_TABLE, self._data_dir, ctx.dice)
        except TableNotFoundError as exc:
            raise FlextaleDataError(
                f"FlexTale tables not found in {self._data_dir}; run `solo-flextale-import <pdf>` first"
            ) from exc

        exits.remove(used)
        source_area = area(state, here)
        new_id = _new_area_id(state)
        x, y = _place(state, source_area, used["side"])
        areas = state["map"]["areas"]
        areas[new_id] = {
            "name": f"Area {len(areas) + 1}",
            "description": rolled["result"],
            "x": x, "y": y, "w": AREA_W, "h": AREA_H,
            "known": True,
            "kind": _area_kind(rolled["result"]),
        }
        state["map"]["connections"].append(
            {"id": f"{here}-{new_id}", "a": here, "b": new_id, "label": used["label"]}
        )
        entry = OPPOSITE[used["side"]]
        for side in "nesw":
            if side != entry:
                exits.append(
                    {"id": f"{new_id}-{side}", "area": new_id, "side": side, "label": f"{_SIDE_NAME[side]} exit"}
                )
        state["party"]["area"] = new_id
        name = areas[new_id]["name"]
        return [
            {
                "type": "mechanics",
                "text": f"Map generator: rolled {rolled['roll']} on {rolled['dice']}: {rolled['result']}",
                "procedure": "map-generator",
                "dice": rolled["dice"],
                "rolls": rolled["rolls"],
                "total": rolled["roll"],
                "result": rolled["result"],
                "source": f"table {MAP_TABLE}",
            },
            {"type": "area_revealed", "area": new_id, "text": f"New area: {name}."},
            {
                "type": "moved",
                "from": here,
                "to": new_id,
                "text": f"The party moves from {source_area['name']} to {name}.",
            },
        ]


def _area_kind(result: str) -> str:
    low = result.lower()
    if "dead end" in low:
        return "dead-end"
    return "chamber" if "chamber" in low else "hall"


_SIDE_NAME = {"n": "north", "e": "east", "s": "south", "w": "west"}


def _explore_actions(state: dict[str, Any]) -> list[Action]:
    here = state["party"]["area"]
    return [
        {
            "id": f"explore:{e['id']}",
            "label": f"Explore the {e['label']}",
            "command": {"type": "explore", "exit": e["id"]},
        }
        for e in state["map"].get("open_exits", [])
        if e["area"] == here
    ]


def _new_area_id(state: dict[str, Any]) -> str:
    n = len(state["map"]["areas"]) + 1
    while f"area-{n}" in state["map"]["areas"]:
        n += 1
    return f"area-{n}"


def _place(state: dict[str, Any], src: dict[str, Any], side: str) -> tuple[int, int]:
    """Put a new area beside `src` on `side`, sliding it along the wall until it overlaps nothing."""
    x, y = src["x"], src["y"]
    if side == "e":
        x = src["x"] + src["w"] + GAP
    elif side == "w":
        x = src["x"] - AREA_W - GAP
    elif side == "s":
        y = src["y"] + src["h"] + GAP
    else:
        y = src["y"] - AREA_H - GAP
    step = (0, AREA_H + 1) if side in "ew" else (AREA_W + 1, 0)
    while any(_overlaps(x, y, other) for other in state["map"]["areas"].values()):
        x, y = x + step[0], y + step[1]
    return x, y


def _overlaps(x: int, y: int, other: dict[str, Any]) -> bool:
    return not (
        x + AREA_W <= other["x"]
        or other["x"] + other["w"] <= x
        or y + AREA_H <= other["y"]
        or other["y"] + other["h"] <= y
    )
