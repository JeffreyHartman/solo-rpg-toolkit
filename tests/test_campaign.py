import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from solo_roll.campaign import (
    _create_campaign,
    _create_vault,
    _ensure_solo_roll,
    _install_skills,
    _resolve_repo_root,
)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


def test_campaign_help_runs():
    result = subprocess.run(["solo-campaign", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Scaffold a new solo RPG campaign folder" in result.stdout


def test_campaign_module_imports():
    from solo_roll import campaign
    assert callable(campaign.main)


# ---------------------------------------------------------------------------
# Task 2: _resolve_repo_root
# ---------------------------------------------------------------------------


def test_resolve_repo_root_returns_dir_with_pyproject_and_example_campaign():
    root = _resolve_repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "example-campaign").is_dir()
    assert (root / "skills").is_dir()


# ---------------------------------------------------------------------------
# Task 3: _create_campaign
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_template(tmp_path):
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


# ---------------------------------------------------------------------------
# Task 4: _install_skills
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_skills_source(tmp_path):
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


# ---------------------------------------------------------------------------
# Task 5: _create_vault
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Task 6: _ensure_solo_roll
# ---------------------------------------------------------------------------


def test_ensure_solo_roll_skips_if_on_path(tmp_path):
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
    from solo_roll.campaign import CampaignError
    with patch("solo_roll.campaign.shutil.which", return_value=None):
        with pytest.raises(CampaignError):
            _ensure_solo_roll(tmp_path)


# ---------------------------------------------------------------------------
# Task 7: main() integration tests
# ---------------------------------------------------------------------------

import os

from solo_roll.campaign import main


def test_main_happy_path(tmp_path, monkeypatch, capsys):
    """End-to-end: create campaign, install skills, create vault, print success."""
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
