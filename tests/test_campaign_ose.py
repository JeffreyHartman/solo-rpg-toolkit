import json
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

    def test_copies_the_ose_system_layer(self, tmp_path):
        _, target = scaffold(tmp_path)
        assert (target / "rules/dungeon-turn.md").is_file()
        assert (target / "rules/encounters.md").is_file()
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

