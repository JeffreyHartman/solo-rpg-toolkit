"""Tests for voice loader, validator, and CLAUDE.md injection helper."""
import pytest

from solo_roll.voices import (
    VoiceError,
    VoiceFormatError,
    VoiceNotFoundError,
)


def test_voice_error_hierarchy():
    """VoiceNotFoundError and VoiceFormatError both subclass VoiceError."""
    assert issubclass(VoiceNotFoundError, VoiceError)
    assert issubclass(VoiceFormatError, VoiceError)
    assert VoiceError is not VoiceNotFoundError
    assert VoiceError is not VoiceFormatError
