"""solo-campaign: scaffold a new solo RPG campaign folder."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


class CampaignError(Exception):
    """Internal error type for clean exit-1 paths from helpers."""


def _resolve_repo_root() -> Path:
    """Return the toolkit repo root (parent of `src/`)."""
    return Path(__file__).resolve().parents[2]


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


def _install_skills(skills_source: Path, skills_target: Path) -> list[Path]:
    """Symlink every skill directory under skills_source into skills_target.

    Creates skills_target if missing. Replaces existing symlinks at <target>/<name>.
    Raises IsADirectoryError if <target>/<name> is a real directory.
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


VAULT_SUBDIRS = ("Session Log", "People", "Places", "Threads", "Lore")


def _create_vault(vault_path: Path) -> None:
    """Create vault root and 5 subdirs. Idempotent."""
    vault_path.mkdir(parents=True, exist_ok=True)
    for sub in VAULT_SUBDIRS:
        (vault_path / sub).mkdir(exist_ok=True)


def _ensure_solo_roll(repo_root: Path) -> None:
    """If `solo-roll` is not on PATH, run `uv tool install --editable <repo_root>`."""
    if shutil.which("solo-roll"):
        return
    if not shutil.which("uv"):
        raise CampaignError("uv not found — install from https://docs.astral.sh/uv/")
    subprocess.run(
        ["uv", "tool", "install", "--editable", str(repo_root)],
        check=True,
    )


def _prompt_vault_path() -> Path:
    if not sys.stdin.isatty():
        raise CampaignError("--vault required when not interactive")
    raw = input("PLAYER_VAULT_PATH (path to Obsidian vault folder): ").strip()
    if not raw:
        raise CampaignError("vault path cannot be empty")
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

    try:
        vault_path = (
            Path(args.vault).expanduser() if args.vault
            else _prompt_vault_path()
        )
        _create_campaign(args.name, target, vault_path, template_dir)
        _install_skills(skills_source, skills_target)
        _ensure_solo_roll(repo_root)
        _create_vault(vault_path)
    except (CampaignError, FileExistsError, IsADirectoryError,
            OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"ready — run `claude` in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
