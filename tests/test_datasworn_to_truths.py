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
