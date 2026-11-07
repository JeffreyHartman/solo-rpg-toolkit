"""Tests for `solo_roll.reveal` and `solo-roll reveal`: which map areas the fog
viewer shows, as written to the `state/revealed.js` file it polls."""
import json
import subprocess

import pytest

from solo_roll.reveal import RevealError, hide, load_revealed, reveal

AREAS = {"map": {"src": "map.png"}, "areas": [
    {"id": "1"}, {"id": "2"}, {"id": "10"}, {"id": "c1"}, {"id": "s1"},
]}


@pytest.fixture
def camp(tmp_path):
    (tmp_path / "map").mkdir()
    (tmp_path / "map/areas.json").write_text(json.dumps(AREAS))
    (tmp_path / "state").mkdir()
    return tmp_path


def paths(camp):
    return camp / "state/revealed.js", camp / "map/areas.json"


class TestReveal:
    def test_starts_empty_when_no_file_exists(self, camp):
        state, _ = paths(camp)
        assert load_revealed(state) == []

    def test_writes_a_script_the_viewer_can_load(self, camp):
        state, areas = paths(camp)
        reveal(state, areas, ["2"])
        text = state.read_text()
        assert text.startswith("window.REVEALED = ")
        assert json.loads(text.removeprefix("window.REVEALED = ").rstrip(";\n")) == ["2"]

    def test_adds_to_what_is_already_revealed(self, camp):
        state, areas = paths(camp)
        reveal(state, areas, ["1"])
        out = reveal(state, areas, ["c1", "1"])
        assert out == {"revealed": ["1", "c1"], "added": ["c1"], "already": ["1"]}

    def test_sorts_numbers_before_prefixed_ids(self, camp):
        state, areas = paths(camp)
        out = reveal(state, areas, ["s1", "10", "c1", "2"])
        assert out["revealed"] == ["2", "10", "c1", "s1"]

    def test_rejects_an_unknown_id_without_writing(self, camp):
        state, areas = paths(camp)
        with pytest.raises(RevealError, match="99"):
            reveal(state, areas, ["1", "99"])
        assert not state.exists()

    def test_errors_when_no_map_is_installed(self, tmp_path):
        with pytest.raises(RevealError, match="areas"):
            reveal(tmp_path / "revealed.js", tmp_path / "map/areas.json", ["1"])

    def test_reads_the_grouped_form_the_viewer_also_accepts(self, camp):
        state, _ = paths(camp)
        state.write_text('window.REVEALED = {"level1": ["1"], "level2": ["c1"]};\n')
        assert load_revealed(state) == ["1", "c1"]


class TestHide:
    def test_removes_an_id(self, camp):
        state, areas = paths(camp)
        reveal(state, areas, ["1", "2"])
        out = hide(state, ["2"])
        assert out["revealed"] == ["1"]
        assert load_revealed(state) == ["1"]


def run(*args, cwd):
    return subprocess.run(["solo-roll", *args], capture_output=True, text=True, cwd=cwd)


class TestCli:
    def test_reveals_from_the_campaign_root(self, camp):
        out = json.loads(run("reveal", "1", "c1", cwd=camp).stdout)
        assert out["added"] == ["1", "c1"]
        assert load_revealed(camp / "state/revealed.js") == ["1", "c1"]

    def test_no_ids_lists_what_is_revealed(self, camp):
        run("reveal", "2", cwd=camp)
        assert json.loads(run("reveal", cwd=camp).stdout)["revealed"] == ["2"]

    def test_hide_flag_removes(self, camp):
        run("reveal", "1", "2", cwd=camp)
        out = json.loads(run("reveal", "--hide", "1", cwd=camp).stdout)
        assert out["revealed"] == ["2"]

    def test_unknown_id_exits_1(self, camp):
        proc = run("reveal", "nope", cwd=camp)
        assert proc.returncode == 1
        assert "nope" in proc.stderr
