# Campaign Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `solo-campaign` CLI that scaffolds a fresh campaign folder, symlinks skills to `~/.claude/skills/`, ensures `solo-roll` is installed, and creates the Obsidian vault subdir structure — all in one idempotent command.

**Architecture:** Single new module `src/solo_roll/campaign.py` with focused functions injected with paths (testable). Second console_script entry in `pyproject.toml`. Tests use `tmp_path` fixture; subprocess-based `uv tool install` path is mocked, not exercised.

**Tech Stack:** Python 3.10+, argparse, pathlib, shutil, os.symlink, subprocess. pytest with tmp_path.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/solo_roll/campaign.py` | New: all bootstrap logic + `main()` entry point |
| `pyproject.toml` | Modify: add `solo-campaign` console_script |
| `tests/test_campaign.py` | New: unit tests + happy-path integration test |
| `README.md` | Modify: add `solo-campaign` usage + Windows manual fallback |
| `docs/ROADMAP.md` | Modify: check off Sub-project 3 items |

---

## Task 1: Skeleton — module, entry point, smoke test

**Files:**
- Create: `src/solo_roll/campaign.py`
- Modify: `pyproject.toml`
- Create: `tests/test_campaign.py`

- [ ] **Step 1: Add module skeleton**

Create `src/solo_roll/campaign.py`:

```python
"""solo-campaign: scaffold a new solo RPG campaign folder."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="solo-campaign",
                                     description="Scaffold a new solo RPG campaign folder.")
    parser.add_argument("name", help="Display name for the campaign")
    parser.add_argument("path", help="Target campaign directory (must not exist)")
    parser.add_argument("--vault", type=str, default=None,
                        help="Player Obsidian vault path")
    parser.add_argument("--skills-dir", type=str, default=None,
                        help="Override ~/.claude/skills/ (env: CLAUDE_SKILLS_DIR)")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add console_script entry**

Edit `pyproject.toml`. Find the `[project.scripts]` block and change it to:

```toml
[project.scripts]
solo-roll = "solo_roll.cli:main"
solo-campaign = "solo_roll.campaign:main"
```

- [ ] **Step 3: Reinstall to register entry point**

Run: `uv tool install --editable . --reinstall`

Expected: succeeds, then `which solo-campaign` prints a path.

- [ ] **Step 4: Smoke test**

Run: `solo-campaign --help`
Expected: argparse prints help with `name`, `path`, `--vault`, `--skills-dir`. Exit 0.

- [ ] **Step 5: Add import smoke test**

Create `tests/test_campaign.py`:

```python
import subprocess


def test_campaign_help_runs():
    result = subprocess.run(["solo-campaign", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Scaffold a new solo RPG campaign folder" in result.stdout


def test_campaign_module_imports():
    from solo_roll import campaign
    assert callable(campaign.main)
```

- [ ] **Step 6: Run full test suite**

Run: `pytest --tb=short -q`
Expected: 78 passed (76 existing + 2 new).

- [ ] **Step 7: Commit**

```bash
git add src/solo_roll/campaign.py pyproject.toml tests/test_campaign.py
git commit -m "feat: add solo-campaign skeleton entry point"
```

---

## Task 2: `_resolve_repo_root` helper

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_campaign.py`:

```python
from pathlib import Path

from solo_roll.campaign import _resolve_repo_root


def test_resolve_repo_root_returns_dir_with_pyproject_and_example_campaign():
    root = _resolve_repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "example-campaign").is_dir()
    assert (root / "skills").is_dir()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_campaign.py::test_resolve_repo_root_returns_dir_with_pyproject_and_example_campaign -v`
Expected: FAIL with `ImportError: cannot import name '_resolve_repo_root'`.

- [ ] **Step 3: Implement**

In `src/solo_roll/campaign.py`, add at the top of the file (after imports, before `main`):

```python
from pathlib import Path


def _resolve_repo_root() -> Path:
    """Return the toolkit repo root (parent of `src/`)."""
    return Path(__file__).resolve().parents[2]
```

- [ ] **Step 4: Run test, verify it passes**

Run: `pytest tests/test_campaign.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat: add _resolve_repo_root helper to campaign module"
```

---

## Task 3: `_create_campaign` — copy template + substitute placeholders

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_campaign.py`:

```python
import pytest

from solo_roll.campaign import _create_campaign


@pytest.fixture
def fake_template(tmp_path):
    """Create a minimal example-campaign template for testing."""
    template = tmp_path / "example-campaign"
    template.mkdir()
    (template / "CLAUDE.md").write_text(
        "# Solo RPG Campaign — [Campaign Name]\n\n"
        "PLAYER_VAULT_PATH: /CHANGE/ME/path/to/Obsidian/Vault/Solo Campaign\n"
    )
    (template / "dm-notes").mkdir()
    (template / "dm-notes" / "mythic-state.md").write_text("# Mythic State\nCF: 5\n")
    return template


def test_create_campaign_copies_template(tmp_path, fake_template):
    target = tmp_path / "my-campaign"
    _create_campaign("My Campaign", target, Path("/vault/solo"), fake_template)
    assert (target / "CLAUDE.md").is_file()
    assert (target / "dm-notes" / "mythic-state.md").is_file()


def test_create_campaign_substitutes_name(tmp_path, fake_template):
    target = tmp_path / "my-campaign"
    _create_campaign("Bleak Winter", target, Path("/vault/solo"), fake_template)
    text = (target / "CLAUDE.md").read_text()
    assert "Bleak Winter" in text
    assert "[Campaign Name]" not in text


def test_create_campaign_substitutes_vault_path(tmp_path, fake_template):
    target = tmp_path / "my-campaign"
    _create_campaign("Bleak Winter", target, Path("/home/me/Obsidian/Solo"), fake_template)
    text = (target / "CLAUDE.md").read_text()
    assert "/home/me/Obsidian/Solo" in text
    assert "/CHANGE/ME/path/to/Obsidian/Vault/Solo Campaign" not in text


def test_create_campaign_target_exists_raises(tmp_path, fake_template):
    target = tmp_path / "existing"
    target.mkdir()
    with pytest.raises(FileExistsError):
        _create_campaign("X", target, Path("/v"), fake_template)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_campaign.py -v -k create_campaign`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

In `src/solo_roll/campaign.py`, add at the top of imports:

```python
import shutil
```

Add this function after `_resolve_repo_root`:

```python
def _create_campaign(
    name: str,
    target: Path,
    vault_path: Path,
    template_dir: Path,
) -> None:
    """Copy template_dir to target, substituting placeholders in CLAUDE.md."""
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    shutil.copytree(template_dir, target)
    claude_md = target / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text()
        text = text.replace("[Campaign Name]", name)
        text = text.replace(
            "/CHANGE/ME/path/to/Obsidian/Vault/Solo Campaign",
            str(vault_path),
        )
        claude_md.write_text(text)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_campaign.py -v -k create_campaign`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat: add _create_campaign with template copy and placeholder substitution"
```

---

## Task 4: `_install_skills` — symlink each skill into ~/.claude/skills/

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_campaign.py`:

```python
from solo_roll.campaign import _install_skills


@pytest.fixture
def fake_skills_source(tmp_path):
    """Create a fake skills/ dir with three skill subdirs."""
    src = tmp_path / "src_skills"
    src.mkdir()
    for name in ("alpha", "beta", "gamma"):
        skill = src / name
        skill.mkdir()
        (skill / "SKILL.md").write_text(f"# {name}\n")
    return src


def test_install_skills_creates_symlinks(tmp_path, fake_skills_source):
    target = tmp_path / "skills_target"
    _install_skills(fake_skills_source, target)
    for name in ("alpha", "beta", "gamma"):
        link = target / name
        assert link.is_symlink()
        assert link.resolve() == (fake_skills_source / name).resolve()


def test_install_skills_creates_target_if_missing(tmp_path, fake_skills_source):
    target = tmp_path / "deep" / "skills"
    _install_skills(fake_skills_source, target)
    assert target.is_dir()


def test_install_skills_replaces_existing_symlink(tmp_path, fake_skills_source):
    target = tmp_path / "skills_target"
    target.mkdir()
    stale_pointee = tmp_path / "stale"
    stale_pointee.mkdir()
    (target / "alpha").symlink_to(stale_pointee)
    _install_skills(fake_skills_source, target)
    assert (target / "alpha").resolve() == (fake_skills_source / "alpha").resolve()


def test_install_skills_refuses_real_dir(tmp_path, fake_skills_source):
    target = tmp_path / "skills_target"
    target.mkdir()
    (target / "alpha").mkdir()
    with pytest.raises(IsADirectoryError):
        _install_skills(fake_skills_source, target)


def test_install_skills_skips_non_directory_entries(tmp_path, fake_skills_source):
    (fake_skills_source / "README.md").write_text("not a skill")
    target = tmp_path / "skills_target"
    _install_skills(fake_skills_source, target)
    assert not (target / "README.md").exists()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_campaign.py -v -k install_skills`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Add to `src/solo_roll/campaign.py` after `_create_campaign`:

```python
def _install_skills(skills_source: Path, skills_target: Path) -> list[Path]:
    """Symlink every skill directory under skills_source into skills_target.

    - Creates skills_target if missing.
    - Replaces existing symlinks at <target>/<name>.
    - Raises IsADirectoryError if <target>/<name> is a real directory.
    """
    skills_target.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for skill_dir in sorted(skills_source.iterdir()):
        if not skill_dir.is_dir():
            continue
        link = skills_target / skill_dir.name
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            raise IsADirectoryError(
                f"refusing to replace real directory at {link} "
                f"(only symlinks are auto-replaced)"
            )
        link.symlink_to(skill_dir.resolve())
        created.append(link)
    return created
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_campaign.py -v -k install_skills`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat: add _install_skills symlink helper"
```

---

## Task 5: `_create_vault` — mkdir vault root + 5 subdirs

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_campaign.py`:

```python
from solo_roll.campaign import _create_vault


def test_create_vault_creates_root_and_subdirs(tmp_path):
    vault = tmp_path / "obsidian" / "solo"
    _create_vault(vault)
    assert vault.is_dir()
    for sub in ("Session Log", "People", "Places", "Threads", "Lore"):
        assert (vault / sub).is_dir(), f"missing {sub}"


def test_create_vault_idempotent(tmp_path):
    vault = tmp_path / "obsidian" / "solo"
    _create_vault(vault)
    (vault / "People" / "Aland.md").write_text("existing")
    _create_vault(vault)
    assert (vault / "People" / "Aland.md").read_text() == "existing"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_campaign.py -v -k create_vault`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Add to `src/solo_roll/campaign.py` after `_install_skills`:

```python
VAULT_SUBDIRS = ("Session Log", "People", "Places", "Threads", "Lore")


def _create_vault(vault_path: Path) -> None:
    """Create vault root and 5 subdirs. Idempotent."""
    vault_path.mkdir(parents=True, exist_ok=True)
    for sub in VAULT_SUBDIRS:
        (vault_path / sub).mkdir(exist_ok=True)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_campaign.py -v -k create_vault`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat: add _create_vault helper for Obsidian vault scaffolding"
```

---

## Task 6: `_ensure_solo_roll` — check PATH, run uv tool install if missing

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_campaign.py`:

```python
from unittest.mock import patch

from solo_roll.campaign import _ensure_solo_roll


def test_ensure_solo_roll_skips_if_on_path(tmp_path):
    # If shutil.which returns truthy, function returns without running subprocess.
    with patch("solo_roll.campaign.shutil.which", return_value="/usr/bin/solo-roll"):
        with patch("solo_roll.campaign.subprocess.run") as run:
            _ensure_solo_roll(tmp_path)
            run.assert_not_called()


def test_ensure_solo_roll_runs_uv_install_if_missing(tmp_path):
    def which_side(cmd):
        return None if cmd == "solo-roll" else "/usr/bin/uv"

    with patch("solo_roll.campaign.shutil.which", side_effect=which_side):
        with patch("solo_roll.campaign.subprocess.run") as run:
            _ensure_solo_roll(tmp_path)
            run.assert_called_once()
            args = run.call_args.args[0]
            assert args[0] == "uv"
            assert "install" in args
            assert str(tmp_path) in args


def test_ensure_solo_roll_errors_if_uv_missing(tmp_path):
    with patch("solo_roll.campaign.shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc:
            _ensure_solo_roll(tmp_path)
        assert exc.value.code == 1
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_campaign.py -v -k ensure_solo_roll`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

In `src/solo_roll/campaign.py`, add to imports:

```python
import subprocess
```

Add after `_create_vault`:

```python
def _ensure_solo_roll(repo_root: Path) -> None:
    """If `solo-roll` is not on PATH, run `uv tool install --editable <repo_root>`."""
    if shutil.which("solo-roll"):
        return
    if not shutil.which("uv"):
        print(
            "error: uv not found — install from https://docs.astral.sh/uv/",
            file=sys.stderr,
        )
        sys.exit(1)
    subprocess.run(
        ["uv", "tool", "install", "--editable", str(repo_root)],
        check=True,
    )
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_campaign.py -v -k ensure_solo_roll`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat: add _ensure_solo_roll dependency check"
```

---

## Task 7: `main()` orchestration + argparse + happy path tests

**Files:**
- Modify: `src/solo_roll/campaign.py`
- Modify: `tests/test_campaign.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_campaign.py`:

```python
import os

from solo_roll.campaign import main


def test_main_happy_path(tmp_path, monkeypatch, capsys):
    """End-to-end: create campaign, install skills, create vault, print success."""
    # Prevent _ensure_solo_roll from invoking uv: pretend solo-roll is installed.
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )

    target = tmp_path / "my-campaign"
    vault = tmp_path / "obsidian" / "solo"
    skills_dir = tmp_path / "claude_skills"

    rc = main([
        "Bleak Winter",
        str(target),
        "--vault", str(vault),
        "--skills-dir", str(skills_dir),
    ])

    assert rc == 0
    assert (target / "CLAUDE.md").is_file()
    assert "Bleak Winter" in (target / "CLAUDE.md").read_text()
    assert str(vault) in (target / "CLAUDE.md").read_text()
    assert vault.is_dir()
    assert (vault / "Session Log").is_dir()
    # Real repo skills exist, so symlinks should be created
    assert any(p.is_symlink() for p in skills_dir.iterdir())

    out = capsys.readouterr().out
    assert "ready" in out
    assert str(target) in out


def test_main_target_exists_returns_1(tmp_path, capsys):
    existing = tmp_path / "existing"
    existing.mkdir()
    rc = main([
        "X", str(existing),
        "--vault", str(tmp_path / "v"),
        "--skills-dir", str(tmp_path / "s"),
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already exists" in err


def test_main_no_vault_non_tty_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc = main([
        "X", str(tmp_path / "campaign"),
        "--skills-dir", str(tmp_path / "s"),
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "vault" in err.lower()


def test_main_skills_dir_from_env(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "solo_roll.campaign.shutil.which",
        lambda cmd: "/usr/bin/solo-roll" if cmd == "solo-roll" else None,
    )
    skills_dir = tmp_path / "env_skills"
    monkeypatch.setenv("CLAUDE_SKILLS_DIR", str(skills_dir))
    rc = main([
        "X", str(tmp_path / "campaign"),
        "--vault", str(tmp_path / "v"),
    ])
    assert rc == 0
    assert skills_dir.is_dir()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_campaign.py -v -k "test_main_"`
Expected: FAIL — `main` does not yet implement the logic (the skeleton from Task 1 just parses and returns 0; tests will fail on missing files or behavior).

- [ ] **Step 3: Implement**

Add to `src/solo_roll/campaign.py` imports:

```python
import os
```

Replace the existing `main()` with this full implementation:

```python
def _prompt_vault_path() -> Path:
    if not sys.stdin.isatty():
        print("error: --vault required when not interactive", file=sys.stderr)
        sys.exit(1)
    raw = input("PLAYER_VAULT_PATH (path to Obsidian vault folder): ").strip()
    if not raw:
        print("error: vault path cannot be empty", file=sys.stderr)
        sys.exit(1)
    return Path(raw).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="solo-campaign",
        description="Scaffold a new solo RPG campaign folder.",
    )
    parser.add_argument("name", help="Display name for the campaign")
    parser.add_argument("path", help="Target campaign directory (must not exist)")
    parser.add_argument("--vault", type=str, default=None,
                        help="Player Obsidian vault path")
    parser.add_argument("--skills-dir", type=str, default=None,
                        help="Override ~/.claude/skills/ (env: CLAUDE_SKILLS_DIR)")
    args = parser.parse_args(argv)

    repo_root = _resolve_repo_root()
    template_dir = repo_root / "example-campaign"
    skills_source = repo_root / "skills"

    if not template_dir.is_dir():
        print(
            f"error: toolkit install corrupt — example-campaign not found at {template_dir}",
            file=sys.stderr,
        )
        return 1

    target = Path(args.path).expanduser()
    if target.exists():
        print(f"error: {target} already exists", file=sys.stderr)
        return 1

    skills_dir_arg = args.skills_dir or os.environ.get("CLAUDE_SKILLS_DIR")
    skills_target = (
        Path(skills_dir_arg).expanduser() if skills_dir_arg
        else Path.home() / ".claude" / "skills"
    )

    vault_path = (
        Path(args.vault).expanduser() if args.vault
        else _prompt_vault_path()
    )

    try:
        _create_campaign(args.name, target, vault_path, template_dir)
        _install_skills(skills_source, skills_target)
        _ensure_solo_roll(repo_root)
        _create_vault(vault_path)
    except (FileExistsError, IsADirectoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"ready — run `claude` in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_campaign.py -v`
Expected: all 18+ tests pass (skeleton + helpers + main).

- [ ] **Step 5: Run full test suite**

Run: `pytest --tb=short -q`
Expected: 76 existing + new tests = ~94 total, all pass.

- [ ] **Step 6: Manual smoke test**

```bash
cd /tmp
solo-campaign "Smoke Test" /tmp/smoke-test --vault /tmp/smoke-vault --skills-dir /tmp/smoke-skills
ls /tmp/smoke-test
ls /tmp/smoke-skills
ls /tmp/smoke-vault
cat /tmp/smoke-test/CLAUDE.md | head -5
rm -rf /tmp/smoke-test /tmp/smoke-vault /tmp/smoke-skills
```

Expected: campaign dir contains `CLAUDE.md` with "Smoke Test" substituted; skills dir has 3 symlinks; vault has 5 subdirs. Output ends with `ready — run `claude` in /tmp/smoke-test`.

- [ ] **Step 7: Commit**

```bash
git add src/solo_roll/campaign.py tests/test_campaign.py
git commit -m "feat: wire main() orchestration for solo-campaign"
```

---

## Task 8: README + ROADMAP updates

**Files:**
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Add `solo-campaign` section to README**

Edit `README.md`. After the `## Install the `solo-roll` CLI` section, add a new section:

```markdown
## Bootstrap a campaign with `solo-campaign`

Once `solo-roll` is installed (see above — `solo-campaign` ships in the same package), one command scaffolds a fresh campaign:

```bash
solo-campaign "Bleak Winter" ~/rpg/bleak-winter --vault ~/Obsidian/Solo
```

What it does:
- Copies `example-campaign/` to `~/rpg/bleak-winter/` and substitutes the campaign name + vault path into the new `CLAUDE.md`
- Symlinks each skill (`ironsworn`, `mythic-gme`, `solo-journaler`) into `~/.claude/skills/` — edits in your repo propagate immediately
- Verifies `solo-roll` is on PATH; runs `uv tool install --editable .` from the repo if not
- Creates `~/Obsidian/Solo/{Session Log,People,Places,Threads,Lore}` if missing

If you omit `--vault`, the script prompts for the vault path interactively. Use `--skills-dir <path>` (or the `CLAUDE_SKILLS_DIR` env var) to override the default `~/.claude/skills/` location.

The script fails fast if the target campaign directory already exists — it never overwrites.

### Windows

`solo-campaign` is Linux/macOS-first. On Windows, use the manual setup at the bottom of this README (Copy-Item commands), then edit the new `CLAUDE.md` to set `PLAYER_VAULT_PATH`.
```

- [ ] **Step 2: Update ROADMAP.md sub-project 3**

Edit `docs/ROADMAP.md`. In the Sub-project 3 section, change `- [ ]` to `- [x]` for these items:

```
- [x] Shell/fish script: `new-campaign <name> <path>`
- [x] Copies `example-campaign/` to target path
- [x] Installs skills to `~/.claude/skills/` (idempotent)
- [x] Runs `uv tool install --editable .` for `solo-roll`
- [x] Prompts for `PLAYER_VAULT_PATH` and writes to campaign `CLAUDE.md`
- [x] Creates Obsidian vault folder structure at `PLAYER_VAULT_PATH`
- [x] Prints "ready — run `claude` in `<path>`"
- [x] Works on Linux/macOS; documents Windows PowerShell equivalent in README
```

(Title changed from `new-campaign` to `solo-campaign` during design — leave the roadmap text as-is or update if you want strict consistency.)

- [ ] **Step 3: Commit**

```bash
git add README.md docs/ROADMAP.md
git commit -m "docs: add solo-campaign usage and mark sub-project 3 complete"
```

---

## Verification

After all tasks complete:

1. `pytest --tb=short -q` — all tests pass
2. Fresh smoke test from a clean tmp dir:
   ```bash
   solo-campaign "Verify" /tmp/verify --vault /tmp/verify-vault --skills-dir /tmp/verify-skills
   test -f /tmp/verify/CLAUDE.md && echo "campaign OK"
   test -d /tmp/verify-vault/People && echo "vault OK"
   test -L /tmp/verify-skills/ironsworn && echo "skills OK"
   rm -rf /tmp/verify /tmp/verify-vault /tmp/verify-skills
   ```
3. README documents the new command at the install section
4. ROADMAP shows Sub-project 3 fully checked

---

## Self-Review Notes

**Spec coverage:**
- ✅ entry point + argparse synopsis (Task 1, 7)
- ✅ `_resolve_repo_root` (Task 2)
- ✅ `_create_campaign` with copy + substitute (Task 3)
- ✅ `_install_skills` symlink mode (Task 4)
- ✅ `_create_vault` 5 subdirs (Task 5)
- ✅ `_ensure_solo_roll` with `uv` fallback (Task 6)
- ✅ `_prompt_vault_path` tty check (Task 7)
- ✅ Error handling table covered: target exists, non-tty + no vault, real-dir refusal, uv missing
- ✅ Tests for every function + integration happy path
- ✅ README + ROADMAP updates (Task 8)

**Out of scope per spec:** Windows PowerShell code, PyPI distribution, custom skill selection, re-running on existing campaign. None of those have tasks. Correct.

**Type/name consistency:** All function signatures match between definition and usage. `VAULT_SUBDIRS` constant introduced once in Task 5, used only in `_create_vault`.
