# Narrative Voices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `data/voices/<name>.md` files plus a `solo-campaign --voice` flag and `voice apply` / `voice list` subcommands that inject a chosen voice block into a campaign's `CLAUDE.md`, so per-campaign GM prose discipline reaches the LLM in the always-loaded preamble with zero tool calls.

**Architecture:** Pure-data voice files in `data/voices/` consumed by a new `src/solo_roll/voices.py` module (loader + injection helper). `campaign.py` gains a `--voice` flag that wires injection into the existing scaffold flow, plus a `voice` subcommand group (`apply`, `list`) for post-scaffold operations. Voice content is wrapped in HTML-comment marker pairs in `CLAUDE.md` for idempotent re-injection.

**Tech Stack:** Python 3.11+, stdlib only (`argparse`, `pathlib`, `re`), pytest.

**Reference:** Spec at `docs/superpowers/specs/2026-04-30-narrative-voices-design.md`.

---

## File Structure

**New files:**
- `data/voices/default.md` — neutral baseline voice (Task 4)
- `data/voices/folkloric.md` — Hobb / Le Guin anchor (Task 9)
- `data/voices/grim-grounded.md` — Abercrombie / Parker anchor (Task 10)
- `src/solo_roll/voices.py` — voice loader + validator + injection helper (Tasks 1-3)
- `tests/test_voices.py` — unit tests for `voices.py` (Tasks 1-3)
- `tests/test_voices_content.py` — content assertions for shipped voice files (Task 11)

**Modified files:**
- `src/solo_roll/campaign.py` — add `--voice` flag + `voice` subcommand group (Tasks 5-7)
- `tests/test_campaign.py` — extend with voice CLI tests (Tasks 5-7)
- `docs/ROADMAP.md` — mark sub-project complete (Task 12)

**Anchor verified:** `example-campaign/CLAUDE.md` line 14 contains `## Active skills` — used as injection insertion point when no markers are present.

---

## Conventions

- TDD: failing test → run-fail → minimal impl → run-pass → commit. One logical change per commit.
- Inject paths into helpers (no `Path.home()` / `__file__` reads inside utility functions). Match existing toolkit style.
- Typed exceptions raised from helpers (`VoiceError`, `VoiceNotFoundError`, `VoiceFormatError`); only `main()` translates to exit codes.
- Run all tests after each task: `pytest --tb=short -q`. New tests must pass; pre-existing tests must stay green.

---

### Task 1: voices.py — error types and module skeleton

**Files:**
- Create: `src/solo_roll/voices.py`
- Test: `tests/test_voices.py`

- [ ] **Step 1: Write the failing test**

`tests/test_voices.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_voices.py::test_voice_error_hierarchy -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solo_roll.voices'`

- [ ] **Step 3: Write minimal implementation**

`src/solo_roll/voices.py`:
```python
"""solo-campaign voice file loading, validation, and CLAUDE.md injection."""


class VoiceError(Exception):
    """Base class for voice-loading errors."""


class VoiceNotFoundError(VoiceError):
    """Raised when a requested voice name has no matching file."""


class VoiceFormatError(VoiceError):
    """Raised when a voice file fails structural validation."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_voices.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/voices.py tests/test_voices.py
git commit -m "feat(voices): add error type scaffolding for voice module"
```

---

### Task 2: voices.py — load_voice + list_voices

**Files:**
- Modify: `src/solo_roll/voices.py`
- Modify: `tests/test_voices.py`

- [ ] **Step 1: Add failing tests for list_voices and load_voice**

Append to `tests/test_voices.py`:
```python
from pathlib import Path

from solo_roll.voices import list_voices, load_voice


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
    assert "# Narrative Style:" not in body  # H1 was stripped
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_voices.py -v`
Expected: FAIL — `ImportError` on `list_voices` / `load_voice`.

- [ ] **Step 3: Implement list_voices and load_voice**

Append to `src/solo_roll/voices.py`:
```python
import re
from pathlib import Path

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
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `pytest tests/test_voices.py -v`
Expected: PASS (9 passed including the error-hierarchy test).

- [ ] **Step 5: Run full suite**

Run: `pytest --tb=short -q`
Expected: All pre-existing tests still pass. New 9 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/voices.py tests/test_voices.py
git commit -m "feat(voices): add list_voices and load_voice with structural validation"
```

---

### Task 3: voices.py — inject_voice_block

