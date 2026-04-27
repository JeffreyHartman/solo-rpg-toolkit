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
