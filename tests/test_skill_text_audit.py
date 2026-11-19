"""Tests that skill, doc and template text matches the code and the rules it
cites: `PLAYER_VAULT_PATH` use, Ask the Oracle odds, Mythic state layout,
referee output, `repair_hyphenation` and `load_revealed`.

Each test carries the 2026-11-18 audit finding number where one applies."""
import json
import re
import subprocess
from pathlib import Path

import pytest

from solo_roll.reveal import RevealError, load_revealed

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def read(*parts) -> str:
    return (ROOT.joinpath(*parts)).read_text()


def test_no_skill_depends_on_player_vault_path():
    """The vault is the fixed ./playervault/ folder; the CLAUDE.md line is gone."""
    offenders = [str(p.relative_to(ROOT)) for p in SKILLS.rglob("*")
                 if p.is_file() and "PLAYER_VAULT_PATH" in p.read_text()]
    assert offenders == []


def test_ironsworn_statusline_reads_the_fixed_vault(tmp_path):
    (tmp_path / "playervault").mkdir()
    (tmp_path / "playervault/Character.md").write_text(
        "# Kesta\n> Health: 4/5\n> Spirit: 5/5\n> Supply: 3/5\n> Momentum: +2\n")
    proc = subprocess.run(["bash", str(SKILLS / "ironsworn/statusline.sh")],
                          cwd=tmp_path, capture_output=True, text=True)
    assert "Kesta" in proc.stdout and "4/5" in proc.stdout


def test_ask_the_oracle_rolls_d100_for_d100_odds():
    """Datasworn classic ask_the_oracle: dice 1d100, yes at 11/26/51/76/91 or more."""
    text = read("skills/ironsworn/moves/ask-the-oracle.md")
    assert "solo-roll roll d100" in text
    assert "2d10" not in text
    for threshold in ("11 or greater", "26 or greater", "51 or greater",
                      "76 or greater", "91 or greater"):
        assert threshold in text


def test_no_skill_names_a_table_that_does_not_exist():
    """Every `solo-roll table <name>` in a skill must be a shipped table."""
    missing = []
    for path in SKILLS.rglob("*.md"):
        for name in re.findall(r"solo-roll table ([a-z0-9_/-]+)", path.read_text()):
            if not (ROOT / "data/tables" / f"{name}.json").exists():
                missing.append((path.name, name))
    assert missing == []


def test_no_skill_points_at_a_missing_moves_md():
    assert not (SKILLS / "ironsworn/moves.md").exists()
    for path in SKILLS.rglob("*.md"):
        assert "`moves.md`" not in path.read_text(), path


def test_thread_heading_table_uses_boxes_for_the_upper_ranks():
    """Ironsworn Troublesome marks 3 boxes, Epic 1 tick. SKILL.md live stat
    tracking states the same step sizes."""
    text = read("skills/ironsworn/SKILL.md")
    assert "| Troublesome | `3 boxes per mark`" in text
    assert "| Epic        | `1 tick per mark`" in text
    assert "3 ticks per mark" not in text


def test_mythic_cf_allows_only_plus_or_minus_one():
    """Mythic 2e, The Chaos Factor: a scene raises or lowers CF by 1."""
    assert "Genuine mixed result: no change" not in read("skills/mythic-gme/SKILL.md")
    assert "yeses get yes-er" not in read("skills/mythic-gme/chaos-factor.md")


def test_mythic_state_layout_is_the_same_everywhere():
    campaign_py = read("src/solo_roll/campaign.py")
    skill = read("skills/mythic-gme/SKILL.md")
    assert "## Chaos Factor: 5" in campaign_py and "## Chaos Factor: 5" in skill
    assert "## Scene History" in campaign_py and "## Scene History" in skill
    assert "## Scene History" in read("skills/mythic-gme/chaos-factor.md")
    assert "CF History" not in campaign_py


def test_readme_does_not_use_a_vault_flag():
    assert "--vault" not in read("README.md")


def test_referee_returns_nothing_the_docs_say_it_withholds():
    """README.md and docs/dungeon-schema.md: the referee returns only what the
    party perceives, and designer notes are not narrated."""
    text = read("templates/ose/.claude/agents/referee.md")
    assert "**Hidden.**" not in text
    assert "**On contact.**" not in text
    assert "**Designer note.**" not in text


def test_map_viewer_keys_areas_by_string_id():
    html = read("templates/ose/map/index.html")
    assert "[String(a.id), a]" in html
    assert "maskImg.set(String(a.id), im)" in html


def test_load_revealed_rejects_a_trailing_comma(tmp_path):
    path = tmp_path / "revealed.js"
    path.write_text('window.REVEALED = ["1", "2",];\n')
    with pytest.raises(RevealError, match="invalid JSON"):
        load_revealed(path)


@pytest.fixture
def extract_prose():
    source = read("templates/ose/tools/extract_prose.py")
    namespace: dict = {}
    exec(source.split("ap = argparse.ArgumentParser()")[0], namespace)
    return namespace["repair_hyphenation"]


class TestReflowHyphenation:
    def test_joins_a_word_split_at_a_hyphen(self, extract_prose):
        assert extract_prose("the ac- tions of") == "the actions of"

    def test_keeps_a_dice_expression_wrapped_after_a_minus(self, extract_prose):
        assert extract_prose("damage 1d6- 1 points") == "damage 1d6- 1 points"

    def test_keeps_a_wrapped_numeric_range(self, extract_prose):
        assert extract_prose("rooms 1- 3") == "rooms 1- 3"


def test_ose_claude_md_documents_the_two_in_six_modifier():
    """templates/ose/CLAUDE.md tells the referee to pass `--mod -1` for a
    2-in-6 search. Audit findings 6 and 7."""
    assert "--mod -1" in read("templates/ose/CLAUDE.md")


def test_ose_claude_md_documents_the_class_minimums():
    """templates/ose/CLAUDE.md lists the minimums `gen-character` checks.
    Audit finding 19."""
    text = read("templates/ose/CLAUDE.md")
    assert "eligible" in text and "minimum" in text.lower()