**Files:**
- Modify: `src/solo_roll/voices.py`
- Modify: `tests/test_voices.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_voices.py`:
```python
from solo_roll.voices import (
    MARKER_END,
    MARKER_START,
    inject_voice_block,
)


VOICE_BODY_FIXTURE = "## Narrative Style: Test\n\nbody content here\n"


CLAUDE_MD_TEMPLATE = """# Solo RPG Campaign — Foo

## Configuration

```
SYSTEM: Ironsworn
```

## Active skills

This campaign uses:
- ironsworn

## House rules

- something
"""


def test_inject_into_empty_markers_inserts_before_active_skills():
    new_text, warning = inject_voice_block(CLAUDE_MD_TEMPLATE, VOICE_BODY_FIXTURE)
    assert warning is None
    assert MARKER_START in new_text
    assert MARKER_END in new_text
    # Block must appear before "## Active skills"
    assert new_text.index(MARKER_END) < new_text.index("## Active skills")
    # Block must appear after "## Configuration"
    assert new_text.index("## Configuration") < new_text.index(MARKER_START)
    # Voice body must be inside markers
    start = new_text.index(MARKER_START)
    end = new_text.index(MARKER_END)
    assert "body content here" in new_text[start:end]


def test_inject_replaces_existing_block():
    initial, _ = inject_voice_block(CLAUDE_MD_TEMPLATE, VOICE_BODY_FIXTURE)
    new_body = "## Narrative Style: Other\n\nreplacement content\n"
    replaced, warning = inject_voice_block(initial, new_body)
    assert warning is None
    assert "replacement content" in replaced
    assert "body content here" not in replaced
    # Exactly one marker pair survives
    assert replaced.count(MARKER_START) == 1
    assert replaced.count(MARKER_END) == 1


def test_inject_idempotent_same_voice():
    once, _ = inject_voice_block(CLAUDE_MD_TEMPLATE, VOICE_BODY_FIXTURE)
    twice, _ = inject_voice_block(once, VOICE_BODY_FIXTURE)
    assert once == twice


def test_inject_anchor_missing_appends_with_warning():
    no_anchor = "# Title\n\n## Configuration\n\n## House rules\n\n- thing\n"
    new_text, warning = inject_voice_block(no_anchor, VOICE_BODY_FIXTURE)
    assert warning is not None
    assert "Active skills" in warning
    assert new_text.endswith(MARKER_END + "\n")


def test_inject_duplicate_markers_raises():
    bad = (
        CLAUDE_MD_TEMPLATE
        + f"\n{MARKER_START}\nfirst\n{MARKER_END}\n"
        + f"\n{MARKER_START}\nsecond\n{MARKER_END}\n"
    )
    with pytest.raises(VoiceFormatError, match="[Mm]alformed|duplicate"):
        inject_voice_block(bad, VOICE_BODY_FIXTURE)


def test_inject_unbalanced_markers_raises():
    bad = CLAUDE_MD_TEMPLATE + f"\n{MARKER_START}\norphaned start\n"
    with pytest.raises(VoiceFormatError, match="[Mm]alformed"):
        inject_voice_block(bad, VOICE_BODY_FIXTURE)


def test_inject_end_before_start_raises():
    bad = CLAUDE_MD_TEMPLATE + f"\n{MARKER_END}\nweird\n{MARKER_START}\n"
    with pytest.raises(VoiceFormatError, match="end before start"):
        inject_voice_block(bad, VOICE_BODY_FIXTURE)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_voices.py -v`
Expected: FAIL — `ImportError` on `inject_voice_block`, `MARKER_START`, `MARKER_END`.

- [ ] **Step 3: Implement inject_voice_block**

Append to `src/solo_roll/voices.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_voices.py -v`
Expected: PASS (all tests, ~16 total).

- [ ] **Step 5: Run full suite**

Run: `pytest --tb=short -q`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/voices.py tests/test_voices.py
git commit -m "feat(voices): add inject_voice_block helper with marker handling"
```

---

### Task 4: Ship data/voices/default.md

**Files:**
- Create: `data/voices/default.md`

This must exist before scaffold tests can exercise the no-flag default.

- [ ] **Step 1: Create the voice file**

`data/voices/default.md`:
```markdown
# Narrative Style: Default

## Scope

These rules govern in-fiction narration only. Mechanical reporting (rolls,
stat changes, move announcements, oracle results) stays plain — no styled
prose for "Roll 8 vs CF 6" or "+1 momentum."

## Beat budget

Write 1-3 sentences per beat, then stop and hand control back. After any
single image or action, pause. Do not chain beats together with conjunctions
or em-dashes. The player drives the next beat.

## Hard rules

- No "begins to" / "starts to" / "started to" — use the verb directly.
- No three-item sensory lists (sight + sound + smell rolled into one
  paragraph).
