from pathlib import Path

import pytest

from solo_roll import DEFAULT_DATA_DIR
from solo_roll.quicksets import (
    QuicksetDataError,
    QuicksetNotFoundError,
    load_quickset,
    run_quickset,
)


def test_load_npc_profile():
    qs = load_quickset("npc_profile", DEFAULT_DATA_DIR)
    assert qs["id"] == "npc_profile"
    assert len(qs["steps"]) == 8


def test_load_unknown_quickset_raises():
    with pytest.raises(QuicksetNotFoundError):
        load_quickset("bogus_profile", DEFAULT_DATA_DIR)


def test_every_shipped_quickset_loads_and_tables_resolve():
    root = DEFAULT_DATA_DIR / "quicksets"
    ids = sorted(p.stem for p in root.glob("*.json"))
    assert len(ids) >= 3
    from solo_roll.tables import load_table
    for qs_id in ids:
        qs = load_quickset(qs_id, DEFAULT_DATA_DIR)
        for step in qs["steps"]:
            load_table(step["table"], DEFAULT_DATA_DIR)


def test_run_quickset_emits_one_result_per_step(scripted_dice):
    qs = load_quickset("npc_profile", DEFAULT_DATA_DIR)
    dice = scripted_dice([1] * len(qs["steps"]))
    payload = run_quickset("npc_profile", DEFAULT_DATA_DIR, dice)
    assert payload["id"] == "npc_profile"
    assert payload["name"] == "NPC Profile"
    assert len(payload["steps"]) == len(qs["steps"])
    for result_step, spec_step in zip(payload["steps"], qs["steps"]):
        assert result_step["label"] == spec_step["label"]
        assert result_step["table"] == spec_step["table"]
        assert "roll" in result_step and "result" in result_step


def test_run_quickset_missing_table_raises(tmp_path):
    import json
    data = tmp_path / "data"
    (data / "quicksets").mkdir(parents=True)
    (data / "tables").mkdir(parents=True)
    (data / "quicksets" / "broken.json").write_text(json.dumps({
        "id": "broken",
        "name": "Broken",
        "description": "",
        "steps": [{"label": "X", "table": "does_not_exist"}],
    }))
    from solo_roll.rng import ScriptedDice
    with pytest.raises(QuicksetDataError):
        run_quickset("broken", data, ScriptedDice([1]))
