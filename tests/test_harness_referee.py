"""Tests for the Referee adapter seam, driven through `ScriptedReferee`.

The path guard and the engine tools run here exactly as the Agent SDK adapter
runs them, so these tests cover the vault boundary without the real SDK.
"""
import asyncio

import pytest
from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.referee import Call, Say, ScriptedReferee


def run_turn(referee, text="I look around."):
    async def collect():
        return [event async for event in referee.turn(text)]

    return asyncio.run(collect())


@pytest.fixture
def campaign(tmp_path):
    return make_campaign(tmp_path)


@pytest.fixture
def paths(campaign):
    return CampaignPaths(campaign)


@pytest.fixture
def engine(campaign):
    return open_engine(campaign)


def scripted(engine, paths, *turns):
    return ScriptedReferee(engine, paths, turns=list(turns))


def tool_results(events):
    return [e for e in events if e["type"] == "tool_result"]


def test_a_turn_streams_text_and_ends_with_done(engine, paths):
    referee = scripted(engine, paths, [Say("The wind "), Say("howls.")])

    events = run_turn(referee)

    assert [(e["type"], e.get("text")) for e in events] == [
        ("text", "The wind "),
        ("text", "howls."),
        ("done", None),
    ]


def test_each_turn_receives_the_player_text_and_a_fresh_state_snapshot(engine, paths):
    referee = scripted(engine, paths, [Say("ok")], [Say("ok")])

    run_turn(referee, "first")
    engine.act({"type": "move", "to": "hall"})
    run_turn(referee, "second")

    assert [t.player_input for t in referee.turns_seen] == ["first", "second"]
    assert [t.snapshot["party"]["area"] for t in referee.turns_seen] == ["gate", "hall"]


def test_the_move_tool_moves_the_party_through_the_engine(engine, paths):
    referee = scripted(engine, paths, [Call("mcp__engine__move", {"to": "hall"}), Say("You enter.")])

    events = run_turn(referee)

    start, result = events[0], events[1]
    assert start["type"] == "tool_start"
    assert start["label"] == "Moving to Long Hall"
    assert result["type"] == "tool_result" and result["ok"] is True
    assert [e["type"] for e in result["events"]] == ["moved", "area_revealed"]
    assert engine.state()["party"]["area"] == "hall"


def test_an_illegal_move_is_a_failed_tool_result_and_the_party_stays(engine, paths):
    referee = scripted(engine, paths, [Call("mcp__engine__move", {"to": "crypt"})])

    [result] = tool_results(run_turn(referee))

    assert result["ok"] is False
    assert "crypt" in result["error"]
    assert engine.state()["party"]["area"] == "gate"


def test_the_state_tool_returns_the_snapshot(engine, paths):
    referee = scripted(engine, paths, [Call("mcp__engine__state", {})])

    events = run_turn(referee)

    assert events[0]["label"] == "Checking the state"
    assert events[1]["output"]["state"]["party"]["area"] == "gate"


def test_reading_a_vault_note_is_allowed_and_labelled_with_its_vault_path(engine, paths):
    (paths.vault / "NPCs" / "Old Mag.md").write_text("Mag sells rope.")
    referee = scripted(engine, paths, [Call("Read", {"file_path": str(paths.vault / "NPCs" / "Old Mag.md")})])

    start, result, _ = run_turn(referee)

    assert start["label"] == "Reading NPCs/Old Mag.md"
    assert result["ok"] is True
    assert "Mag sells rope." in result["output"]


def test_writing_a_record_in_the_vault_is_allowed(engine, paths):
    referee = scripted(engine, paths, [Call("Write", {"file_path": "NPCs/Old Mag.md", "content": "rope"})])

    [result] = tool_results(run_turn(referee))

    assert result["ok"] is True
    assert (paths.vault / "NPCs" / "Old Mag.md").read_text() == "rope"


def test_the_referee_folder_outside_the_vault_is_allowed(engine, paths):
    secret = paths.referee / "Secrets.md"
    referee = scripted(engine, paths, [Call("Write", {"file_path": str(secret), "content": "trap"})])

    [result] = tool_results(run_turn(referee))

    assert result["ok"] is True
    assert secret.read_text() == "trap"


@pytest.mark.parametrize(
    "tool, tool_input",
    [
        ("Read", {"file_path": "../campaign.json"}),
        ("Read", {"file_path": "NPCs/../../campaign.json"}),
        ("Write", {"file_path": "../escape.md", "content": "x"}),
        ("Grep", {"pattern": "secret", "path": ".."}),
        ("Glob", {"pattern": "../**/*.json"}),
        ("Grep", {"pattern": "x", "glob": "../*.json"}),
    ],
)
def test_dot_dot_paths_are_denied(engine, paths, tool, tool_input):
    referee = scripted(engine, paths, [Call(tool, tool_input)])

    [result] = tool_results(run_turn(referee))

    assert result["ok"] is False and result["denied"] is True
    assert not (paths.root / "escape.md").exists()


