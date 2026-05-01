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


MARKER_START = "<!-- voice:start -->"
MARKER_END = "<!-- voice:end -->"
ANCHOR_HEADING = "## Active skills"


def inject_voice_block(claude_md: str, voice_body: str) -> tuple[str, str | None]:
    """Insert or replace a voice block in CLAUDE.md content.

    Returns (new_text, warning) where warning is None on clean success or a
    short message describing a non-fatal anomaly (e.g., anchor heading
    missing — block appended at end).

    Raises VoiceFormatError if markers are malformed (unbalanced count,
    end-before-start, or more than one pair).
    """
    block = f"{MARKER_START}\n{voice_body.rstrip()}\n{MARKER_END}"

    starts = [m.start() for m in re.finditer(re.escape(MARKER_START), claude_md)]
    ends = [m.start() for m in re.finditer(re.escape(MARKER_END), claude_md)]

    if len(starts) != len(ends) or len(starts) > 1:
        raise VoiceFormatError(
            "Malformed or duplicate voice markers in CLAUDE.md, fix manually."
        )

    if len(starts) == 1:
        if ends[0] < starts[0]:
            raise VoiceFormatError(
                "Malformed voice markers (end before start) in CLAUDE.md, "
                "fix manually."
            )
        end_pos = ends[0] + len(MARKER_END)
        new_text = claude_md[:starts[0]] + block + claude_md[end_pos:]
        return new_text, None

    # No markers — insert before anchor heading.
    anchor_match = re.search(rf"^{re.escape(ANCHOR_HEADING)}\s*$",
                             claude_md, re.MULTILINE)
    if anchor_match:
        insert_pos = anchor_match.start()
        new_text = (
            claude_md[:insert_pos]
            + block + "\n\n"
            + claude_md[insert_pos:]
        )
        return new_text, None

    # Anchor heading missing — append at end.
    sep = "" if claude_md.endswith("\n") else "\n"
    new_text = claude_md + sep + "\n" + block + "\n"
    warning = (
        f"{ANCHOR_HEADING!r} heading not found in CLAUDE.md; "
        f"voice block appended at end."
    )
    return new_text, warning
