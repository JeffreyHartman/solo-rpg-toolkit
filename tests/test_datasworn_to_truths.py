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
