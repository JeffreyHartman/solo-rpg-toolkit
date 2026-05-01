"""solo-campaign voice file loading, validation, and CLAUDE.md injection."""


class VoiceError(Exception):
    """Base class for voice-loading errors."""


class VoiceNotFoundError(VoiceError):
    """Raised when a requested voice name has no matching file."""


class VoiceFormatError(VoiceError):
    """Raised when a voice file fails structural validation."""
