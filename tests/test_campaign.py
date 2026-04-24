import subprocess

from pathlib import Path


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

from solo_roll.campaign import _resolve_repo_root


def test_resolve_repo_root_returns_dir_with_pyproject_and_example_campaign():
    root = _resolve_repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "example-campaign").is_dir()
    assert (root / "skills").is_dir()
