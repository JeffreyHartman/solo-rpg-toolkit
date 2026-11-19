"""Tests for templates/ose/.claude/hooks/guard-dungeon.py: which tool calls it
denies. The hook is the only thing hiding the dungeon key, because a settings
deny rule would block the referee subagent as well."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "templates/ose/.claude/hooks/guard-dungeon.py"
KEY = "/home/x/camp/dungeon/level-1/01-entrance-hall.md"


def run(payload) -> str:
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, check=True)
    return proc.stdout


def denied(payload) -> bool:
    out = run(payload)
    if not out.strip():
        return False
    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    return decision == "deny"


class TestMainSession:
    @pytest.mark.parametrize("tool,key", [
        ("Read", "file_path"), ("Glob", "pattern"), ("Grep", "path"),
    ])
    def test_denies_every_read_shaped_tool(self, tool, key):
        assert denied({"tool_name": tool, "tool_input": {key: KEY}})

    def test_denies_reading_through_bash(self):
        assert denied({"tool_name": "Bash",
                       "tool_input": {"command": f"cat {KEY}"}})

    @pytest.mark.parametrize("path", [
        "/home/x/camp/dungeon/monsters/goblin.md",
        "/home/x/camp/dungeon/index.json",
        "/home/x/camp/dungeon/00-running-the-tomb.md",
        "/home/x/camp/dungeon/map/exits.json",
        "/home/x/camp/dungeon/map/crops/7.png",
        "/home/x/camp/map/map.png",
        "/home/x/camp/map/masks/7.png",
        "/home/x/camp/map/patches/s1.png",
        "/home/x/camp/map/areas.json",
    ])
    def test_denies_the_other_guarded_paths(self, path):
        assert denied({"tool_name": "Read", "tool_input": {"file_path": path}})

    @pytest.mark.parametrize("path", [
        "/home/x/camp/rules/combat.md",
        "/home/x/camp/state/clock.json",
        "/home/x/camp/playervault/Character.md",
        "/home/x/camp/module.md",
        "/home/x/camp/state/revealed.js",
        "/home/x/camp/map/index.html",
        "/home/x/camp/playervault/Map.md",
    ])
    def test_allows_everything_else(self, path):
        assert not denied({"tool_name": "Read", "tool_input": {"file_path": path}})


class TestRefereeSubagent:
    def test_allows_the_referee_to_read_the_key(self):
        assert not denied({"agent_type": "referee", "tool_name": "Read",
                           "tool_input": {"file_path": KEY}})

    def test_denies_any_other_subagent(self):
        assert denied({"agent_type": "general-purpose", "tool_name": "Read",
                       "tool_input": {"file_path": KEY}})


class TestMalformedInput:
    def test_allows_when_the_payload_is_not_json(self):
        proc = subprocess.run([sys.executable, str(HOOK)], input="not json",
                              capture_output=True, text=True, check=True)
        assert proc.stdout.strip() == ""

    def test_allows_when_tool_input_is_missing(self):
        assert not denied({"tool_name": "Read"})


@pytest.fixture
def camp(tmp_path):
    """A campaign folder with its own copy of the hook, so the hook's root is a
    real directory and relative paths mean something."""
    root = tmp_path / "camp"
    (root / ".claude/hooks").mkdir(parents=True)
    hook = root / ".claude/hooks/guard-dungeon.py"
    hook.write_bytes(HOOK.read_bytes())
    for sub in ("dungeon/level-1", "map", "rules", "playervault", "state"):
        (root / sub).mkdir(parents=True)
    (root / "map/index.html").write_text("<html>")
    return root


def camp_denied(camp, tool, tool_input, cwd=None, agent_type=None):
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd or camp)}
    if agent_type:
        payload["agent_type"] = agent_type
    proc = subprocess.run([sys.executable, str(camp / ".claude/hooks/guard-dungeon.py")],
                          input=json.dumps(payload), capture_output=True, text=True,
                          check=True)
    return bool(proc.stdout.strip()) and \
        json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestAuditBypasses:
    """Tool calls that reach the dungeon key without naming a guarded path:
    relative paths, globs, recursive searches and `cd`. Audit finding 3."""

    def test_grep_without_a_path_searches_the_campaign_root(self, camp):
        assert camp_denied(camp, "Grep", {"pattern": "secret door"})

    def test_grep_path_dungeon(self, camp):
        assert camp_denied(camp, "Grep", {"pattern": "secret", "path": "dungeon"})

    def test_grep_path_root_dot(self, camp):
        assert camp_denied(camp, "Grep", {"pattern": "secret", "path": "."})

    def test_bash_grep_recursive_from_root(self, camp):
        assert camp_denied(camp, "Bash", {"command": "grep -rn secret ."})

    def test_bash_rg_with_no_path(self, camp):
        assert camp_denied(camp, "Bash", {"command": "rg secret"})

    def test_bash_cd_into_dungeon_then_cat(self, camp):
        assert camp_denied(camp, "Bash",
                           {"command": "cd dungeon && cat level-1/07-x.md"})

    def test_bash_find_from_root(self, camp):
        assert camp_denied(camp, "Bash", {"command": "find . -name '*.md'"})

    def test_bash_glob_expands_into_dungeon(self, camp):
        assert camp_denied(camp, "Bash", {"command": "cat d*/level-1/07-x.md"})

    def test_bash_ls_dungeon(self, camp):
        assert camp_denied(camp, "Bash", {"command": "ls ./dungeon"})

    @pytest.mark.parametrize("command", [
        "tar cf - . | tar tf -",
        "zip -r out.zip .",
        "cp -r . /tmp/copy",
        "cp -r dungeon /tmp/copy",
        "rsync -a . /tmp/copy",
        "find . -exec cat {} +",
    ], ids=["tar", "zip", "cp-r", "cp-r-dungeon", "rsync", "find-exec"])
    def test_bash_archive_or_copy_of_the_tree(self, camp, command):
        assert camp_denied(camp, "Bash", {"command": command})

    def test_bash_tar_of_an_allowed_folder_is_allowed(self, camp):
        assert not camp_denied(camp, "Bash", {"command": "tar cf /tmp/r.tar rules"})

    def test_bash_python_reading_the_key(self, camp):
        assert camp_denied(camp, "Bash", {"command": "python3 -c \"print(open('dungeon/index.json').read())\""})

    def test_glob_recursive_markdown(self, camp):
        assert camp_denied(camp, "Glob", {"pattern": "**/*.md"})

    def test_glob_names_dungeon(self, camp):
        assert camp_denied(camp, "Glob", {"pattern": "dungeon/**"})

    def test_glob_with_brace_alternatives(self, camp):
        assert camp_denied(camp, "Glob", {"pattern": "{rules,dungeon}/**/*.md"})

    def test_relative_read_resolves_against_cwd(self, camp):
        assert camp_denied(camp, "Read", {"file_path": "level-1/01-x.md"},
                           cwd=camp / "dungeon")

    def test_read_through_dotdot(self, camp):
        assert camp_denied(camp, "Read",
                           {"file_path": str(camp / "rules/../dungeon/level-1/a.md")})

    def test_read_through_symlink(self, camp):
        (camp / "state/link").symlink_to(camp / "dungeon")
        assert camp_denied(camp, "Read", {"file_path": "state/link/level-1/a.md"})

    def test_map_viewer_assets_other_than_index_are_denied(self, camp):
        assert camp_denied(camp, "Read", {"file_path": "map/areas.json"})


class TestAuditStillAllows:
    @pytest.mark.parametrize("tool,tool_input", [
        ("Grep", {"pattern": "ghoul", "path": "rules"}),
        ("Grep", {"pattern": "ghoul", "path": "playervault"}),
        ("Glob", {"pattern": "rules/*.md"}),
        ("Glob", {"pattern": "*.md"}),
        ("Read", {"file_path": "map/index.html"}),
        ("Read", {"file_path": "module.md"}),
        ("Bash", {"command": "grep -rn ghoul rules playervault"}),
        ("Bash", {"command": "solo-roll turn --state state/clock.json"}),
        ("Bash", {"command": "cat rules/combat.md | head -5"}),
        ("Bash", {"command": "cat >> playervault/Map.md <<EOF\nThe dungeon is damp.\nEOF"}),
    ])
    def test_allows(self, camp, tool, tool_input):
        assert not camp_denied(camp, tool, tool_input)

    def test_referee_may_search_from_the_root(self, camp):
        assert not camp_denied(camp, "Grep", {"pattern": "secret"},
                               agent_type="referee")
