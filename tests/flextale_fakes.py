"""Builds small fake FlexTale tables in a temp data folder for the encounter tests."""
import json
from pathlib import Path

from harness_fixtures import BUILTIN_PLUGINS

from solo_roll import OSE_DATA_DIR
from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.plugins.ose import OsePlugin
from solo_roll.harness.plugins.flextale import FlextalePlugin
from solo_roll.rng import ScriptedDice

MAP = {
    "areas": {"start": {"name": "Start", "x": 0, "y": 0, "w": 4, "h": 3}},
    "connections": [],
    "open_exits": [
        {"id": "e1", "area": "start", "side": "e", "label": "east door"},
        {"id": "e2", "area": "start", "side": "s", "label": "south door"},
    ],
}

# Each table maps a d20 range to a result. Roll 1-5 on the map table is a hall,
# 6-10 a chamber, 11-15 a dead end.
MAP_TABLE = [(1, 5, "A hall"), (6, 10, "A chamber"), (11, 15, "A dead end"), (16, 20, "A stair")]
ENCOUNTER = [
    (1, 8, "No Encounter"), (9, 10, "Trap"), (11, 12, "Obstacle"), (13, 14, "Secret"),
    (15, 17, "Combat Encounter"), (18, 18, "Roll Twice: more"), (19, 20, "Combat and Treasure: both"),
]
DEFAULT_TABLES: dict[str, list[tuple[int, int, str]]] = {
    "map-generator-a": MAP_TABLE,
    "hallway-encounter-a": ENCOUNTER,
    "chamber-encounter-a": ENCOUNTER,
    "dead-end-encounter-a": ENCOUNTER,
    "trap-a-osr": [(1, 5, "Dart: Save vs breath"), (6, 20, "Pit: Save vs death")],
    "obstacle-a": [(1, 20, "Rubble: Strength check")],
    "secret-door-a": [(1, 20, "A hidden latch")],
    "combat-encounter-a": [(1, 10, "Two fake goblins"), (11, 20, "One fake ogre")],
    "difficulty-class-a-osr": [
        (1, 1, "Susceptible: reroll with disadvantage"), (2, 10, "+2 on roll"),
        (11, 15, "Normal / roll"), (16, 19, "-2 on roll"), (20, 20, "Resistant: reroll with advantage"),
    ],
    "treasure-a": [
        (1, 1, "Contact Poison: Reroll."), (2, 2, "No treasure"), (3, 4, "Low Coin"),
        (5, 6, "Low Gems"), (7, 8, "Potion (roll on Spell)"), (9, 10, "Scroll (roll on Spell)"),
        (11, 12, "Additional Treasure: reroll twice"), (13, 20, "Favorable Treasure: reroll twice"),
    ],
    "treasure-low-coin-a-osr": [(1, 20, "1d4 gp / 2d4 gp / 3d4 gp / 4d4 gp")],
    "treasure-low-gem-a-osr": [(1, 20, "Agate: 1d4x; 2 gp")],
    "potion-a": [(1, 20, "Fake Healing: heals")],
}


def write_tables(data_dir: Path, tables: dict[str, list[tuple[int, int, str]]] | None = None, drop=()) -> None:
    for name, ranges in (DEFAULT_TABLES if tables is None else tables).items():
        if name in drop:
            continue
        path = data_dir / "tables" / "quickstart" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "name": f"quickstart/{name}", "dice": "d20",
            "ranges": [{"min": lo, "max": hi, "result": text} for lo, hi, text in ranges],
        }))


def make_engine(tmp_path: Path, rolls: list[int], drop=(), tables=None, party=None):
    data = tmp_path / "data"
    write_tables(data, tables, drop)
    root = create_campaign(
        tmp_path / "campaign", ["ose", "flextale"], MAP, "start",
        party or [{"name": "Brannoc", "abilities": {"STR": 14, "DEX": 12}, "saves": {"breath": 15, "death": 12}}],
    )
    factories = {**BUILTIN_PLUGINS, "ose": lambda: OsePlugin(OSE_DATA_DIR, wandering=None), "flextale": lambda: FlextalePlugin(data)}
    return open_campaign(root, ScriptedDice(rolls), factories)


def explore(engine, exit_id="e1"):
    return engine.act({"type": "explore", "exit": exit_id})