- No abstract noun phrases: "a sense of dread", "a wave of unease",
  "a feeling of foreboding". Show the dread; do not name it.
- No em-dash-explainer balanced compounds: "She wasn't refusing — she was
  counting." Either say one or the other.
- No italicized free-indirect thought used to explain subtext to the
  reader.
- Every sentence grounds in concrete sensory or action detail.
- Avoid Latinate filler ("commenced", "proceeded to", "in the direction
  of"). Plain Anglo-Saxon verbs.
- Do not editorialize on the player's choices. Do not call a position
  "strong", "favorable", "well-played", or similar. Report; do not coach.

## Voice notes

Plain, direct, contemporary. No specific author anchor — this is the
neutral baseline. Lean toward concrete nouns and active verbs. Trust the
reader. When in doubt, cut a sentence.

## Examples

### Bad / Good — exploration

**BAD:**
> The forest path begins to narrow as Cadoc proceeds deeper into the
> ancient woods, a sense of unease creeping over him as the canopy thickens
> overhead, blocking out the warm afternoon sunlight that had been guiding
> his way.

**GOOD:**
> The path narrowed. Cadoc kept walking. The canopy closed overhead and
> the light went thin and green.

### Bad / Good — dialogue

**BAD:**
> "I see," the merchant said thoughtfully, stroking his beard in a
> contemplative manner. He wasn't agreeing — he was deciding whether you
> were worth his time.

**GOOD:**
> The merchant looked at him for a long moment. "I see," he said. He
> didn't say anything else.

### Bad / Good — combat / consequence

**BAD:**
> A surge of pain washed over Cadoc as the blade found its mark, sending
> waves of agony radiating through his shoulder, his vision beginning to
> blur as the world seemed to tilt around him.

**GOOD:**
> The blade caught him in the shoulder. He went down on one knee. Bran
> was barking somewhere far away.
```

- [ ] **Step 2: Verify with load_voice**

Run: `python -c "from pathlib import Path; from solo_roll.voices import load_voice; n, b = load_voice('default', Path('data/voices')); print(n); print(len(b), 'chars')"`
Expected: Prints `Default` and a body length > 1000.

- [ ] **Step 3: Commit**

```bash
git add data/voices/default.md
git commit -m "feat(voices): add default voice — neutral prose discipline"
```

---

### Task 5: campaign.py — wire --voice flag into scaffold

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_campaign.py` (or wherever subprocess tests sit):
```python
def test_scaffold_default_voice_injects_default_block(tmp_path):
    target = tmp_path / "camp"
    result = subprocess.run(
        ["solo-campaign", "Camp", str(target), "--skills", "none"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    claude_md = (target / "CLAUDE.md").read_text()
    assert "<!-- voice:start -->" in claude_md
    assert "<!-- voice:end -->" in claude_md
    assert "## Narrative Style: Default" in claude_md


def test_scaffold_voice_none_skips_injection(tmp_path):
    target = tmp_path / "camp"
    result = subprocess.run(
        ["solo-campaign", "Camp", str(target),
         "--skills", "none", "--voice", "none"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    claude_md = (target / "CLAUDE.md").read_text()
    assert "<!-- voice:start -->" not in claude_md
    assert "## Narrative Style:" not in claude_md


def test_scaffold_unknown_voice_errors(tmp_path):
    target = tmp_path / "camp"
    result = subprocess.run(
        ["solo-campaign", "Camp", str(target),
         "--skills", "none", "--voice", "nonsense"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "nonsense" in result.stderr or "Voice not found" in result.stderr
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_campaign.py -v -k voice`
Expected: FAIL — flag not recognized / voice not injected.

- [ ] **Step 3: Modify campaign.py — add imports, flag, helper, injection call, and error handling**

**3a. Add imports** at the top of `src/solo_roll/campaign.py`, alongside existing imports:
```python
from solo_roll.voices import (
    VoiceError,
    inject_voice_block,
    load_voice,
)
```

**3b. Add helper** near the other helpers (e.g., after `_parse_skills_arg`):
```python
def _inject_voice_into_campaign(
    campaign_path: Path,
    voice_name: str,
    voices_dir: Path,
) -> str | None:
    """Load voice and inject block into campaign CLAUDE.md.

    Returns optional warning string from inject_voice_block, or None.
    Raises VoiceNotFoundError / VoiceFormatError on failure.
    """
    _, body = load_voice(voice_name, voices_dir)
    claude_md_path = campaign_path / "CLAUDE.md"
    new_text, warning = inject_voice_block(claude_md_path.read_text(), body)
    claude_md_path.write_text(new_text)
    return warning
```

**3c. Add the flag** in `main()` after the `--skills` argument:
```python
    parser.add_argument(
        "--voice", type=str, default=None, dest="voice",
        help="Narrative voice to inject into campaign CLAUDE.md "
             "(default: 'default'). Use 'none' to skip injection.",
    )
```

**3d. Wire injection** in `main()` between `_create_campaign(...)` and
`_install_skills(...)` (so CLAUDE.md exists when we inject):
```python
    voices_source = repo_root / "data" / "voices"
    voice_choice = args.voice if args.voice is not None else "default"
    if voice_choice.lower() != "none":
        warning = _inject_voice_into_campaign(target, voice_choice, voices_source)
        if warning:
            print(f"warning: {warning}", file=sys.stderr)
```

**3e. Extend the existing `except` tuple** in `main()` to catch `VoiceError`.
Change:
```python
    except (CampaignError, FileExistsError, IsADirectoryError,
            OSError, subprocess.CalledProcessError) as exc:
```
to:
```python
    except (CampaignError, VoiceError, FileExistsError, IsADirectoryError,
            OSError, subprocess.CalledProcessError) as exc:
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_campaign.py -v -k voice`
Expected: PASS (3 new tests).

- [ ] **Step 5: Run full suite**

Run: `pytest --tb=short -q`
Expected: All green. No regressions.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat(campaign): add --voice flag, inject voice block at scaffold time"
```

---

### Task 6: campaign.py — `voice list` subcommand

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

The CLI shape becomes a hybrid: positional usage for scaffold, `voice <action>` form for voice ops. Use argparse subparsers.

- [ ] **Step 1: Add failing test**

Append to `tests/test_campaign.py`:
```python
def test_voice_list_prints_available_voices():
    result = subprocess.run(
        ["solo-campaign", "voice", "list"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "default" in result.stdout
    # Output should include display name from H1
    assert "Default" in result.stdout
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_campaign.py::test_voice_list_prints_available_voices -v`
Expected: FAIL — argparse rejects "voice" as a name positional.

- [ ] **Step 3: Extend voices import**

Find the `from solo_roll.voices import (...)` block at the top of
`src/solo_roll/campaign.py` (added in Task 5). Add `list_voices` to the
imported names so it becomes:
```python
from solo_roll.voices import (
    VoiceError,
    inject_voice_block,
    list_voices,
    load_voice,
)
```

If `re` is not yet imported at the top of `src/solo_roll/campaign.py`, add
`import re` to the standard-library import block.

- [ ] **Step 4: Refactor argparse to use subcommands**

In `main()`, restructure parsing. Replace the existing `parser.add_argument("name", ...)` and `parser.add_argument("path", ...)` with a subparser layout:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="solo-campaign",
        description="Scaffold a new solo RPG campaign folder.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Default scaffold command (no subcommand keyword).
    # We achieve "solo-campaign <name> <path>" by making scaffold the
    # default when first arg is not a known subcommand.
    scaffold = subparsers.add_parser("scaffold", help="Create a new campaign")
    scaffold.add_argument("name", help="Display name for the campaign")
    scaffold.add_argument("path", help="Target campaign directory (must not exist)")
    scaffold.add_argument("--skills", type=str, default=None, dest="skills",
                          help="Comma-separated skill names (default: all). "
                               "Use 'none' to install no skills.")
    scaffold.add_argument("--voice", type=str, default=None, dest="voice",
                          help="Narrative voice to inject (default: 'default'). "
                               "Use 'none' to skip.")

    voice_cmd = subparsers.add_parser("voice", help="Voice management")
    voice_subs = voice_cmd.add_subparsers(dest="voice_action")
    voice_list = voice_subs.add_parser("list", help="List available voices")

    # Manual dispatch: if argv[0] is not a registered subcommand, treat as
    # implicit `scaffold <argv...>` for backward compatibility.
    raw = list(sys.argv[1:] if argv is None else argv)
    known_subs = {"scaffold", "voice"}
    if raw and raw[0] not in known_subs and not raw[0].startswith("-"):
        raw = ["scaffold"] + raw
    args = parser.parse_args(raw)

    if args.command == "voice":
        return _voice_command(args)
    if args.command == "scaffold" or args.command is None:
        return _scaffold_command(args)
    parser.print_help()
    return 2
```

Move the existing scaffold body into `_scaffold_command(args)`. Add `_voice_command`:
```python
def _voice_command(args) -> int:
    repo_root = _resolve_repo_root()
    voices_dir = repo_root / "data" / "voices"
    if args.voice_action == "list":
        return _voice_list(voices_dir)
    print("usage: solo-campaign voice {list}", file=sys.stderr)
    return 2


def _voice_list(voices_dir: Path) -> int:
    names = list_voices(voices_dir)
    if not names:
        print("(no voices available)")
        return 0
    for name in names:
        try:
            display, body = load_voice(name, voices_dir)
            # First non-empty line of "## Voice notes" is the description.
            desc = _voice_first_note_line(body)
        except Exception:
            display, desc = name, "(invalid voice file)"
        print(f"  {name:20s} — {display}: {desc}")
    return 0


def _voice_first_note_line(body: str) -> str:
    """Extract the first non-blank sentence after the '## Voice notes' heading."""
    m = re.search(r"^## Voice notes\s*\n+(.*?)(?:\n##|\Z)",
                  body, re.DOTALL | re.MULTILINE)
    if not m:
        return "(no voice notes)"
    para = m.group(1).strip().split("\n\n", 1)[0].strip()
    # Trim to first sentence (or 80 chars).
    first = para.split(". ", 1)[0].rstrip(".")
    return (first[:80] + "...") if len(first) > 80 else first
```

(`re` is already imported at module top via the imports added in Task 5 — `voices.py` uses it; campaign.py needs to add `import re` to its top-level imports if not already present. Verify by `grep "^import re" src/solo_roll/campaign.py` — if no match, add `import re` to the import block.)

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_campaign.py -v -k voice`
Expected: PASS for all 4 voice tests.

- [ ] **Step 6: Run full suite**

Run: `pytest --tb=short -q`
Expected: All green. The implicit-scaffold dispatch must keep `solo-campaign Foo /path` working as before.

- [ ] **Step 7: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat(campaign): add 'voice list' subcommand, refactor to subparsers"
```

---

### Task 7: campaign.py — `voice apply` subcommand

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_campaign.py`:
```python
def test_voice_apply_inserts_block_when_absent(tmp_path):
    # Scaffold without voice, then apply.
    target = tmp_path / "camp"
    subprocess.run(
        ["solo-campaign", "Camp", str(target),
         "--skills", "none", "--voice", "none"],
        check=True,
    )
    claude_md = target / "CLAUDE.md"
    assert "<!-- voice:start -->" not in claude_md.read_text()

    result = subprocess.run(
        ["solo-campaign", "voice", "apply", str(target), "default"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    text = claude_md.read_text()
    assert "<!-- voice:start -->" in text
    assert "## Narrative Style: Default" in text


def test_voice_apply_idempotent(tmp_path):
    target = tmp_path / "camp"
    subprocess.run(
        ["solo-campaign", "Camp", str(target),
         "--skills", "none", "--voice", "default"],
        check=True,
    )
    claude_md = target / "CLAUDE.md"
    text_before = claude_md.read_text()

    result = subprocess.run(
        ["solo-campaign", "voice", "apply", str(target), "default"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    text_after = claude_md.read_text()
    assert text_before == text_after


def test_voice_apply_missing_campaign_errors(tmp_path):
    result = subprocess.run(
        ["solo-campaign", "voice", "apply",
         str(tmp_path / "nonexistent"), "default"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "CLAUDE.md" in result.stderr or "not found" in result.stderr.lower()


def test_voice_apply_unknown_voice_errors(tmp_path):
    target = tmp_path / "camp"
    subprocess.run(
        ["solo-campaign", "Camp", str(target),
         "--skills", "none", "--voice", "default"],
        check=True,
    )
    result = subprocess.run(
        ["solo-campaign", "voice", "apply", str(target), "nonsense"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "nonsense" in result.stderr or "Voice not found" in result.stderr


def test_voice_apply_duplicate_markers_errors(tmp_path):
    target = tmp_path / "camp"
    subprocess.run(
        ["solo-campaign", "Camp", str(target),
         "--skills", "none", "--voice", "default"],
        check=True,
    )
    claude_md = target / "CLAUDE.md"
    # Corrupt: duplicate the existing block.
    text = claude_md.read_text()
    extra = "\n<!-- voice:start -->\nx\n<!-- voice:end -->\n"
    claude_md.write_text(text + extra)

    result = subprocess.run(
        ["solo-campaign", "voice", "apply", str(target), "default"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "Malformed" in result.stderr or "manually" in result.stderr.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_campaign.py -v -k voice_apply`
Expected: FAIL — `apply` subcommand not registered.

- [ ] **Step 3: Add `voice apply` to argparse + dispatch**

In `main()`, extend the voice subparser:
```python
    voice_apply = voice_subs.add_parser("apply",
        help="Re-inject or swap voice block in an existing campaign")
    voice_apply.add_argument("campaign_path", help="Existing campaign directory")
    voice_apply.add_argument("voice_name", help="Voice to inject")
```

Extend `_voice_command`:
```python
def _voice_command(args) -> int:
    repo_root = _resolve_repo_root()
    voices_dir = repo_root / "data" / "voices"
    if args.voice_action == "list":
        return _voice_list(voices_dir)
    if args.voice_action == "apply":
        return _voice_apply(
            Path(args.campaign_path).expanduser(),
            args.voice_name,
            voices_dir,
        )
    print("usage: solo-campaign voice {list,apply}", file=sys.stderr)
    return 2


def _voice_apply(campaign_path: Path, voice_name: str,
                 voices_dir: Path) -> int:
    claude_md = campaign_path / "CLAUDE.md"
    if not claude_md.is_file():
        print(f"error: CLAUDE.md not found at {claude_md}", file=sys.stderr)
        return 1
    try:
        warning = _inject_voice_into_campaign(
            campaign_path, voice_name, voices_dir,
        )
    except VoiceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"voice '{voice_name}' applied to {campaign_path}")
    return 0
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_campaign.py -v -k voice`
Expected: All voice-related tests pass (~9 voice tests total).

- [ ] **Step 5: Run full suite**

Run: `pytest --tb=short -q`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat(campaign): add 'voice apply' subcommand for existing campaigns"
```

---

### Task 8: Manual smoke test of the CLI surface

This is a no-code verification step. Catches integration issues that unit/subprocess tests miss.

- [ ] **Step 1: Reinstall the editable tool to pick up new entry-point flags**

Run: `uv tool install --editable . --reinstall`
Expected: Reinstalls `solo-campaign` and `solo-roll` from local source.

- [ ] **Step 2: Smoke-test scaffold + voice list + voice apply**

Run:
```bash
TMPCAMP=$(mktemp -d)/smoke
solo-campaign "Smoke" "$TMPCAMP" --skills none
grep -c "voice:start" "$TMPCAMP/CLAUDE.md"      # expect 1
solo-campaign voice list                         # expect "default" line
solo-campaign voice apply "$TMPCAMP" default     # idempotent
diff <(cat "$TMPCAMP/CLAUDE.md") <(cat "$TMPCAMP/CLAUDE.md")  # no-op sanity
rm -rf "$(dirname "$TMPCAMP")"
```
Expected: Each command succeeds. `grep -c` returns 1.

- [ ] **Step 3: No commit (verification only)**

Skip commit — this is a runtime check, not a code change.

---

### Task 9: Ship data/voices/folkloric.md

**Files:**
- Create: `data/voices/folkloric.md`

- [ ] **Step 1: Create the voice file**

`data/voices/folkloric.md`:
```markdown
# Narrative Style: Folkloric

## Scope

These rules govern in-fiction narration only. Mechanical reporting (rolls,
stat changes, move announcements, oracle results) stays plain — no styled
prose for "Roll 8 vs CF 6" or "+1 momentum."

## Beat budget

Write 1-3 sentences per beat, then stop and hand control back. After any
single image or action, pause. Do not chain beats together with conjunctions
or em-dashes. The player drives the next beat.

## Hard rules

- No "begins to" / "starts to" / "started to" — use the verb directly.
- No three-item sensory lists.
- No abstract noun phrases ("a sense of X", "a wave of Y", "a feeling of Z").
- No em-dash-explainer balanced compounds ("She wasn't refusing — she was
  counting"). Pick one and let it stand.
- No italicized free-indirect thought used to explain subtext.
- Every sentence grounds in concrete sensory or action detail.
- One grounded metaphor per beat maximum, and only when drawn from working
  life — wood, road, cloth, water, weather, livestock — never from abstract
  emotion or interior weather.
- Plain Anglo-Saxon vocabulary preferred over Latinate. Say "stone", not
  "edifice"; "walk", not "perambulate".
- Do not editorialize on the player's choices.

## Voice notes

In the mode of Robin Hobb and Ursula Le Guin. Warmer than grim — sensory,
willing to let an image land — but disciplined: each image lands once and is
not hammered. Subtext sits without explanation. Interior life is implied
through gesture, not narrated. Trust the reader to feel weight without being
told what to feel.

## Examples

### Bad / Good — exploration

**BAD:**
> A wave of foreboding swept over Cadoc as the path began to narrow into
> the deep, ancient forest, the thick canopy above blocking out the warm
> afternoon sun and casting everything in an eerie, unsettling green half-
> light that seemed to whisper of forgotten things.

**GOOD:**
> The path narrowed where the old beeches grew close. Cadoc walked under
> them and the light came down green, the way it does under old leaves.
> The forest had a sound he did not know. He walked on.

### Bad / Good — dialogue

**BAD:**
> "I have four people I'd call fighters," she said, her voice carrying the
> weight of impossible decisions. She wasn't refusing — she was counting,
> her mind racing through the brutal arithmetic of survival in a hard
> land.

**GOOD:**
> The fire spoke twice before Wren did. A pop, then another, like dry wood
> saying its piece.
>
> "I have four fighters," she said at last. "Two are also our best
> hunters. To send them is to go hungry come winter." Her hands lay flat
> on her knees, still.

### Bad / Good — combat / consequence

**BAD:**
> A surge of agony radiated through Cadoc's body as the blade found its
> mark, his vision beginning to blur as a sense of impending doom washed
> over him. He felt his strength leaving him like water from a broken
> jar.

**GOOD:**
> The blade caught him under the collarbone. He went down on one knee.
> Bran was barking somewhere he could not see, and the road was tilting
> under him the way a deck tilts in a swell.
```

- [ ] **Step 2: Verify with load_voice**

Run: `python -c "from pathlib import Path; from solo_roll.voices import load_voice; n, b = load_voice('folkloric', Path('data/voices')); print(n)"`
Expected: Prints `Folkloric`.

- [ ] **Step 3: Commit**

```bash
git add data/voices/folkloric.md
git commit -m "feat(voices): add folkloric voice — Hobb/Le Guin anchor"
```

---

### Task 10: Ship data/voices/grim-grounded.md

**Files:**
- Create: `data/voices/grim-grounded.md`

- [ ] **Step 1: Create the voice file**

`data/voices/grim-grounded.md`:
```markdown
# Narrative Style: Grim & Grounded

## Scope

These rules govern in-fiction narration only. Mechanical reporting (rolls,
stat changes, move announcements, oracle results) stays plain — no styled
prose for "Roll 8 vs CF 6" or "+1 momentum."

## Beat budget

Write 1-3 sentences per beat, then stop and hand control back. After any
single image or action, pause. Do not chain beats together. The player
drives the next beat.

## Hard rules

- No "begins to" / "starts to" / "started to".
- No three-item sensory lists.
- No abstract noun phrases ("a sense of X", "a wave of Y", "a feeling of Z").
- No em-dash-explainer balanced compounds.
- No italicized free-indirect thought.
- No "beautiful" descriptions of landscape or character. The world is
  weather, dirt, and weight.
- Characters are observed via what they do, not what they think. Interior
  life is rare and earned.
- Short declarative sentences predominate. A long sentence is a deliberate
  choice, never a default.
- Dry irony is permitted. Sentiment is not.
- Do not editorialize on the player's choices.

## Voice notes

In the mode of Joe Abercrombie and K.J. Parker. Bodies and weight before
atmosphere. The world is hard and the people in it are not heroic.
Violence has consequences and the consequences are physical. When in
doubt, cut.

## Examples

### Bad / Good — exploration

**BAD:**
> The ancient forest stretched before them, its towering canopy blocking
> out most of the warm afternoon sunlight, casting an eerie green
> half-light that seemed to whisper of forgotten things and lost paths.
> Cadoc felt a sense of unease wash over him as he proceeded forward.

**GOOD:**
> The path went into the trees and got narrower. The light went thin.
> Cadoc kept walking. Bran kept up.

### Bad / Good — dialogue

**BAD:**
> "I have four people I'd call fighters," she said, her voice carrying
> the weight of leadership. She wasn't refusing — she was performing the
> grim arithmetic of a leader who has too few hands and too much winter
> ahead.

**GOOD:**
> Wren let the fire pop twice before she answered.
>
> "Four fighters. Two of them my best hunters. Lose them, we go hungry
> come winter."
>
> She wasn't saying no. She was doing arithmetic.

### Bad / Good — combat / consequence

**BAD:**
> Searing pain radiated from his shoulder as the blade found its mark,
> his vision swimming as a wave of nauseous dread overtook him, the
> realization beginning to dawn that this might be where he died.

**GOOD:**
> The blade went in under the collarbone. Cadoc felt it stop against
> bone. He went down. The world stayed the same — there was no big
> moment, just the ground coming up and then the ground.
```

- [ ] **Step 2: Verify with load_voice**

Run: `python -c "from pathlib import Path; from solo_roll.voices import load_voice; n, b = load_voice('grim-grounded', Path('data/voices')); print(n)"`
Expected: Prints `Grim & Grounded`.

- [ ] **Step 3: Commit**

```bash
git add data/voices/grim-grounded.md
git commit -m "feat(voices): add grim-grounded voice — Abercrombie/Parker anchor"
```

---

### Task 11: tests/test_voices_content.py — pin shipped voice contracts

**Files:**
- Create: `tests/test_voices_content.py`

- [ ] **Step 1: Write the test file**

`tests/test_voices_content.py`:
```python
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
    # "**BAD:**" should appear at least 3 times (one per pair).
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
    from solo_roll.voices import list_voices
    available = set(list_voices(VOICES_DIR))
    for name in SHIPPED_VOICES:
        assert name in available, f"{name} not surfaced by list_voices"
```

- [ ] **Step 2: Run the new tests**

Run: `pytest tests/test_voices_content.py -v`
Expected: PASS — all parametrized tests for default/folkloric/grim-grounded.

- [ ] **Step 3: Run full suite**

Run: `pytest --tb=short -q`
Expected: All green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_voices_content.py
git commit -m "test(voices): pin content contract for shipped voice files"
```

---

### Task 12: Update ROADMAP

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Mark sub-project complete**

Open `docs/ROADMAP.md`. Find sub-project 5.6's last open prose item:
```
- [ ] Prose style: GM narration too florid. Fix via campaign `CLAUDE.md` prose block first ...
```

Replace with:
```
- [x] Prose style: shipped via standalone narrative-voices sub-project. See
      `docs/superpowers/specs/2026-04-30-narrative-voices-design.md` and
      `docs/superpowers/plans/2026-04-30-narrative-voices.md`. Voices live in
      `data/voices/`; campaigns receive a chosen voice block via
      `solo-campaign --voice <name>` (default: `default`) injected into
      CLAUDE.md.
```

Add a new sub-project section after 5.6, marked complete:
```markdown
---

## Sub-project 5.7: Narrative Voices

Per-campaign GM prose discipline. Voices ship as standalone markdown in
`data/voices/`, injected into the campaign's `CLAUDE.md` at scaffold time
inside HTML-comment marker block. Frozen-snapshot semantics — campaigns
do not drift when toolkit voice files change. `solo-campaign voice apply`
re-injects/swaps for existing campaigns.

- [x] Spec: `docs/superpowers/specs/2026-04-30-narrative-voices-design.md`
- [x] Plan: `docs/superpowers/plans/2026-04-30-narrative-voices.md`
- [x] `voices.py` — loader, validator, injection helper
- [x] `solo-campaign --voice <name>` flag at scaffold time
- [x] `solo-campaign voice list` subcommand
- [x] `solo-campaign voice apply <campaign> <voice>` subcommand
- [x] Ship voices: `default.md`, `folkloric.md`, `grim-grounded.md`
- [x] Skill-content tests pinning scope clause + required sections + word cap
```

- [ ] **Step 2: Run full suite once more**

Run: `pytest --tb=short -q`
Expected: All green.

- [ ] **Step 3: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark sub-project 5.7 narrative voices complete"
```

---

## Self-Review Notes

Spec coverage check:

| Spec section | Implemented in task |
|---|---|
| `data/voices/<name>.md` location | Tasks 4, 9, 10 |
| Voice file shape (H1, sections, scope pin, examples) | Tasks 4, 9, 10, 11 |
| `solo-campaign --voice <name>` flag | Task 5 |
| `--voice none` opt-out | Task 5 |
| Default → `default.md` when omitted | Task 5 |
| `voice apply` subcommand | Task 7 |
| `voice list` subcommand | Task 6 |
| Block markers (HTML comments) | Task 3 |
| Injection algorithm (insert/replace/marker validation) | Task 3 |
| Anchor location (`## Active skills`) | Task 3 |
| Anchor missing → append + warn | Task 3 |
| Malformed/duplicate marker error | Task 3, 7 |
| Typed exceptions (`VoiceError`/`VoiceNotFoundError`/`VoiceFormatError`) | Tasks 1-3 |
| Voice content tests | Task 11 |
| CLI tests | Tasks 5-7 |
| Injection unit tests | Task 3 |
| 800-word cap | Task 11 |
| Scope pin substring assertion | Tasks 1-2, 11 |
| `_template.md` (deferred) | Out of scope per spec |

No gaps. All decision points from the spec land in a task.

Type / signature consistency: `load_voice` returns `(display_name, body)` consistently across tasks 2, 5, 6, 7. `inject_voice_block` returns `(new_text, warning)` in tasks 3, 5, 7. Marker constants `MARKER_START` / `MARKER_END` defined once in task 3, referenced in tests for tasks 5, 7.
