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
