import json

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
            ".claude/hooks/guard-dungeon.sh",
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
        for hook in (target / ".claude/hooks").glob("*.sh"):
            assert hook.stat().st_mode & 0o111, hook


class TestSettings:
    def test_written_with_absolute_paths(self, tmp_path):
        _, target = scaffold(tmp_path)
        settings = json.loads((target / ".claude/settings.json").read_text())
        assert settings["outputStyle"] == "referee"
        assert settings["env"]["SOLO_ROLL_DATA"] == str(target / "data")
        assert str(target) in settings["statusLine"]["command"]

    def test_denies_reading_the_dungeon(self, tmp_path):
        _, target = scaffold(tmp_path)
        settings = json.loads((target / ".claude/settings.json").read_text())
        assert f"Read({target}/dungeon/**)" in settings["permissions"]["deny"]

    def test_registers_all_three_hooks(self, tmp_path):
        _, target = scaffold(tmp_path)
        hooks = json.loads((target / ".claude/settings.json").read_text())["hooks"]
        assert set(hooks) == {"UserPromptSubmit", "PreToolUse", "Stop"}
        assert hooks["PreToolUse"][0]["matcher"] == "Read"

    def test_state_starts_at_turn_zero(self, tmp_path):
        _, target = scaffold(tmp_path)
        clock = json.loads((target / "state/clock.json").read_text())
        assert clock["turn"] == 0
        assert clock["light"] == []

    def test_starting_level_is_recorded(self, tmp_path):
        _, target = scaffold(tmp_path, extra=("--starting-level", "2"))
        assert json.loads((target / "state/clock.json").read_text())["level"] == 2
