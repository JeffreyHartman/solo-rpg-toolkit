"""Tests for sessions: `Engine.new_session`, the session opening, and the Referee's session controls.

The Referee side runs through `ScriptedReferee`; `test_harness_referee_sdk.py` covers the SDK adapter.
"""
import asyncio

import pytest
from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.errors import SettingError
from solo_roll.harness.referee import Call, ScriptedReferee


@pytest.fixture
def paths(tmp_path):
    return CampaignPaths(make_campaign(tmp_path))


@pytest.fixture
def engine(paths):
    return open_engine(paths.root)


def test_a_new_session_after_play_ends_the_raw_log_and_starts_the_next_session(engine, paths):
    engine.act({"type": "move", "to": "hall"})

    events = engine.new_session()

    assert [e["type"] for e in events] == ["session_ended"]
    assert engine.state()["session"] == 2
    assert open_engine(paths.root).state()["session"] == 2
    assert "Session 1 ends." in paths.raw_log(1).read_text()
    assert not paths.raw_log(2).exists()
    assert "Session: 2" in paths.state_note.read_text()


def test_a_new_session_with_nothing_played_keeps_the_session_number(engine, paths):
    assert engine.new_session() == []
    assert engine.state()["session"] == 1


def run_turn(referee, text="I look around."):
    async def collect():
        return [event async for event in referee.turn(text)]

    return asyncio.run(collect())


def test_the_first_turn_of_a_conversation_opens_the_session_from_the_vault(engine, paths):
    referee = ScriptedReferee(engine, paths)

    run_turn(referee, "first")
    run_turn(referee, "second")

    first, second = referee.turns_seen
    assert "<session>" in first.prompt and "Home.md" in first.prompt
    assert '"area": "gate"' in first.prompt and first.prompt.endswith("first")
    assert "<session>" not in second.prompt


def test_a_new_conversation_reads_the_last_clean_session_note(engine, paths):
    engine.act({"type": "move", "to": "hall"})
    (paths.vault / "Sessions" / "Session 001 - The Gate.md").write_text("# The Gate\n")
    engine.new_session()
    referee = ScriptedReferee(engine, paths)
    run_turn(referee, "before")

    asyncio.run(referee.new_session())
    run_turn(referee, "after")

    after = referee.turns_seen[-1]
    assert after.conversation == referee.turns_seen[0].conversation + 1
    assert "Session 2" in after.prompt
    assert "Sessions/Session 001 - The Gate.md" in after.prompt
    assert '"area": "hall"' in after.prompt


def test_the_scripted_turn_context_lists_the_prompt_parts_and_tool_results(engine, paths):
    referee = ScriptedReferee(engine, paths, [[Call("mcp__engine__move", {"to": "hall"})]])

    run_turn(referee, "I walk east.")

    parts = referee.turn_context()
    assert [p["label"] for p in parts] == ["Session opening", "State snapshot", "Player input", "Moving to Long Hall"]
    assert '"area": "hall"' in parts[3]["text"]


def test_a_new_campaign_runs_the_referee_on_sonnet_at_low_effort_with_a_budget(engine):
    referee = engine.settings()["referee"]

    assert (referee["model"], referee["effort"]) == ("sonnet", "low")
    assert referee["budget"] > 0


def test_referee_settings_change_and_persist(engine, paths):
    engine.change_setting("referee", "model", "opus")
    engine.change_setting("referee", "effort", "high")
    engine.change_setting("referee", "budget", 80000)

    assert open_engine(paths.root).settings()["referee"] == {"model": "opus", "effort": "high", "budget": 80000}


@pytest.mark.parametrize(
    "key, value",
    [("model", "gpt"), ("effort", "extreme"), ("budget", 0), ("budget", "lots"), ("budget", True), ("voice", "x")],
)
def test_a_bad_referee_setting_is_refused_and_saves_nothing(engine, key, value):
    before = engine.settings()["referee"]

    with pytest.raises(SettingError):
        engine.change_setting("referee", key, value)

    assert engine.settings()["referee"] == before
