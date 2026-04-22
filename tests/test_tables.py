import json
from pathlib import Path

import pytest

from solo_roll.tables import (
    TableDataError,
    TableNotFoundError,
    load_table,
    roll_table,
)


DICE_MAP = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "tables").mkdir(parents=True)
    return root


def test_load_flat_table(data_dir: Path):
    _write_json(
        data_dir / "tables" / "sample.json",
        {
            "name": "sample",
            "display_name": "Sample",
            "dice": "d4",
            "source": "test",
            "entries": ["a", "b", "c", "d"],
        },
    )
    table = load_table("sample", data_dir)
    assert table["name"] == "sample"
    assert table["entries"] == ["a", "b", "c", "d"]
    assert table["dice"] == "d4"


def test_load_nested_table(data_dir: Path):
    _write_json(
        data_dir / "tables" / "nested" / "child.json",
        {"name": "child", "dice": "d4", "entries": ["w", "x", "y", "z"]},
    )
    table = load_table("nested/child", data_dir)
    assert table["name"] == "child"


def test_flat_table_entry_count_mismatch_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "bad.json",
        {"name": "bad", "dice": "d6", "entries": ["only", "three", "entries"]},
    )
    with pytest.raises(TableDataError):
        load_table("bad", data_dir)


def test_ranged_table_loads_and_validates_coverage(data_dir: Path):
    _write_json(
        data_dir / "tables" / "ranged.json",
        {
            "name": "ranged",
            "dice": "d10",
            "ranges": [
                {"min": 1, "max": 3, "result": "low"},
                {"min": 4, "max": 7, "result": "mid"},
                {"min": 8, "max": 10, "result": "high"},
            ],
        },
    )
    table = load_table("ranged", data_dir)
    assert len(table["ranges"]) == 3


def test_ranged_table_gap_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "gap.json",
        {
            "name": "gap",
            "dice": "d10",
            "ranges": [
                {"min": 1, "max": 3, "result": "low"},
                {"min": 5, "max": 10, "result": "high"},  # missing 4
            ],
        },
    )
    with pytest.raises(TableDataError):
        load_table("gap", data_dir)


def test_ranged_table_overlap_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "overlap.json",
        {
            "name": "overlap",
            "dice": "d10",
            "ranges": [
                {"min": 1, "max": 5, "result": "low"},
                {"min": 5, "max": 10, "result": "high"},  # 5 in both
            ],
        },
    )
    with pytest.raises(TableDataError):
        load_table("overlap", data_dir)


def test_table_with_both_entries_and_ranges_raises(data_dir: Path):
    _write_json(
        data_dir / "tables" / "both.json",
        {
            "name": "both",
            "dice": "d4",
            "entries": ["a", "b", "c", "d"],
            "ranges": [{"min": 1, "max": 4, "result": "x"}],
        },
    )
    with pytest.raises(TableDataError):
        load_table("both", data_dir)


def test_unknown_table_raises(data_dir: Path):
    with pytest.raises(TableNotFoundError):
        load_table("missing", data_dir)


def test_roll_table_flat_returns_index_and_result(data_dir: Path, scripted_dice):
    _write_json(
        data_dir / "tables" / "sample.json",
        {"name": "sample", "dice": "d4", "entries": ["a", "b", "c", "d"]},
    )
    result = roll_table("sample", data_dir, scripted_dice([3]))
    assert result["table"] == "sample"
    assert result["dice"] == "d4"
    assert result["roll"] == 3
    assert result["result"] == "c"


def test_roll_table_flat_edge_positions(data_dir: Path, scripted_dice):
    _write_json(
        data_dir / "tables" / "sample.json",
        {"name": "sample", "dice": "d4", "entries": ["a", "b", "c", "d"]},
    )
    assert roll_table("sample", data_dir, scripted_dice([1]))["result"] == "a"
    assert roll_table("sample", data_dir, scripted_dice([4]))["result"] == "d"


def test_dice_map_is_complete():
    for key, faces in DICE_MAP.items():
        assert int(key[1:]) == faces
