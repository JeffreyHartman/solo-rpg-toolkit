"""Tests for sessions: `Engine.new_session`, the session opening, and the Referee's session controls.

The Referee side runs through `ScriptedReferee`; `test_harness_referee_sdk.py` covers the SDK adapter.
"""
import asyncio

import pytest
from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths


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
