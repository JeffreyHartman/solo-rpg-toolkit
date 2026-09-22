import json
import subprocess

import pytest

REACTION = {
    "name": "ose/reaction", "display_name": "Monster Reaction",
    "description": "OSE 2d6 monster reaction roll.", "dice": "2d6",
    "ranges": [
        {"min": -10, "max": 2, "result": "Hostile, attacks"},
        {"min": 3, "max": 5, "result": "Unfriendly, may attack"},
        {"min": 6, "max": 8, "result": "Neutral, uncertain"},
        {"min": 9, "max": 11, "result": "Indifferent, uninterested"},
        {"min": 12, "max": 30, "result": "Friendly, helpful"},
    ],
}
WANDER = {
    "name": "ose/w", "description": "d", "dice": "d6",
    "entries": ["bat", "spider", "goblins", "jelly", "omen", "raid"],
}


@pytest.fixture
def data_dir(tmp_path):
    root = tmp_path / "data"
    for name, payload in (("ose/reaction", REACTION), ("ose/w", WANDER)):
        path = root / "tables" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    return root


def run(*args):
    proc = subprocess.run(["solo-roll", *args], capture_output=True, text=True)
    return proc


class TestRoll:
    def test_multiple_dice(self):
        out = json.loads(run("roll", "3d6").stdout)
        assert len(out["rolls"]) == 3
        assert 3 <= out["total"] <= 18

    def test_modifier(self):
        out = json.loads(run("roll", "1d8+2").stdout)
        assert out["modifier"] == 2
        assert 3 <= out["total"] <= 10

    def test_rejects_garbage(self):
        proc = run("roll", "banana")
        assert proc.returncode == 1
        assert "invalid dice" in proc.stderr


class TestCheck:
    def test_surprise_is_a_d6(self):
        out = json.loads(run("check", "surprise").stdout)
        assert 1 <= out["roll"] <= 6
        assert out["surprised"] is (out["roll"] <= 2)

    def test_morale_needs_a_target(self):
        proc = run("check", "morale")
        assert proc.returncode == 1

    def test_morale_twelve_never_rolls(self):
        out = json.loads(run("check", "morale", "--target", "12").stdout)
        assert out["checked"] is False
        assert out["holds"] is True

    def test_reaction_reads_the_table(self, data_dir):
        out = json.loads(run("check", "reaction", "--data", str(data_dir)).stdout)
        assert out["table"] == "ose/reaction"
        assert 2 <= out["natural"] <= 12

    def test_reaction_modifier_is_reported(self, data_dir):
        out = json.loads(run("check", "reaction", "--mod", "2", "--data", str(data_dir)).stdout)
        assert out["modifier"] == 2
        assert out["roll"] == out["natural"] + 2


class TestTurn:
    def test_init_writes_a_clock(self, tmp_path, data_dir):
        clock = tmp_path / "clock.json"
        out = json.loads(run("turn", "--init", "--state", str(clock),
                             "--data", str(data_dir)).stdout)
        assert out["state"]["turn"] == 0
        assert clock.exists()

    def test_advance_increments_and_persists(self, tmp_path, data_dir):
        clock = tmp_path / "clock.json"
        run("turn", "--init", "--state", str(clock), "--data", str(data_dir))
        run("turn", "--state", str(clock), "--data", str(data_dir))
        out = json.loads(run("turn", "--state", str(clock), "--data", str(data_dir)).stdout)
        assert out["turn"] == 2
        assert json.loads(clock.read_text())["turn"] == 2

    def test_dry_run_does_not_persist(self, tmp_path, data_dir):
        clock = tmp_path / "clock.json"
        run("turn", "--init", "--state", str(clock), "--data", str(data_dir))
        run("turn", "--state", str(clock), "--dry-run", "--data", str(data_dir))
        assert json.loads(clock.read_text())["turn"] == 0

    def test_burns_a_torch_over_six_turns(self, tmp_path, data_dir):
        clock = tmp_path / "clock.json"
        run("turn", "--init", "--state", str(clock), "--data", str(data_dir))
        state = json.loads(clock.read_text())
        state["light"] = [{"kind": "torch", "bearer": "Hana", "turns_left": 6}]
        clock.write_text(json.dumps(state))
        for _ in range(5):
            out = json.loads(run("turn", "--state", str(clock), "--data", str(data_dir)).stdout)
            assert out["in_darkness"] is False
        out = json.loads(run("turn", "--state", str(clock), "--data", str(data_dir)).stdout)
        assert out["in_darkness"] is True
        assert out["light_expired"] == [{"kind": "torch", "bearer": "Hana"}]

    def test_missing_state_file_errors(self, tmp_path, data_dir):
        proc = run("turn", "--state", str(tmp_path / "nope.json"), "--data", str(data_dir))
        assert proc.returncode == 1
        assert "not found" in proc.stderr


class TestGenCharacter:
    def test_rolls_six_abilities(self):
        out = json.loads(run("gen-character").stdout)
        assert len(out["abilities"]) == 6
        assert all(3 <= v <= 18 for v in out["abilities"].values())

    def test_class_sets_hit_die(self):
        out = json.loads(run("gen-character", "--class", "Magic-User").stdout)
        assert out["hit_die"] == "d4"
        assert out["hit_points"] >= 1

    def test_rejects_unknown_class(self):
        proc = run("gen-character", "--class", "Bard")
        assert proc.returncode == 1
