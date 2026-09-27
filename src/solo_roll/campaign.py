"""solo-campaign: scaffold a new solo RPG campaign folder."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from solo_roll.voices import (
    VoiceError,
    inject_voice_block,
    list_voices,
    load_voice,
)


class CampaignError(Exception):
    """Internal error type for clean exit-1 paths from helpers."""


def _resolve_repo_root() -> Path:
    """Return the toolkit repo root (parent of `src/`)."""
    return Path(__file__).resolve().parents[2]


def _list_available_skills(skills_source: Path) -> list[str]:
    """Return sorted names of skill directories present under skills_source."""
    return sorted(p.name for p in skills_source.iterdir() if p.is_dir())


def _format_active_skills(selected: list[str]) -> str:
    """Render the [Active Skills] block for the campaign CLAUDE.md."""
    if not selected:
        return "_(no skills installed — campaign runs unassisted)_"
    descriptions = {
        "ironsworn": "system rules, moves, oracles",
        "mythic-gme": "chaos factor, fate checks, scene tests, event focus",
        "solo-journaler": "session journaling, vault note management",
    }
    lines = []
    for name in selected:
        desc = descriptions.get(name)
        if desc:
            lines.append(f"- `{name}` — {desc}")
        else:
            lines.append(f"- `{name}`")
    return "\n".join(lines)


def _create_campaign(
    name: str,
    target: Path,
    template_dir: Path,
    selected_skills: list[str],
) -> None:
    """Copy template_dir to target, substituting placeholders in CLAUDE.md."""
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    shutil.copytree(template_dir, target)
    claude_md = target / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text()
        text = text.replace("[Campaign Name]", name)
        text = text.replace("[Active Skills]", _format_active_skills(selected_skills))
        claude_md.write_text(text)


def _install_skills(
    skills_source: Path,
    skills_target: Path,
    selected: list[str] | None = None,
) -> list[Path]:
    """Symlink skill directories under skills_source into skills_target.

    If `selected` is None, install all skill subdirs of skills_source.
    Otherwise install only those names; raises CampaignError on unknown name.
    Creates skills_target if missing. Replaces existing symlinks at <target>/<name>.
    Raises IsADirectoryError if <target>/<name> is a real directory.
    """
    available = _list_available_skills(skills_source)
    if selected is None:
        chosen = available
    else:
        unknown = [name for name in selected if name not in available]
        if unknown:
            raise CampaignError(
                f"unknown skill(s): {', '.join(unknown)}. "
                f"available: {', '.join(available)}"
            )
        chosen = list(selected)

    skills_target.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for name in chosen:
        skill_dir = skills_source / name
        link = skills_target / name
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


def _create_mythic_state(campaign_path: Path) -> None:
    """Bootstrap mythic-state.md at campaign root with CF 5 and empty lists."""
    (campaign_path / "mythic-state.md").write_text(
        "# Mythic State\n\n"
        "## Chaos Factor\n**Current: 5**\n\n"
        "## Current scene\n*(Set at start of each scene: \"Expected setup = [one sentence]\")*\n\n"
        "## Last scene outcome\n*(in control / out of control / mixed — used to adjust CF at scene end)*\n\n"
        "## Threads List\n"
        "*(Active story threads — problems, quests, unresolved tensions. Numbered for oracle rolls.)*\n\n"
        "1. \n\n"
        "## Characters List\n"
        "*(NPCs in play, including ones the player hasn't met. Numbered for oracle rolls.)*\n\n"
        "1. \n\n"
        "## CF History\n"
        "*(One line per session: date + CF start → CF end + reason)*\n"
    )


def _write_campaign_settings(campaign_path: Path, installed_names: list[str]) -> None:
    """Write .claude/settings.json with a statusLine if ironsworn is installed."""
    if "ironsworn" not in installed_names:
        return
    script = campaign_path.resolve() / ".claude" / "skills" / "ironsworn" / "statusline.sh"
    settings = {
        "statusLine": {
            "type": "command",
            "command": f'bash "{script}"',
        }
    }
    settings_path = campaign_path / ".claude" / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


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


def _parse_skills_arg(raw: str | None, available: list[str]) -> list[str] | None:
    """Translate --skills CLI arg into a selection list.

    None  → install all (default)
    "none" → install nothing
    "a,b" → install only those names (validated against available)
    """
    if raw is None:
        return None
    if raw.strip().lower() == "none":
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    unknown = [p for p in parts if p not in available]
    if unknown:
        raise CampaignError(
            f"unknown skill(s): {', '.join(unknown)}. "
            f"available: {', '.join(available)}"
        )
    return parts


def _voice_first_note_line(body: str) -> str:
    """Extract the first non-blank sentence after the '## Voice notes' heading."""
    m = re.search(r"^## Voice notes\s*\n+(.*?)(?:\n##|\Z)",
                  body, re.DOTALL | re.MULTILINE)
    if not m:
        return "(no voice notes)"
    para = m.group(1).strip().split("\n\n", 1)[0].strip()
    first = para.split(". ", 1)[0].rstrip(".")
    return (first[:80] + "...") if len(first) > 80 else first


def _voice_list(voices_dir: Path) -> int:
    names = list_voices(voices_dir)
    if not names:
        print("(no voices available)")
        return 0
    for name in names:
        try:
            display, body = load_voice(name, voices_dir)
            desc = _voice_first_note_line(body)
        except Exception:
            display, desc = name, "(invalid voice file)"
        print(f"  {name:20s} — {display}: {desc}")
    return 0


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


def _scaffold_command(args) -> int:
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

    skills_target = target / ".claude" / "skills"

    try:
        available = _list_available_skills(skills_source)
        selected = _parse_skills_arg(args.skills, available)
        installed_names = selected if selected is not None else available
        _create_campaign(args.name, target, template_dir, installed_names)
        voices_source = repo_root / "data" / "voices"
        voice_choice = args.voice if args.voice is not None else "default"
        if voice_choice.lower() != "none":
            warning = _inject_voice_into_campaign(target, voice_choice, voices_source)
            if warning:
                print(f"warning: {warning}", file=sys.stderr)
        _install_skills(skills_source, skills_target, selected)
        _write_campaign_settings(target, installed_names)
        _ensure_solo_roll(repo_root)
        _create_vault(target / "playervault")
        if "mythic-gme" in installed_names:
            _create_mythic_state(target)
    except (CampaignError, VoiceError, FileExistsError, IsADirectoryError,
            OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"ready — run `claude` in {target}")
    return 0


OSE_HOOKS = (
    ("UserPromptSubmit", None, "bash", "inject-state.sh"),
    ("PreToolUse", "Read|Glob|Grep|Bash", "python3", "guard-dungeon.py"),
    ("Stop", None, "bash", "journal.sh"),
)


def _ose_settings(target: Path) -> dict:
    """Settings for an OSE campaign: referee voice and the three hooks.

    guard-dungeon.py, not a permissions deny rule, is what hides the key. A deny
    rule would also block the referee subagent, and absolute paths in permission
    rules do not match anything."""
    hooks: dict[str, list[dict]] = {}
    for event, matcher, runner, script in OSE_HOOKS:
        entry: dict = {"hooks": [{
            "type": "command",
            "command": f'{runner} "{target / ".claude/hooks" / script}"',
        }]}
        if matcher:
            entry["matcher"] = matcher
        hooks.setdefault(event, []).append(entry)

    return {
        "outputStyle": "referee",
        "env": {"SOLO_ROLL_DATA": str(target / "data")},
        "statusLine": {
            "type": "command",
            "command": f'bash "{target / ".claude/statusline.sh"}"',
        },
        "permissions": {
            # Paths must be relative. Claude Code does not match absolute
            # paths in permission rules, and Edit rules cover Write too.
            "allow": [
                "Bash(solo-roll:*)",
                "Read(./rules/**)",
                "Read(./state/**)",
                "Read(./playervault/**)",
                "Read(./module.md)",
                "Edit(./state/**)",
                "Edit(./playervault/**)",
            ],
            "deny": [],
        },
        "hooks": hooks,
    }


def _ose_command(args) -> int:
    repo_root = _resolve_repo_root()
    template_dir = repo_root / "templates" / "ose"
    if not template_dir.is_dir():
        print(f"error: toolkit install corrupt — {template_dir} not found",
              file=sys.stderr)
        return 1

    target = Path(args.path).expanduser()
    if target.exists():
        print(f"error: {target} already exists", file=sys.stderr)
        return 1

    try:
        shutil.copytree(template_dir, target)
        for name in ("CLAUDE.md", "README.md", "module.md"):
            path = target / name
            if path.is_file():
                text = path.read_text()
                text = text.replace("[CAMPAIGN NAME]", args.name)
                text = text.replace("[MODULE NAME]", args.module)
                path.write_text(text)

        for hook in (target / ".claude" / "hooks").glob("*.sh"):
            hook.chmod(0o755)
        statusline = target / ".claude" / "statusline.sh"
        if statusline.is_file():
            statusline.chmod(0o755)

        clock = target / "state" / "clock.json"
        state = json.loads(clock.read_text())
        state["level"] = args.starting_level
        clock.write_text(json.dumps(state, indent=2) + "\n")

        settings = target / ".claude" / "settings.json"
        settings.write_text(json.dumps(_ose_settings(target), indent=2) + "\n")
        _ensure_solo_roll(repo_root)
    except (CampaignError, FileExistsError, OSError,
            subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"scaffolded {target}")
    print("next: convert the module into dungeon/ against "
          "docs/dungeon-schema.md, then fill in module.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="solo-campaign",
        description="Scaffold a new solo RPG campaign folder.",
    )
    subparsers = parser.add_subparsers(dest="command")

    scaffold = subparsers.add_parser("scaffold", help="Create a new campaign")
    scaffold.add_argument("name", help="Display name for the campaign")
    scaffold.add_argument("path", help="Target campaign directory (must not exist)")
    scaffold.add_argument(
        "--skills", type=str, default=None, dest="skills",
        help="Comma-separated skill names to install "
             "(default: all). Use 'none' to install no skills.",
    )
    scaffold.add_argument(
        "--voice", type=str, default=None, dest="voice",
        help="Narrative voice to inject into campaign CLAUDE.md "
             "(default: 'default'). Use 'none' to skip injection.",
    )

    ose = subparsers.add_parser(
        "ose", help="Create an OSE dungeon-crawl campaign (referee harness, "
                    "OSE rules and tables, empty dungeon/)")
    ose.add_argument("name", help="Display name for the campaign")
    ose.add_argument("path", help="Target campaign directory (must not exist)")
    ose.add_argument("--module", default="[MODULE NAME]",
                     help="Published module this campaign runs")
    ose.add_argument("--starting-level", type=int, default=1,
                     help="Dungeon level the party starts on (default 1)")
    ose.set_defaults(func=_ose_command)

    voice_cmd = subparsers.add_parser("voice", help="Voice management")
    voice_subs = voice_cmd.add_subparsers(dest="voice_action")
    voice_subs.add_parser("list", help="List available voices")
    voice_apply = voice_subs.add_parser("apply",
        help="Re-inject or swap voice block in an existing campaign")
    voice_apply.add_argument("campaign_path", help="Existing campaign directory")
    voice_apply.add_argument("voice_name", help="Voice to inject")

    raw = list(sys.argv[1:] if argv is None else argv)
    known_subs = {"scaffold", "voice", "ose"}
    if raw and raw[0] not in known_subs and not raw[0].startswith("-"):
        raw = ["scaffold"] + raw
    args = parser.parse_args(raw)

    if args.command == "voice":
        return _voice_command(args)
    if args.command == "scaffold":
        return _scaffold_command(args)
    if args.command == "ose":
        return _ose_command(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
