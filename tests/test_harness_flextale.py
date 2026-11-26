"""Tests for the FlexTale generator plugin: exploring an open exit through the engine."""
import json
from pathlib import Path

import pytest

from solo_roll.harness.campaign import create_campaign
from solo_roll.harness.engine import open_campaign
from solo_roll.harness.errors import FlextaleDataError, IllegalActionError
from solo_roll.harness.plugins import BUILTIN_PLUGINS
from solo_roll.harness.plugins.flextale import FlextalePlugin
from solo_roll.rng import ScriptedDice

TABLE = "quickstart/map-generator-a"
FAKE_RESULT = "A fake chamber with a fake fountain"

MAP = {
    "areas": {"start": {"name": "Start", "x": 0, "y": 0, "w": 4, "h": 3}},
    "connections": [],
    "open_exits": [
        {"id": "e1", "area": "start", "side": "e", "label": "east door"},
        {"id": "e2", "area": "start", "side": "s", "label": "south door"},
    ],
}


def write_fake_table(data_dir: Path) -> None:
    path = data_dir / "tables" / "quickstart" / "map-generator-a.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "name": TABLE,
                "dice": "d20",
                "ranges": [
                    {"min": 1, "max": 10, "result": "A fake corridor"},
                    {"min": 11, "max": 20, "result": FAKE_RESULT},
                ],
            }
        )
    )


def make_engine(tmp_path: Path, rolls: list[int], data_dir: Path | None = None):
    data = data_dir or tmp_path / "data"
    root = create_campaign(
        tmp_path / "campaign", ["ose", "flextale"], MAP, "start", [{"name": "Brannoc"}]
    )
    factories = {**BUILTIN_PLUGINS, "flextale": lambda: FlextalePlugin(data)}
    return open_campaign(root, ScriptedDice(rolls), factories)


def explore_ids(engine):
    return [a["id"] for a in engine.available_actions() if a["command"]["type"] == "explore"]


def test_every_open_exit_of_the_current_area_is_an_explore_action(tmp_path):
    engine = make_engine(tmp_path, [])
    assert explore_ids(engine) == ["explore:e1", "explore:e2"]


def test_explore_places_a_connected_area_and_moves_the_party_in(tmp_path):
    write_fake_table(tmp_path / "data")
    engine = make_engine(tmp_path, [15])
    engine.act({"type": "explore", "exit": "e1"})
    state = engine.state()
    new_id = state["party"]["area"]
    assert new_id != "start"
    new = state["map"]["areas"][new_id]
    assert new["known"] is True
    assert new["description"] == FAKE_RESULT
    assert {"a": "start", "b": new_id} == {
        k: v for k, v in state["map"]["connections"][0].items() if k in ("a", "b")
    }
    assert state["map"]["connections"][0]["label"] == "east door"
    assert [e["id"] for e in state["map"]["open_exits"] if e["area"] == "start"] == ["e2"]


def test_new_area_sits_beside_the_exit_without_overlap(tmp_path):
    write_fake_table(tmp_path / "data")
    engine = make_engine(tmp_path, [15, 15])
    engine.act({"type": "explore", "exit": "e1"})
    first = engine.state()["party"]["area"]
    state = engine.state()
    a, s = state["map"]["areas"][first], state["map"]["areas"]["start"]
    assert a["x"] >= s["x"] + s["w"]
    engine.act({"type": "move", "to": "start"})
    engine.act({"type": "explore", "exit": "e2"})
    state = engine.state()
    rects = [(r["x"], r["y"], r["w"], r["h"]) for r in state["map"]["areas"].values()]
    for i, p in enumerate(rects):
        for q in rects[i + 1 :]:
            assert p[0] + p[2] <= q[0] or q[0] + q[2] <= p[0] or p[1] + p[3] <= q[1] or q[1] + q[3] <= p[1]


def test_new_area_offers_exits_on_its_other_sides(tmp_path):
    write_fake_table(tmp_path / "data")
    engine = make_engine(tmp_path, [15])
    engine.act({"type": "explore", "exit": "e1"})
    state = engine.state()
    here = state["party"]["area"]
    sides = {e["side"] for e in state["map"]["open_exits"] if e["area"] == here}
    assert "w" not in sides and sides


def test_explore_emits_a_mechanics_card_with_dice_result_and_source(tmp_path):
    write_fake_table(tmp_path / "data")
    engine = make_engine(tmp_path, [15])
    events = engine.act({"type": "explore", "exit": "e1"})
    card = next(e for e in events if e["type"] == "mechanics")
    assert card["procedure"] == "map-generator"
    assert card["dice"] == "d20"
    assert card["rolls"] == [15]
    assert card["total"] == 15
    assert card["result"] == FAKE_RESULT
    assert card["source"] == f"table {TABLE}"
    assert card["text"]
    assert [e["type"] for e in events][-2:] == ["area_revealed", "moved"] or "moved" in [
        e["type"] for e in events
    ]


def test_missing_data_raises_an_error_naming_the_import_command(tmp_path):
    engine = make_engine(tmp_path, [15])
    with pytest.raises(FlextaleDataError, match="solo-flextale-import"):
        engine.act({"type": "explore", "exit": "e1"})
    assert engine.state()["party"]["area"] == "start"


def test_explore_of_an_exit_elsewhere_is_illegal(tmp_path):
    write_fake_table(tmp_path / "data")
    engine = make_engine(tmp_path, [15])
    with pytest.raises(IllegalActionError):
        engine.act({"type": "explore", "exit": "nope"})


def test_builtin_flextale_factory_uses_the_default_data_folder():
    plugin = BUILTIN_PLUGINS["flextale"]()
    assert plugin.name == "flextale" and plugin.kind == "generator"
