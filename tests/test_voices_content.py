"""Content assertions for shipped voice files.

The injected voice block lives in CLAUDE.md every turn. If a required
section disappears or the scope clause loses its pin, behavior breaks
silently. These tests pin the contract on the bundled voice files.
"""
from pathlib import Path

import pytest

from solo_roll.voices import (
    REQUIRED_SECTIONS,
    SCOPE_PIN,
    list_voices,
    load_voice,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VOICES_DIR = REPO_ROOT / "data" / "voices"

SHIPPED_VOICES = ("default", "folkloric", "grim-grounded")
WORD_CAP = 800


@pytest.mark.parametrize("name", SHIPPED_VOICES)
def test_voice_loads(name):
    display, body = load_voice(name, VOICES_DIR)
    assert display
    assert body


@pytest.mark.parametrize("name", SHIPPED_VOICES)
def test_voice_has_required_sections(name):
    _, body = load_voice(name, VOICES_DIR)
    for section in REQUIRED_SECTIONS:
        assert section in body, f"{name}: missing {section}"


@pytest.mark.parametrize("name", SHIPPED_VOICES)
def test_voice_scope_pin_present(name):
    _, body = load_voice(name, VOICES_DIR)
    assert SCOPE_PIN in body


@pytest.mark.parametrize("name", SHIPPED_VOICES)
def test_voice_has_three_bad_good_pairs(name):
    _, body = load_voice(name, VOICES_DIR)
    assert body.count("**BAD:**") >= 3, \
        f"{name}: fewer than 3 BAD examples"
    assert body.count("**GOOD:**") >= 3, \
        f"{name}: fewer than 3 GOOD examples"


@pytest.mark.parametrize("name", SHIPPED_VOICES)
def test_voice_under_word_cap(name):
    path = VOICES_DIR / f"{name}.md"
    word_count = len(path.read_text().split())
    assert word_count <= WORD_CAP, \
        f"{name}: {word_count} words exceeds cap of {WORD_CAP}"


def test_all_shipped_voices_listed():
    """list_voices on the real data dir surfaces all expected voices."""
    available = set(list_voices(VOICES_DIR))
    for name in SHIPPED_VOICES:
        assert name in available, f"{name} not surfaced by list_voices"
