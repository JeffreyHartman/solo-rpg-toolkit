# Campaign Bootstrap Script — Design Spec

**Date:** 2026-04-24
**Sub-project:** 3 of 7 (Solo RPG GM Assistant Roadmap)
**Goal:** One command to scaffold a new campaign folder, install skills, and ensure `solo-roll` is on PATH.

---

## Motivation

Today, starting a fresh campaign requires manually:
1. Copying `example-campaign/` to a new location and renaming
2. Editing `CLAUDE.md` to set `PLAYER_VAULT_PATH`
3. Copying three skill dirs to `~/.claude/skills/`
4. Installing `solo-roll` via `uv tool install --editable .`
5. Creating the Obsidian vault subfolder structure

Sub-project 3 collapses these steps into a single idempotent command.

---

## Architecture

A new entry point `solo-campaign` is added as a second console_script in `pyproject.toml`, backed by a new module `src/solo_roll/campaign.py`. The same `uv tool install --editable .` that installs `solo-roll` also installs `solo-campaign` — no separate package.

The script resolves the toolkit repo root via `Path(__file__).resolve().parents[2]` (same convention `src/solo_roll/__init__.py` uses for `DEFAULT_DATA_DIR`). Because installs are editable, symlinks created by the script point back to the live worktree, so repo edits propagate immediately to `~/.claude/skills/`.

**Synopsis:**
```
solo-campaign <name> <campaign-path> [--vault <vault-path>] [--skills-dir <dir>]
```

One command. Idempotent. Fails fast on conflicts.

---

## Components

Single module `src/solo_roll/campaign.py` with focused functions:

| Function | Responsibility |
|---|---|
| `main(argv)` | argparse setup + orchestration |
| `_resolve_repo_root()` | locates toolkit repo via `__file__` |
| `_create_campaign(name, target, vault_path)` | copies `example-campaign/` to target, substitutes placeholders in `CLAUDE.md` |
| `_install_skills(repo_root, skills_dir)` | symlinks each `skills/<name>` to `<skills_dir>/<name>` |
| `_ensure_solo_roll(repo_root)` | checks `shutil.which("solo-roll")`; runs `uv tool install --editable <repo>` if missing |
| `_create_vault(vault_path)` | `mkdir -p` for vault root + 5 subdirs |
| `_prompt_vault_path()` | interactive `input()` if `--vault` not given and stdin is tty |

---

## Data flow (happy path)

```
$ solo-campaign "Bleak Winter" ~/rpg/bleak-winter --vault ~/Obsidian/Solo

  1. resolve repo root from __file__
  2. validate ~/rpg/bleak-winter does not exist  → error 1 if exists
  3. shutil.copytree example-campaign/ → ~/rpg/bleak-winter/
  4. read ~/rpg/bleak-winter/CLAUDE.md
     replace "[Campaign Name]" → "Bleak Winter"
     replace "/CHANGE/ME/path/to/Obsidian/Vault/Solo Campaign" → vault path
  5. for each name in (ironsworn, mythic-gme, solo-journaler):
       os.symlink(repo/skills/<name>, ~/.claude/skills/<name>)
       (replace if existing symlink; error if real dir)
  6. shutil.which("solo-roll")? skip : subprocess.run(uv tool install --editable <repo>)
  7. mkdir -p ~/Obsidian/Solo/{Session Log,People,Places,Threads,Lore}
  8. print "ready — run `claude` in ~/rpg/bleak-winter"
```

---

## CLI surface

| Arg | Required | Description |
|---|---|---|
| `<name>` | yes | Display name for the campaign (substituted into `CLAUDE.md`) |
| `<campaign-path>` | yes | Target directory. Must not exist. |
| `--vault <path>` | no | Player Obsidian vault path. Prompted if not given and stdin is tty. |
| `--skills-dir <path>` | no | Override `~/.claude/skills/` (test hook + advanced users) |

Environment variable parallel for `--skills-dir`: `CLAUDE_SKILLS_DIR` (lower priority than flag).

---

## Error handling

| Condition | Behavior |
|---|---|
| Target campaign dir exists | `error: <path> already exists` exit 1 |
| `--vault` missing AND stdin not a tty | `error: --vault required when not interactive` exit 1 |
| `<skills-dir>/<name>` exists as real dir (not symlink) | `error: refusing to replace real dir at <path>` exit 1 |
| `<skills-dir>/<name>` exists as symlink | replace it (point at current repo) |
| `uv` not on PATH AND `solo-roll` not installed | `error: uv not found — see https://docs.astral.sh/uv/` exit 1 |
| Repo `example-campaign/` missing | `error: toolkit install corrupt — example-campaign not found at <path>` exit 1 |
| Vault path creation fails (permissions) | propagate `OSError` with clear message |

All errors exit 1. Success exits 0.

---

## Testing

`tests/test_campaign.py` — unit tests using `tmp_path` fixture. No real filesystem state outside tmp.

| Test | Verifies |
|---|---|
| `test_create_campaign_copies_template` | `example-campaign/` contents land in target with substituted CLAUDE.md |
| `test_create_campaign_substitutes_name_and_vault` | `[Campaign Name]` and `/CHANGE/ME/...` are replaced |
| `test_create_campaign_target_exists_errors` | Pre-existing target dir → exit 1 |
| `test_install_skills_symlinks` | Three symlinks created in `--skills-dir` pointing at repo skills |
| `test_install_skills_replaces_existing_symlink` | Stale symlink gets pointed at current repo |
| `test_install_skills_refuses_real_dir` | Real dir at `<skills-dir>/<name>` → exit 1 |
| `test_create_vault_creates_subdirs` | All 5 subdirs created |
| `test_create_vault_idempotent` | Re-running doesn't error if dirs exist |
| `test_main_happy_path` | End-to-end via `main([...])` with all flags |
| `test_main_missing_vault_non_tty` | No `--vault` + non-tty stdin → exit 1 |

`_ensure_solo_roll` is tested only via the "already installed" branch (mock `shutil.which`). The subprocess `uv tool install` path is not unit-tested — too environment-coupled. Manual smoke test instead.

---

## Out of scope (deferred)

- Windows PowerShell equivalent — README documentation only, no code (per roadmap)
- PyPI distribution — Sub-project 7
- Custom skill set selection (e.g. only ironsworn, no mythic) — YAGNI
- Re-running `solo-campaign` to update an existing campaign's CLAUDE.md — YAGNI; user edits manually

---

## Acceptance criteria

A user can run:

```bash
cd ~/git/solo-rpg-toolkit
uv tool install --editable .
solo-campaign "Bleak Winter" ~/rpg/bleak-winter --vault ~/Obsidian/Solo
cd ~/rpg/bleak-winter
claude
```

— and the agent loads with all three skills, can call `solo-roll` for dice, and the player vault is structured for note writing on first session.
