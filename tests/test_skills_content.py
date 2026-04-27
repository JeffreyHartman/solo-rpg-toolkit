"""Assertions over the markdown content of bundled skills.

The agent reads these files at runtime; if a section it relies on is
removed or renamed, behavior breaks silently. These tests pin the
contract.
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"


@pytest.fixture
def journaler_skill() -> str:
    return (SKILLS_DIR / "solo-journaler" / "SKILL.md").read_text()


@pytest.fixture
def ironsworn_skill() -> str:
    return (SKILLS_DIR / "ironsworn" / "SKILL.md").read_text()


@pytest.fixture
def ironsworn_character_template() -> str:
    return (SKILLS_DIR / "ironsworn" / "character-template.md").read_text()


def test_skills_dir_exists():
    assert SKILLS_DIR.is_dir()


def test_journaler_has_thread_example(journaler_skill):
    """Thread example must be present with all required sections."""
    # Heading anchors example block
    assert "## Example Thread file" in journaler_skill or \
           "## Example thread file" in journaler_skill
    # Required sections inside the Thread example
    for heading in (
        "## What we know",
        "## What we suspect",
        "## Progression",
        "## Resolution",
    ):
        assert heading in journaler_skill, f"missing Thread heading: {heading}"
    # Stakes line is part of the metadata block
    assert "**Stakes**" in journaler_skill


def test_journaler_has_location_example(journaler_skill):
    """Location example must be present with required sections."""
    assert "## Example Location file" in journaler_skill or \
           "## Example location file" in journaler_skill
    # The example file uses Stonebeck — that string should appear in a
    # Place context (it already appears in the Thread example, so the
    # check below depends on the heading anchor above)
    assert "# Stonebeck" in journaler_skill
    for heading in (
        "## Description",
        "## Visits",
    ):
        assert heading in journaler_skill, f"missing Location heading: {heading}"


def test_npc_example_uses_fictional_date(journaler_skill):
    """The Kesta NPC example must not use ISO-date strings — vault
    narrative is fictional-date only."""
    # Find the NPC example block. Anchor on the existing heading.
    assert "## Example NPC file" in journaler_skill
    # The Kesta block previously contained `Met: 2026-04-26`. After this
    # change it must use a fictional-date string and must not contain
    # any 4-digit-year-dash-month-dash-day pattern within the example.
    npc_section_start = journaler_skill.index("## Example NPC file")
    # The next "## " heading bounds the section
    next_heading = journaler_skill.find("\n## ", npc_section_start + 1)
    npc_section = journaler_skill[npc_section_start:next_heading if next_heading != -1 else None]
    # No ISO-date inside the NPC example
    import re
    assert re.search(r"\b20\d{2}-\d{2}-\d{2}\b", npc_section) is None, \
        "NPC example still contains an ISO date"
    # And the fictional Met line is present
    assert "**Met**: " in npc_section


def test_journaler_uses_sequential_session_filenames(journaler_skill):
    """Session log filenames are `Session NNN.md` — three-digit pad,
    sequential, not ISO-date based."""
    # The filename-conventions section must reference the new pattern
    assert "Session NNN.md" in journaler_skill
    # And must NOT prescribe ISO-date filenames for session logs.
    # Specifically: the old wording contained
    # "ISO date for all session logs ... 2026-04-26.md"
    # which we are removing. Allow the literal date elsewhere (e.g. in
    # the Played: metadata of the session-log example).
    assert "ISO date for all session logs" not in journaler_skill


def test_session_log_example_has_dual_date_metadata(journaler_skill):
    """The vault-side session-log example uses a `Session 001` heading
    and a top metadata block with both Played (real-world ISO) and
    In-fiction (fictional) dates."""
    # Anchor: the example uses heading `# Session 001`
    assert "# Session 001" in journaler_skill
    # Metadata block contents
    assert "**Played**: " in journaler_skill
    assert "**In-fiction**: " in journaler_skill


def test_journaler_has_fictional_dates_rule(journaler_skill):
    """The skill must document the fictional-dates-only rule and where
    the current in-fiction date is stored."""
    # Heading anchors the rule
    assert "## Dates" in journaler_skill or \
           "## Fictional dates" in journaler_skill
    # Storage location for current date
    assert "Current date" in journaler_skill
    assert "Character.md" in journaler_skill
    assert "Calendar.md" in journaler_skill


def test_journaler_has_canonical_context_rule(journaler_skill):
    """The skill must instruct the agent to keep Thread / Place files
    self-contained — updating them in place rather than letting context
    drift into session logs."""
    assert "canonical context" in journaler_skill.lower()
    # And must mention moving suspicions to `What we know` when confirmed
    assert "What we know" in journaler_skill


def test_journaler_session_end_updates_current_date(journaler_skill):
    """Session-end procedure must include updating the current
    in-fiction date."""
    # Anchor: the existing heading
    assert "### At the end of a session" in journaler_skill
    # The end-of-session block must mention updating Current date
    end_idx = journaler_skill.index("### At the end of a session")
    next_heading = journaler_skill.find("\n## ", end_idx + 1)
    end_block = journaler_skill[end_idx:next_heading if next_heading != -1 else None]
    assert "Current date" in end_block
    assert "in-fiction" in end_block.lower()
