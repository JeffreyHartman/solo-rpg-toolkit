import json
import subprocess


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["solo-roll", *args],
        capture_output=True,
        text=True,
    )


def test_table_subcommand_returns_required_keys():
    result = _run("table", "action1", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["table"] == "action1"
    assert payload["dice"] == "d100"
    assert 1 <= payload["roll"] <= 100
    assert isinstance(payload["result"], str) and payload["result"]


def test_table_subcommand_nested_path():
    result = _run("table", "elements/plottwist", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["table"] == "elements/plottwist"


def test_table_subcommand_unknown_table_exits_1():
    result = _run("table", "does_not_exist", "--seed", "0")
    assert result.returncode == 1
    assert "not found" in result.stderr.lower() or "does_not_exist" in result.stderr


def test_table_subcommand_same_seed_is_reproducible():
    a = _run("table", "action1", "--seed", "42")
    b = _run("table", "action1", "--seed", "42")
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout
