"""Tests for the campaign vault: the layout `create_campaign` writes, the engine's
mechanical block in character notes, and the Referee's records through `ScriptedReferee`.
"""
import asyncio
import re
from pathlib import Path

import pytest
from harness_fixtures import HAND_MADE_MAP, make_campaign, open_engine

from solo_roll.harness.campaign import CampaignPaths, create_campaign
from solo_roll.harness.referee import Call, ScriptedReferee
from solo_roll.harness.vault import create_vault

FOLDERS = ["Characters", "NPCs", "Locations", "Threads", "Lore & World", "Sessions", "Sessions/Raw"]


def frontmatter(note: Path) -> dict[str, str]:
    text = note.read_text()
    assert text.startswith("---\n"), f"{note} has no frontmatter"
    block = text.split("---\n", 2)[1]
    return dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)


def test_a_new_campaign_has_the_vault_layout_with_an_index_in_each_folder(tmp_path):
    paths = CampaignPaths(make_campaign(tmp_path))

    for note in ["Home.md", "_Campaign.md", "Conventions.md"]:
        assert frontmatter(paths.vault / note)["type"]
    for folder in FOLDERS:
        assert frontmatter(paths.vault / folder / "_index.md")["type"] == "index"
    assert paths.referee.is_dir()
    assert not paths.referee.resolve().is_relative_to(paths.vault.resolve())


def unresolved_links(vault: Path) -> list[str]:
    """Return each wikilink that Obsidian could not resolve: by vault path, or by note name.

    Obsidian does not link inside inline code, so those spans are skipped.
    """
    notes = [p.relative_to(vault).with_suffix("").as_posix() for p in vault.rglob("*.md")]
    names = {n.rsplit("/", 1)[-1] for n in notes}
    missing = []
    for note in vault.rglob("*.md"):
        for target in re.findall(r"\[\[([^\]|#]+)", re.sub(r"`[^`]*`", "", note.read_text())):
            if target not in notes and target not in names:
                missing.append(f"{note.relative_to(vault)} -> {target}")
    return missing


def test_every_wikilink_in_a_new_vault_resolves(tmp_path):
    paths = CampaignPaths(make_campaign(tmp_path))

    assert unresolved_links(paths.vault) == []


def test_creating_the_vault_again_keeps_the_notes_the_owner_wrote(tmp_path):
    paths = CampaignPaths(make_campaign(tmp_path))
    (paths.vault / "Home.md").write_text("my own home page")

    create_vault(paths, "Again", ["ose"])

    assert (paths.vault / "Home.md").read_text() == "my own home page"


def mechanical_block(note: Path) -> str:
    text = note.read_text()
    assert text.count("%% engine:begin %%") == 1 and text.count("%% engine:end %%") == 1
    return text.split("%% engine:begin %%")[1].split("%% engine:end %%")[0]


def make_fighter_campaign(tmp_path):
    return create_campaign(
        tmp_path / "campaign",
        plugins=["ose"],
        map_data=HAND_MADE_MAP,
        start="gate",
        party=[{"name": "Brannoc", "class": "Fighter", "hp": 6, "ac": 4}],
    )


def test_each_party_member_has_a_character_note_with_a_mechanical_block(tmp_path):
    paths = CampaignPaths(make_fighter_campaign(tmp_path))
    note = paths.vault / "Characters" / "Brannoc.md"

    assert frontmatter(note)["type"] == "character"
    block = mechanical_block(note)
    assert "Hp: 6" in block and "Ac: 4" in block and "Class: Fighter" in block
    assert "Position: Gatehouse" in block
    assert "[[Brannoc]]" in (paths.vault / "Characters" / "_index.md").read_text()
    assert unresolved_links(paths.vault) == []


def test_the_mechanical_block_follows_the_engine_and_the_story_around_it_stays(tmp_path):
    campaign = make_fighter_campaign(tmp_path)
    note = CampaignPaths(campaign).vault / "Characters" / "Brannoc.md"
    note.write_text(note.read_text() + "\nBrannoc swore an oath at the gate.\n")
    engine = open_engine(campaign)

    engine.act({"type": "move", "to": "hall"})

    assert "Position: Long Hall" in mechanical_block(note)
    assert "Position: Gatehouse" not in note.read_text()
    assert "Brannoc swore an oath at the gate." in note.read_text()


def run_turn(referee, text="I look around."):
    async def collect():
        return [event async for event in referee.turn(text)]

    return asyncio.run(collect())


def results_of(campaign, *calls):
    referee = ScriptedReferee(open_engine(campaign), CampaignPaths(campaign), turns=[list(calls)])
    return [e for e in run_turn(referee) if e["type"] == "tool_result"]


def edit(old, new, **extra):
    return Call("Edit", {"file_path": "Characters/Brannoc.md", "old_string": old, "new_string": new, **extra})


def write(content, file_path="Characters/Brannoc.md"):
    return Call("Write", {"file_path": file_path, "content": content})


BLOCK_CHANGES = {
    "edit inside the block": lambda text: edit("Hp: 6", "Hp: 60"),
    "edit across a marker": lambda text: edit("# Brannoc\n\n%% engine:begin %%", "# Brannoc"),
    "edit that adds a marker": lambda text: edit("## Goals", "## Goals\n%% engine:end %%"),
    "replace_all that reaches the block": lambda text: edit("6", "60", replace_all=True),
    "write without the block": lambda text: write("# Brannoc\n\nA new life.\n"),
    "write with a changed block": lambda text: write(text.replace("Hp: 6", "Hp: 60")),
    "write a second block": lambda text: write(text + "\n%% engine:begin %%\nHp: 60\n%% engine:end %%\n"),
    "write a forged block in a new note": lambda text: write(
        "%% engine:begin %%\nHp: 60\n%% engine:end %%\n", file_path="Characters/Twin.md"
    ),
}


@pytest.mark.parametrize("change", BLOCK_CHANGES.values(), ids=BLOCK_CHANGES.keys())
def test_the_referee_cannot_change_the_mechanical_block(tmp_path, change):
    campaign = make_fighter_campaign(tmp_path)
    note = CampaignPaths(campaign).vault / "Characters" / "Brannoc.md"
    before = note.read_text()

    [result] = results_of(campaign, change(before))

    assert result["denied"] is True
    assert "engine" in result["error"]
    assert note.read_text() == before
    assert not (note.parent / "Twin.md").exists()


def test_the_referee_can_edit_the_story_around_the_mechanical_block(tmp_path):
    campaign = make_fighter_campaign(tmp_path)
    note = CampaignPaths(campaign).vault / "Characters" / "Brannoc.md"
    block = mechanical_block(note)

    [edited] = results_of(campaign, edit("## Backstory\n", "## Backstory\n\nA miller's son from the hills.\n"))
    [written] = results_of(campaign, write(note.read_text().replace("## Goals\n", "## Goals\n\nFind his brother.\n")))

    assert edited["ok"] is True and written["ok"] is True
    assert "A miller's son from the hills." in note.read_text()
    assert "Find his brother." in note.read_text()
    assert mechanical_block(note) == block


def test_a_turn_that_meets_an_npc_writes_the_record_and_updates_the_index(tmp_path):
    campaign = make_campaign(tmp_path)
    vault = CampaignPaths(campaign).vault
    index = vault / "NPCs" / "_index.md"
    record = (
        "---\nname: Old Mag\ntype: npc\nstatus: alive\nmet: Session 001\ndisposition: friendly\n---\n"
        "# Old Mag\n\nSells rope to [[Brannoc]] at the gate.\n"
    )

    results = results_of(
        campaign,
        Call("Read", {"file_path": "Conventions.md"}),
        Call("Write", {"file_path": "NPCs/Old Mag.md", "content": record}),
        Call("Write", {"file_path": "NPCs/_index.md", "content": index.read_text() + "- [[Old Mag]] - rope seller\n"}),
    )

    assert [r["ok"] for r in results] == [True, True, True]
    assert frontmatter(vault / "NPCs" / "Old Mag.md")["type"] == "npc"
    assert "- [[Old Mag]] - rope seller" in index.read_text()
    assert unresolved_links(vault) == []


def test_the_raw_log_index_links_each_session_log(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    engine.act({"type": "move", "to": "hall"})
    engine.act({"type": "move", "to": "gate"})

    vault = CampaignPaths(campaign).vault
    index = (vault / "Sessions" / "Raw" / "_index.md").read_text()
    assert index.count("[[Sessions/Raw/Session 001|Session 001]]") == 1
    assert unresolved_links(vault) == []
