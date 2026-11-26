"""Tests for the `out_of_character_note` engine tool."""
import asyncio

from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.referee import Call, Say, ScriptedReferee
from solo_roll.harness.referee.sdk import system_prompt

NOTE = "None of my tools can add a new light source."


def run_turn(engine, campaign, *steps):
    referee = ScriptedReferee(engine, CampaignPaths(campaign), turns=[list(steps)])

    async def collect():
        return [event async for event in referee.turn("We light a torch.")]

    return asyncio.run(collect())


def test_a_note_is_its_own_event_type_apart_from_the_narration(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    events = run_turn(
        engine, campaign, Call("mcp__engine__out_of_character_note", {"text": NOTE}), Say("The corridor stays dark.")
    )

    assert [e["type"] for e in events] == ["tool_start", "tool_result", "text", "done"]
    assert events[0]["label"] == "Noting a harness gap"
    assert events[1]["events"] == [{"type": "ooc_note", "text": NOTE}]
    assert events[2]["text"] == "The corridor stays dark."


def test_a_note_goes_to_the_raw_log_marked_out_of_character(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    run_turn(engine, campaign, Call("mcp__engine__out_of_character_note", {"text": NOTE}))

    log = CampaignPaths(campaign).raw_log(engine.state()["session"]).read_text()
    assert f"- Referee (out of character): {NOTE}" in log


def test_an_empty_note_is_refused(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    _, result, _ = run_turn(engine, campaign, Call("mcp__engine__out_of_character_note", {"text": "  "}))

    assert result["ok"] is False


def test_the_prompt_asks_for_the_gm_voice_and_names_the_note_tool(tmp_path):
    prompt = system_prompt([], CampaignPaths(make_campaign(tmp_path)))

    assert "game master" in prompt
    assert "mcp__engine__out_of_character_note" in prompt
