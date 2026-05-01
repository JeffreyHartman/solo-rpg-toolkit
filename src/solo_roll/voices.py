"""solo-campaign voice file loading, validation, and CLAUDE.md injection."""
import re
from pathlib import Path


class VoiceError(Exception):
    """Base class for voice-loading errors."""


class VoiceNotFoundError(VoiceError):
    """Raised when a requested voice name has no matching file."""


class VoiceFormatError(VoiceError):
    """Raised when a voice file fails structural validation."""


REQUIRED_SECTIONS = (
    "## Scope",
    "## Beat budget",
    "## Hard rules",
    "## Voice notes",
    "## Examples",
)

H1_PATTERN = re.compile(r"^# Narrative Style: (.+?)\s*$", re.MULTILINE)
SCOPE_PIN = "in-fiction narration only"


def list_voices(voices_dir: Path) -> list[str]:
    """Return sorted names (without .md suffix) of voice files in voices_dir.

    Files starting with '_' are excluded (reserved for templates).
    Returns [] if voices_dir does not exist.
    """
    if not voices_dir.is_dir():
        return []
    return sorted(
        p.stem for p in voices_dir.glob("*.md")
        if not p.name.startswith("_")
    )


def load_voice(name: str, voices_dir: Path) -> tuple[str, str]:
    """Read and validate the voice file. Return (display_name, body).

    `body` is the file content with the H1 line replaced by an H2 of the form
    `## Narrative Style: <Display Name>`. The body is what gets injected into
    CLAUDE.md.

    Raises VoiceNotFoundError if the file is missing.
    Raises VoiceFormatError if the file lacks the H1, any required section,
    or the scope-pin substring.
    """
    path = voices_dir / f"{name}.md"
    if not path.is_file():
        available = list_voices(voices_dir)
        avail_str = ", ".join(available) if available else "(none)"
        raise VoiceNotFoundError(
            f"Voice not found: {name}. Available: {avail_str}"
        )
    content = path.read_text()

    h1_match = H1_PATTERN.search(content)
    if not h1_match:
        raise VoiceFormatError(
            f"{path}: missing H1 of form "
            f"'# Narrative Style: <Display Name>'"
        )
    display_name = h1_match.group(1).strip()

    for section in REQUIRED_SECTIONS:
        if section not in content:
            raise VoiceFormatError(
                f"{path}: missing required section '{section}'"
            )

    if SCOPE_PIN not in content:
        raise VoiceFormatError(
            f"{path}: scope clause must contain substring "
            f"'{SCOPE_PIN}'"
        )

    body = H1_PATTERN.sub(
        f"## Narrative Style: {display_name}", content, count=1
    )
    return display_name, body
