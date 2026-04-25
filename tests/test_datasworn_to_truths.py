import json
from pathlib import Path

import pytest

import datasworn_to_truths as dt


def _write_json(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "datasworn.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_truths_returns_mapping(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {"truths": {"iron": {"name": "Iron"}}})
    result = dt.load_truths(src)
    assert result == {"iron": {"name": "Iron"}}


def test_load_truths_raises_when_key_missing(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {"oracles": {}})
    with pytest.raises(ValueError, match="missing top-level 'truths'"):
        dt.load_truths(src)


def test_load_truths_raises_when_empty(tmp_path: Path) -> None:
    src = _write_json(tmp_path, {"truths": {}})
    with pytest.raises(ValueError, match="'truths' is empty"):
        dt.load_truths(src)


def test_format_option_basic() -> None:
    opt = {"min": 1, "max": 33, "description": "The Old World fell."}
    assert dt.format_option(opt, "A") == (
        "### Option A (1\u201333)\n"
        "\n"
        "The Old World fell.\n"
    )


def test_format_option_includes_quest_seed() -> None:
    opt = {
        "min": 34,
        "max": 67,
        "description": "Iron is cursed.",
        "quest_starter": "Find the unbound forge.",
    }
    out = dt.format_option(opt, "B")
    assert out == (
        "### Option B (34\u201367)\n"
        "\n"
        "Iron is cursed.\n"
        "\n"
        "**Quest seed:** Find the unbound forge.\n"
    )


def test_format_option_omits_quest_seed_when_absent() -> None:
    opt = {"min": 68, "max": 100, "description": "No seed here."}
    out = dt.format_option(opt, "C")
    assert "Quest seed" not in out
    assert out.endswith("No seed here.\n")


def test_format_truth_emits_heading_and_attribution() -> None:
    truth = {
        "_id": "classic/truths/iron",
        "name": "Iron",
        "options": [
            {"min": 1, "max": 50, "description": "First."},
            {"min": 51, "max": 100, "description": "Second."},
        ],
    }
    out = dt.format_truth("iron", truth)
    assert out.startswith("## Iron\n")
    assert "Datasworn id `classic/truths/iron`" in out
    assert "### Option A (1\u201350)" in out
    assert "### Option B (51\u2013100)" in out


def test_format_truth_letters_increment_for_more_options() -> None:
    truth = {
        "_id": "classic/truths/example",
        "name": "Example",
        "options": [
            {"min": 1, "max": 25, "description": "One."},
            {"min": 26, "max": 50, "description": "Two."},
            {"min": 51, "max": 75, "description": "Three."},
            {"min": 76, "max": 100, "description": "Four."},
        ],
    }
    out = dt.format_truth("example", truth)
    assert "### Option A " in out
    assert "### Option B " in out
    assert "### Option C " in out
    assert "### Option D " in out


def _truth(name: str, idx: int) -> dict:
    return {
        "_id": f"classic/truths/{name.lower().replace(' ', '_')}",
        "name": name,
        "options": [
            {"min": 1, "max": 100, "description": f"Only option for {name}."},
        ],
    }


def test_format_document_book_order() -> None:
    truths = {
        "iron": _truth("Iron", 1),
        "old_world": _truth("The Old World", 0),
    }
    out = dt.format_document(truths)
    old_pos = out.index("## The Old World")
    iron_pos = out.index("## Iron")
    assert old_pos < iron_pos


def test_format_document_includes_attribution_header() -> None:
    out = dt.format_document({"iron": _truth("Iron", 0)})
    assert out.startswith("# Ironsworn Setting Truths")
    assert "CC-BY-4.0" in out
    assert "https://ironswornrpg.com" in out


def test_format_document_appends_unknown_truths_alphabetically() -> None:
    truths = {
        "zeta": _truth("Zeta", 99),
        "alpha": _truth("Alpha", 98),
        "iron": _truth("Iron", 1),
    }
    out = dt.format_document(truths)
    iron_pos = out.index("## Iron")
    alpha_pos = out.index("## Alpha")
    zeta_pos = out.index("## Zeta")
    assert iron_pos < alpha_pos < zeta_pos


def test_format_document_idempotent() -> None:
    truths = {"iron": _truth("Iron", 1), "old_world": _truth("The Old World", 0)}
    assert dt.format_document(truths) == dt.format_document(truths)
