"""Tests for voice loader, validator, and CLAUDE.md injection helper."""
from pathlib import Path

import pytest

from solo_roll.voices import (
    VoiceError,
    VoiceFormatError,
    VoiceNotFoundError,
    list_voices,
    load_voice,
)


def test_voice_error_hierarchy():
    """VoiceNotFoundError and VoiceFormatError both subclass VoiceError."""
    assert issubclass(VoiceNotFoundError, VoiceError)
    assert issubclass(VoiceFormatError, VoiceError)
    assert VoiceError is not VoiceNotFoundError
    assert VoiceError is not VoiceFormatError


VALID_VOICE_BODY = """# Narrative Style: Test Voice

## Scope

These rules govern in-fiction narration only. Mechanical reporting stays plain.

## Beat budget

1-3 sentences per beat. Then stop.

## Hard rules

- No "begins to" / "starts to"
- No three-item sensory lists
- No abstract noun phrases

## Voice notes

Test anchor. Plain language. Concrete detail.

## Examples

### Bad / Good — exploration
**BAD:** Bad para.
**GOOD:** Good para.

### Bad / Good — dialogue
**BAD:** Bad para.
**GOOD:** Good para.

### Bad / Good — combat
**BAD:** Bad para.
**GOOD:** Good para.
"""


@pytest.fixture
def voices_dir(tmp_path):
    d = tmp_path / "voices"
    d.mkdir()
    return d


def test_list_voices_empty_when_dir_missing(tmp_path):
    assert list_voices(tmp_path / "nonexistent") == []


def test_list_voices_returns_sorted_stems(voices_dir):
    (voices_dir / "alpha.md").write_text(VALID_VOICE_BODY)
    (voices_dir / "zulu.md").write_text(VALID_VOICE_BODY)
    (voices_dir / "bravo.md").write_text(VALID_VOICE_BODY)
    assert list_voices(voices_dir) == ["alpha", "bravo", "zulu"]


def test_list_voices_skips_underscore_prefixed(voices_dir):
    (voices_dir / "alpha.md").write_text(VALID_VOICE_BODY)
    (voices_dir / "_template.md").write_text(VALID_VOICE_BODY)
    assert list_voices(voices_dir) == ["alpha"]


def test_load_voice_returns_display_name_and_body(voices_dir):
    (voices_dir / "test.md").write_text(VALID_VOICE_BODY)
    display, body = load_voice("test", voices_dir)
    assert display == "Test Voice"
    assert body.startswith("## Narrative Style: Test Voice")
    # H1 was stripped — no line begins with single '#' followed by space.
    import re as _re
    assert _re.search(r"^# Narrative Style:", body, _re.MULTILINE) is None
    assert "## Scope" in body
    assert "## Examples" in body


def test_load_voice_missing_file_raises(voices_dir):
    (voices_dir / "alpha.md").write_text(VALID_VOICE_BODY)
    with pytest.raises(VoiceNotFoundError) as exc:
        load_voice("nonexistent", voices_dir)
    assert "alpha" in str(exc.value)  # available list shown


def test_load_voice_missing_h1_raises(voices_dir):
    (voices_dir / "bad.md").write_text("## Scope\n\nin-fiction narration only\n")
    with pytest.raises(VoiceFormatError, match="missing H1"):
        load_voice("bad", voices_dir)


def test_load_voice_missing_required_section_raises(voices_dir):
    bad = "# Narrative Style: X\n\n## Scope\n\nin-fiction narration only\n"
    (voices_dir / "bad.md").write_text(bad)
    with pytest.raises(VoiceFormatError, match="missing required section"):
        load_voice("bad", voices_dir)


def test_load_voice_missing_scope_pin_raises(voices_dir):
    bad = VALID_VOICE_BODY.replace("in-fiction narration only", "applies to text")
    (voices_dir / "bad.md").write_text(bad)
    with pytest.raises(VoiceFormatError, match="scope clause"):
        load_voice("bad", voices_dir)
