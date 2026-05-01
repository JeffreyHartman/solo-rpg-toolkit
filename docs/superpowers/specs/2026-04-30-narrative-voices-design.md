# Narrative Voices — Design

**Date:** 2026-04-30
**Status:** Spec — pending plan
**Sub-project:** Standalone (not folded into 3.6 or 5.6)

## Problem

GM narration during play reads as dry and LLM-flavored. Common tells observed across multiple sessions: "begins to" / "starts to", balanced compound sentences with em-dash explainers, three-item sensory lists, abstract noun phrases ("a sense of unease"), italicized free-indirect thought used to explain subtext, meta-narrator commentary on what a line "really means."

Sub-project 5.6 originally scoped this as a campaign-level prose block but left the architecture open. Two interactive narration tests (sessions 2 + 4) confirmed the issue is real and that bad/good example pairs reshape both wording *and* the LLM's interpretation of identical inputs (same Mythic random event rolls, different voice anchors → different in-fiction reads).

The fix needs to be:
- System-agnostic — usable across Ironsworn, future PF2e, hex-crawl, etc.
- Always-on — must reach the LLM every turn, not via reactive tool calls.
- Per-campaign — the user does not want one voice baked into every game. Different campaigns get different prose.
- Snapshot-stable — once a campaign is using a voice, tweaking the voice file in the toolkit repo should not silently change the running campaign mid-play. Stability beats freshness.
- Cheap to author and tune — the user wants iterative back-and-forth on examples to nail down a voice before locking it in.

## Decision

Voices live as standalone markdown files in `data/voices/<name>.md`. The `solo-campaign` CLI gains a `--voice <name>` flag that injects the chosen voice's content directly into the new campaign's `CLAUDE.md` inside a delimited block. A `voice apply` subcommand re-injects or swaps the block for an already-scaffolded campaign.

