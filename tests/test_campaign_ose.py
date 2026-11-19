import json
import shutil
import subprocess
import sys

import pytest

from solo_roll.campaign import main


@pytest.fixture(autouse=True)
def no_install(monkeypatch):
    monkeypatch.setattr("solo_roll.campaign._ensure_solo_roll", lambda _: None)


def scaffold(tmp_path, name="Barrowmaze", module="Barrowmaze Complete", extra=()):
    target = tmp_path / "camp"
    code = main(["ose", name, str(target), "--module", module, *extra])
    return code, target


class TestScaffold:
    def test_succeeds(self, tmp_path):
        code, target = scaffold(tmp_path)
        assert code == 0
        assert (target / "CLAUDE.md").is_file()

    def test_refuses_existing_path(self, tmp_path):
        target = tmp_path / "camp"
        target.mkdir()
        assert main(["ose", "X", str(target), "--module", "M"]) == 1

    def test_copies_the_engine(self, tmp_path):
        _, target = scaffold(tmp_path)
        for path in (
            ".claude/agents/referee.md",
            ".claude/hooks/guard-dungeon.py",
            ".claude/hooks/inject-state.sh",
            ".claude/hooks/journal.sh",
            ".claude/output-styles/referee.md",
            ".claude/statusline.sh",
            ".claude/skills/journaler/SKILL.md",
        ):
            assert (target / path).is_file(), path

    def test_copies_the_ose_rules_folder(self, tmp_path, ose_template):
        if not (ose_template / "rules").is_dir():
            pytest.skip("templates/ose/rules/ is gitignored and absent here")
        _, target = scaffold(tmp_path)
        assert (target / "rules/dungeon-turn.md").is_file()
        assert (target / "rules/encounters.md").is_file()

    def test_copies_the_ose_tables(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert (target / "data/tables/ose/reaction.json").is_file()

    def test_leaves_the_dungeon_empty(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert (target / "dungeon").is_dir()
        assert list((target / "dungeon").glob("*.md")) == []

    def test_substitutes_the_module_name(self, tmp_path):
        _, target = scaffold(tmp_path)
        module = (target / "module.md").read_text()
        assert "Barrowmaze Complete" in module
        assert "[MODULE NAME]" not in module

    def test_substitutes_the_campaign_name(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert "Barrowmaze" in (target / "README.md").read_text()
        assert "[CAMPAIGN NAME]" not in (target / "README.md").read_text()

    def test_hooks_are_executable(self, tmp_path):
        _, target = scaffold(tmp_path)
        hooks = list((target / ".claude/hooks").iterdir())
        assert hooks
        for hook in hooks:
            assert hook.stat().st_mode & 0o111, hook


class TestSettings:
    def test_written_with_absolute_paths(self, tmp_path):
        _, target = scaffold(tmp_path)
        settings = json.loads((target / ".claude/settings.json").read_text())
        assert settings["outputStyle"] == "referee"
        assert settings["env"]["SOLO_ROLL_DATA"] == str(target / "data")
        assert str(target) in settings["statusLine"]["command"]

    def test_no_deny_rule_guards_the_dungeon(self, tmp_path):
        """A deny rule would block the referee subagent too, so guard-dungeon.py
        is the only guard. It reads agent_type to tell the referee apart."""
        _, target = scaffold(tmp_path)
        settings = json.loads((target / ".claude/settings.json").read_text())
        assert settings["permissions"]["deny"] == []

    def test_permission_paths_are_relative(self, tmp_path):
        """Claude Code does not match absolute paths in permission rules."""
        _, target = scaffold(tmp_path)
        settings = json.loads((target / ".claude/settings.json").read_text())
        paths = [r for r in settings["permissions"]["allow"] if not r.startswith("Bash(")]
        assert paths
        for rule in paths:
            assert "(./" in rule, rule
            assert str(target) not in rule, rule

    def test_registers_all_three_hooks(self, tmp_path):
        _, target = scaffold(tmp_path)
        hooks = json.loads((target / ".claude/settings.json").read_text())["hooks"]
        assert set(hooks) == {"UserPromptSubmit", "PreToolUse", "Stop"}
        assert hooks["PreToolUse"][0]["matcher"] == "Read|Glob|Grep|Bash"
        assert "guard-dungeon.py" in hooks["PreToolUse"][0]["hooks"][0]["command"]

    def test_state_starts_at_turn_zero(self, tmp_path):
        _, target = scaffold(tmp_path)
        clock = json.loads((target / "state/clock.json").read_text())
        assert clock["turn"] == 0
        assert clock["light"] == []

    def test_starting_level_is_recorded(self, tmp_path):
        _, target = scaffold(tmp_path, extra=("--starting-level", "2"))
        assert json.loads((target / "state/clock.json").read_text())["level"] == 2


class TestFogMap:
    def test_ships_the_viewer_and_the_installer(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert (target / "map/index.html").is_file()
        assert (target / "tools/install_map.py").is_file()

    def test_viewer_polls_the_reveal_file_in_state(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert "../state/revealed.js" in (target / "map/index.html").read_text()

    def test_installer_places_viewer_and_referee_files(self, tmp_path):
        _, target = scaffold(tmp_path)
        stage = tmp_path / "stage"
        (stage / "viewer/masks").mkdir(parents=True)
        (stage / "viewer/areas.json").write_text('{"areas": []}')
        (stage / "viewer/masks/1.png").write_bytes(b"png")
        (stage / "referee/crops").mkdir(parents=True)
        (stage / "referee/exits.json").write_text("{}")
        (stage / "referee/crops/1.png").write_bytes(b"png")

        proc = subprocess.run([sys.executable, str(target / "tools/install_map.py"),
                               str(stage)], capture_output=True, text=True)

        assert proc.returncode == 0, proc.stderr
        assert (target / "map/masks/1.png").is_file()
        assert (target / "map/index.html").is_file()
        assert (target / "dungeon/map/exits.json").is_file()
        assert (target / "dungeon/map/crops/1.png").is_file()
        assert (target / "state/revealed.js").read_text() == "window.REVEALED = [];\n"


class TestOseTemplateFiles:
    """Checks that the template ships `gitignore.template` instead of a live
    `.gitignore`, and ships its state and vault files. Audit finding 1."""

    def test_template_folder_has_no_live_gitignore(self, ose_template):
        assert not (ose_template / ".gitignore").exists()
        assert (ose_template / "gitignore.template").is_file()

    def test_campaign_gets_the_ignore_rules(self, tmp_path):
        _, target = scaffold(tmp_path)
        ignore = (target / ".gitignore").read_text().splitlines()
        assert {"dungeon/", "rules/", "state/", "playervault/"} <= set(ignore)
        assert not (target / "gitignore.template").exists()

    def test_template_ships_state_and_vault(self, ose_template):
        for path in ("state/clock.json", "state/party.json",
                     "playervault/Character.md", "playervault/Map.md"):
            assert (ose_template / path).is_file(), path

    def test_character_sheet_names_no_module(self, tmp_path):
        _, target = scaffold(tmp_path, name="Barrowmaze")
        text = (target / "playervault/Character.md").read_text()
        assert "campaign: Barrowmaze" in text
        assert "Serpent" not in text

    def test_missing_template_state_fails_before_creating_target(
            self, tmp_path, monkeypatch):
        fake = tmp_path / "repo"
        (fake / "templates/ose").mkdir(parents=True)
        monkeypatch.setattr("solo_roll.campaign._resolve_repo_root", lambda: fake)
        target = tmp_path / "camp"
        assert main(["ose", "X", str(target)]) == 1
        assert not target.exists()


class TestRulesFolder:
    """`solo-campaign ose` copies rules/ when the template has it and otherwise
    creates an empty rules/ with a warning, because rules/ is gitignored."""

    def test_without_template_rules_creates_an_empty_folder_and_warns(
            self, tmp_path, monkeypatch, ose_template, capsys):
        fake = tmp_path / "repo"
        shutil.copytree(ose_template, fake / "templates/ose",
                        ignore=shutil.ignore_patterns("rules"))
        monkeypatch.setattr("solo_roll.campaign._resolve_repo_root", lambda: fake)
        target = tmp_path / "camp"
        assert main(["ose", "X", str(target), "--module", "M"]) == 0
        assert list((target / "rules").iterdir()) == []
        assert "rules" in capsys.readouterr().err

    def test_with_template_rules_copies_them(
            self, tmp_path, monkeypatch, ose_template, capsys):
        fake = tmp_path / "repo"
        shutil.copytree(ose_template, fake / "templates/ose",
                        ignore=shutil.ignore_patterns("rules"))
        (fake / "templates/ose/rules").mkdir()
        (fake / "templates/ose/rules/a.md").write_text("a")
        monkeypatch.setattr("solo_roll.campaign._resolve_repo_root", lambda: fake)
        target = tmp_path / "camp"
        assert main(["ose", "X", str(target), "--module", "M"]) == 0
        assert (target / "rules/a.md").read_text() == "a"
        assert "warning" not in capsys.readouterr().err


class TestRelativeTarget:
    """`solo-campaign ose` with a relative path writes absolute hook and data
    paths into settings.json. Audit finding 2."""

    def test_settings_use_absolute_paths(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert main(["ose", "X", "camp", "--module", "M"]) == 0
        settings = json.loads((tmp_path / "camp/.claude/settings.json").read_text())
        root = str((tmp_path / "camp").resolve())
        assert settings["env"]["SOLO_ROLL_DATA"] == root + "/data"
        for entries in settings["hooks"].values():
            assert root in entries[0]["hooks"][0]["command"]
        assert root in settings["statusLine"]["command"]


class TestJournalHook:
    """Checks that journal.sh writes each turn line once, into the newest
    session file. Audit finding 8."""

    def run_hook(self, target):
        subprocess.run(["bash", str(target / ".claude/hooks/journal.sh")], check=True)

    def test_does_not_repeat_a_turn_line_after_narrative(self, tmp_path):
        _, target = scaffold(tmp_path)
        log = target / "playervault/Session Log/Session 001.md"
        self.run_hook(target)
        with log.open("a") as fh:
            fh.write("\nThe party rested.\n")
        self.run_hook(target)
        assert log.read_text().count("- Turn 0:") == 1

    def test_writes_to_the_newest_session_file(self, tmp_path):
        _, target = scaffold(tmp_path)
        folder = target / "playervault/Session Log"
        (folder / "Session 001.md").write_text("# Session 001\n")
        (folder / "Session 002.md").write_text("# Session 002\n\n## Turn log\n\n")
        self.run_hook(target)
        assert "- Turn 0:" in (folder / "Session 002.md").read_text()
        assert "- Turn" not in (folder / "Session 001.md").read_text()

    def test_session_start_procedure_creates_the_next_file(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert "create the next" in (target / "CLAUDE.md").read_text()