@pytest.mark.parametrize(
    "tool, tool_input",
    [
        ("Read", {"file_path": "/etc/hostname"}),
        ("Read", {"file_path": "~/.claude/CLAUDE.md"}),
        ("Write", {"file_path": "/tmp/referee_escape.md", "content": "x"}),
        ("Glob", {"pattern": "/home/*/.claude/*.md"}),
        ("Glob", {"pattern": "*.md", "path": "/etc"}),
        ("Grep", {"pattern": "x", "path": "/"}),
    ],
)
def test_absolute_paths_outside_the_vault_are_denied(engine, paths, tool, tool_input):
    referee = scripted(engine, paths, [Call(tool, tool_input)])

    [result] = tool_results(run_turn(referee))

    assert result["denied"] is True


@pytest.mark.parametrize(
    "tool, tool_input",
    [
        ("Glob", {"pattern": "{/etc/*,x}"}),
        ("Glob", {"pattern": "{x,/etc/*}"}),
        ("Glob", {"pattern": "{NPCs,{a,../..}}/*.md"}),
        ("Glob", {"pattern": "{,/}etc/*"}),
        ("Glob", {"pattern": "{/etc/*,x"}),
        ("Grep", {"pattern": "x", "glob": "{/home/*/.ssh/*,*.md}"}),
    ],
)
def test_every_brace_alternative_of_a_glob_must_stay_in_the_vault(engine, paths, tool, tool_input):
    referee = scripted(engine, paths, [Call(tool, tool_input)])

    [result] = tool_results(run_turn(referee))

    assert result["denied"] is True


def test_a_brace_glob_whose_alternatives_stay_in_the_vault_is_allowed(engine, paths):
    referee = scripted(engine, paths, [Call("Glob", {"pattern": "{NPCs,Locations}/*.md"})])

    [result] = tool_results(run_turn(referee))

    assert result["ok"] is True


def test_the_campaign_folder_around_the_vault_is_denied(engine, paths):
    referee = scripted(engine, paths, [Call("Read", {"file_path": str(paths.state)})])

    [result] = tool_results(run_turn(referee))

    assert result["denied"] is True


def test_a_symlink_out_of_the_vault_is_denied(engine, paths, tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("canary")
    paths.vault.mkdir(parents=True, exist_ok=True)
    (paths.vault / "lore.md").symlink_to(outside)
    referee = scripted(
        engine,
        paths,
        [Call("Read", {"file_path": "lore.md"}), Call("Write", {"file_path": "lore.md", "content": "x"})],
    )

    read, write = tool_results(run_turn(referee))

    assert read["denied"] is True and "canary" not in str(read)
    assert write["denied"] is True
    assert outside.read_text() == "canary"


def test_a_symlinked_folder_out_of_the_vault_is_denied(engine, paths, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    paths.vault.mkdir(parents=True, exist_ok=True)
    (paths.vault / "Handouts").symlink_to(tmp_path / "elsewhere")
    referee = scripted(engine, paths, [Call("Write", {"file_path": "Handouts/new.md", "content": "x"})])

    [result] = tool_results(run_turn(referee))

    assert result["denied"] is True
    assert not (tmp_path / "elsewhere" / "new.md").exists()


def test_engine_written_files_cannot_be_written_or_edited(engine, paths):
    engine.act({"type": "move", "to": "hall"})
    before = paths.state_note.read_text()
    raw_log = paths.raw_log(1)
    referee = scripted(
        engine,
        paths,
        [
            Call("Write", {"file_path": "State.md", "content": "hp: 999"}),
            Call("Edit", {"file_path": str(paths.state_note), "old_string": "Long Hall", "new_string": "Throne"}),
            Call("Write", {"file_path": "Sessions/Raw/Session 001.md", "content": "rewritten"}),
            Call("Write", {"file_path": "NPCs/../State.md", "content": "hp: 999"}),
        ],
    )

    results = tool_results(run_turn(referee))

    assert [r["denied"] for r in results] == [True, True, True, True]
    assert paths.state_note.read_text() == before
    assert "rewritten" not in raw_log.read_text()


def test_engine_written_files_can_still_be_read(engine, paths):
    engine.act({"type": "move", "to": "hall"})
    referee = scripted(engine, paths, [Call("Read", {"file_path": "State.md"})])

    [result] = tool_results(run_turn(referee))

    assert result["ok"] is True
    assert "Long Hall" in result["output"]


@pytest.mark.parametrize("tool", ["Bash", "WebFetch", "Agent", "Skill", "NotebookEdit", "mcp__other__thing"])
def test_tools_outside_the_referee_set_are_denied(engine, paths, tool):
    referee = scripted(engine, paths, [Call(tool, {"command": "cat /etc/hostname"})])

    [result] = tool_results(run_turn(referee))

    assert result["denied"] is True


def test_a_file_tool_with_no_path_is_denied(engine, paths):
    referee = scripted(engine, paths, [Call("Write", {"content": "x"})])

    [result] = tool_results(run_turn(referee))

    assert result["denied"] is True


def test_a_turn_with_no_script_left_only_ends(engine, paths):
    referee = scripted(engine, paths)

    assert [e["type"] for e in run_turn(referee)] == ["done"]