Inlining the voice into `CLAUDE.md` (which is auto-loaded into the LLM's system prompt every turn) gives always-on context with zero tool calls, and frozen-snapshot semantics by default — the campaign's voice is whatever was injected at scaffold time, regardless of later edits to the toolkit's voice file. Updating a running campaign's voice is an explicit `voice apply` step.

### Why not a skill

The skill abstraction adds reactive-read overhead (LLM has to remember to read the voice file) and doesn't reach the LLM until something triggers it. Sub-project 5.6's transcript audit confirmed reference files in skills are routinely not read mid-session. Voice rules need to be in the always-loaded preamble, not behind a tool call.

### Why not Claude Code output styles

Output styles modify the global system prompt and apply to *all* output, including mechanical reporting ("Roll 8 vs CF 6", "+1 momentum"). Voice rules should govern in-fiction prose only. Output styles also live in `~/.claude/output-styles/`, outside the project repo, so they are not part of the campaign artifact.

## Components

### Voice file shape

Each voice file is a standalone markdown document. Required sections, asserted by tests:

- `# Narrative Style: <Display Name>` (H1)
- `## Scope` — explicit clause that rules govern in-fiction narration only; mechanical reporting stays plain.
- `## Beat budget` — hard cap on per-beat sentence count, instruction to hand control back after each beat.
- `## Hard rules` — bulleted list of bans. Common rules across all voices (no "begins to", no abstract noun phrases, no three-item sensory lists, no em-dash-explainer compounds, no italicized free-indirect thought) plus voice-specific additions.
- `## Voice notes` — short paragraph (~50-100 words) naming the target: author anchors, register, what to lean into, what to avoid.
- `## Examples` — three Bad/Good pairs covering scene types: exploration, dialogue, combat-or-consequence. Each pair shows an LLM-typical paragraph and a rewrite in the target voice.

Target file length: 400-600 words. Hard cap (asserted by test): 800 words. This bounds the per-turn context cost of inlining the voice into `CLAUDE.md`.

### CLI surface

`solo-campaign` gains:

```
solo-campaign <name> <path> [--voice <name>|none]
solo-campaign voice apply <campaign-path> <voice-name>
solo-campaign voice list
```

**`--voice <name>`** — used at scaffold time. Reads `data/voices/<name>.md`, validates required structure, injects content into the new campaign's `CLAUDE.md`. Validates name exists; on miss, errors with the list of available voices. When `--voice` is omitted, defaults to `default` so even no-flag campaigns get baseline prose discipline.

**`--voice none`** — explicit opt-out. No voice block written. CLAUDE.md keeps the existing template shape.

**`voice apply <campaign-path> <voice-name>`** — operates on an already-scaffolded campaign. Reads the campaign's `CLAUDE.md`:
- If voice block markers present → replace contents between markers.
- If absent → insert block immediately above `## Active skills`.
- If `## Active skills` heading also absent → append at end of file with markers; print a warning.
- Voice-name validation same as `--voice`.

**`voice list`** — prints available voice names + display name + one-line description (drawn from H1 + first sentence of `## Voice notes`). Mirrors the existing `solo-roll list` pattern.

Errors raise typed exceptions (`VoiceNotFoundError`, `VoiceFormatError`, `CampaignNotFoundError`). Only `main()` translates exceptions to exit codes, matching the existing `CampaignError` / `TableNotFoundError` convention.

### Block markers and injection

Markers are HTML comments — invisible in rendered markdown, greppable, parseable:

```
<!-- voice:start -->
## Narrative Style: <Display Name>

[full content of data/voices/<name>.md, with H1 stripped and replaced
 by the H2 above]
<!-- voice:end -->
```

The voice name is not encoded in the marker itself (no `voice:folkloric:start`). One block per CLAUDE.md, swap content via `apply`. Multiple marker pairs in a single file is a corruption case — fail loud rather than guess.

**Injection location:** after `## Configuration`, before `## Active skills`. Voice is configuration-adjacent and belongs in the always-loaded preamble.

**Injection algorithm** (shared by scaffold and `voice apply`):

1. Load voice file. Validate required sections (`Scope`, `Beat budget`, `Hard rules`, `Voice notes`, `Examples`). Validate H1 of form `# Narrative Style: <Display Name>`; raise `VoiceFormatError` if H1 missing or does not match this pattern.
2. Parse `<Display Name>` as the substring after `Narrative Style: ` in the H1. Strip H1 line from content. Prepend `## Narrative Style: <Display Name>` to the remaining body.
3. Wrap in `<!-- voice:start -->` / `<!-- voice:end -->` markers.
4. Read target `CLAUDE.md`. If file missing, raise `CampaignNotFoundError`.
5. Count `<!-- voice:start -->` markers and `<!-- voice:end -->` markers separately:
   - Both counts 0 → locate `## Active skills` heading. If found, insert block above it with one blank line buffer either side. If not found, append at end of file with markers; print warning.
   - Both counts 1, in order (start before end) → replace contents between (and including) the markers.
   - Counts unequal, or end-before-start, or 2+ of either → exit non-zero with "Malformed or duplicate voice markers in CLAUDE.md, fix manually."
6. Write back. Preserve trailing newline.

The injection helper is a pure function with paths and content passed in — no `Path.home()` or `__file__` reaches inside. This matches the toolkit convention and keeps the helper unit-testable in isolation.

### Initial voices

Three voice files ship in v1:

- **`default.md`** — neutral discipline. No author anchor. Goal: even no-flag campaigns get baseline tell-elimination + beat budget. Bad/good pairs use neutral fantasy beats. Tweakable per-campaign without breaking the model. ~400 words.
- **`folkloric.md`** — Voice B from the brainstorming session. Hobb / Le Guin anchor. Warmer, sensory but disciplined. Single grounded metaphor allowance per beat (drawn from working life, not abstract emotion). Plain Anglo-Saxon vocabulary preferred over Latinate. Bad/good pairs: dialogue beat (reworked from session-2 Wren scene), exploration/random-event beat (reworked from session-4 Redgate approach), one combat-or-consequence beat written fresh. ~500-600 words.
- **`grim-grounded.md`** — Voice A from the brainstorming session. Abercrombie / Parker anchor. Short declaratives, dry, body-and-weight. Ships ready for darker campaign tone. Same scenarios as folkloric, rewritten in voice.

`_template.md` for user-authored voices is deferred to a follow-up — easy to add later, adds drag in v1.

### Testing

Three test layers, matching existing pytest conventions (`tmp_path`, `monkeypatch`, no real filesystem outside tmp).

**Voice file content tests** (new file `tests/test_voices_content.py`):

- Each shipped voice file has the required H1 + sections (`Scope`, `Beat budget`, `Hard rules`, `Voice notes`, `Examples`).
- `Examples` section contains three Bad/Good pairs labeled for the three scene types.
- Scope clause contains the substring "in-fiction narration only" (exact-substring pin to catch silent edits).
- File length under 800 words.

**CLI tests** (extend `tests/test_campaign.py`):

- `solo-campaign foo <tmp> --voice folkloric` → CLAUDE.md contains markers and folkloric content.
- `solo-campaign foo <tmp>` (no flag) → CLAUDE.md contains default voice block.
- `solo-campaign foo <tmp> --voice none` → no markers, no block.
- `solo-campaign foo <tmp> --voice nonsense` → exits non-zero, stderr names available voices.
- `solo-campaign voice apply <campaign> grim-grounded` against an existing folkloric campaign → block swapped, markers preserved, rest of CLAUDE.md byte-identical.
- Running `voice apply` twice with the same voice produces an identical file (idempotency).
- `voice apply` against a `--voice none` campaign (no markers) → block inserted near `## Active skills`.
- `voice apply` against CLAUDE.md with duplicate or malformed markers (e.g. start without end) → exits non-zero with "fix manually" error.
- `voice apply` against a missing campaign → `CampaignNotFoundError` exit.
- `solo-campaign voice list` → prints all three voice names with display name and one-liner.

**Injection unit tests** (new file `tests/test_voice_injection.py`):

- Pure-function tests on the inject helper. Helper takes voice content string and CLAUDE.md content string, returns new CLAUDE.md content. No filesystem.
- Cover: insert-when-absent, replace-when-present, multi-marker error, missing-`## Active skills`-heading fallback (append at end + return warning flag).

**Not tested:**

- Live LLM behavior. Whether Claude actually obeys the injected voice is verified by playing test scenes manually, not by pytest.
- Snapshot/golden of CLAUDE.md output. One canonical case is acceptable but does not proliferate across every test.

## Out of scope (v1)

- Hardboiled / McCarthy voice (rejected during brainstorming).
- Voice mixing per scene type (combat = grim, dialogue = folkloric, etc.).
- Per-scene-type voice overlays.
- `_template.md` for user-authored voices.
- Live editing of a running campaign's voice from inside Claude Code (e.g. `/voice swap grim-grounded`).
- Voice files for systems other than Ironsworn-flavored fantasy. Voices ship as system-agnostic prose discipline; setting-specific voices (e.g. urban noir, hard SF) are future additions.

## Risks and mitigations

- **Context-window cost.** Voice block lives in CLAUDE.md every turn. Mitigation: 800-word hard cap, asserted by test. Voice files stay rules + examples, no prose-about-prose.
- **Voice rules leak into mechanical reporting.** Mitigation: every voice file's `## Scope` section explicitly limits rules to in-fiction narration. Test pins the substring.
- **Snapshot stability surprise.** Users may expect tweaking `data/voices/folkloric.md` in the toolkit to update existing campaigns. Mitigation: README documents the snapshot model and the `voice apply` workflow for explicit refresh.
- **Mid-tuning iteration friction.** During voice authorship the loop is: edit voice file → `voice apply` to test campaign → restart Claude Code session → run scene. Friction is acceptable per user — not blocking.

## Open questions

None. All resolved during brainstorming.
