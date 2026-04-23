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


FATE_REQUIRED_KEYS = {
    "likelihood", "cf", "yes_threshold", "exceptional_yes_cap",
    "exceptional_no_floor", "dice", "roll", "outcome", "exceptional",
    "random_event_triggered",
}


def test_fate_check_returns_required_keys():
    result = _run("fate-check", "--likelihood", "likely", "--cf", "5", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) >= FATE_REQUIRED_KEYS
    assert payload["likelihood"] == "likely"
    assert payload["cf"] == 5
    assert payload["outcome"] in {"yes", "no", "exceptional_yes", "exceptional_no"}
    assert isinstance(payload["exceptional"], bool)
    assert isinstance(payload["random_event_triggered"], bool)
    assert len(payload["dice"]) == 2


def test_fate_check_unknown_likelihood_exits_1():
    result = _run("fate-check", "--likelihood", "bogus", "--cf", "5")
    assert result.returncode == 1


def test_fate_check_cf_out_of_range_exits_1():
    result = _run("fate-check", "--likelihood", "likely", "--cf", "99")
    assert result.returncode == 1


def test_fate_check_reproducible_with_seed():
    a = _run("fate-check", "--likelihood", "likely", "--cf", "5", "--seed", "123")
    b = _run("fate-check", "--likelihood", "likely", "--cf", "5", "--seed", "123")
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout


def test_meaning_pair_defaults_action1_descriptor1():
    result = _run("meaning-pair", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"action", "description"}
    assert payload["action"]["table"] == "action1"
    assert payload["description"]["table"] == "descriptor1"
    for side in ("action", "description"):
        assert set(payload[side].keys()) >= {"table", "roll", "result"}


def test_meaning_pair_custom_tables_flag():
    result = _run("meaning-pair", "--tables", "action2,descriptor2", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["action"]["table"] == "action2"
    assert payload["description"]["table"] == "descriptor2"


def test_meaning_pair_bad_tables_flag_exits_1():
    result = _run("meaning-pair", "--tables", "only_one")
    assert result.returncode == 1


def test_quickset_npc_profile_runs_end_to_end():
    result = _run("quickset", "npc_profile", "--seed", "0")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == "npc_profile"
    assert payload["name"] == "NPC Profile"
    assert len(payload["steps"]) == 8
    for step in payload["steps"]:
        assert {"label", "table", "roll", "result"} <= step.keys()
        assert 1 <= step["roll"] <= 100


def test_quickset_unknown_id_exits_1():
    result = _run("quickset", "not_a_real_quickset")
    assert result.returncode == 1


def test_roll_d10_in_range():
    out = _run("roll", "d10")
    assert out.returncode == 0
    data = json.loads(out.stdout)
    assert data["dice"] == "d10"
    assert 1 <= data["roll"] <= 10


def test_roll_d6_in_range():
    out = _run("roll", "d6")
    assert out.returncode == 0
    data = json.loads(out.stdout)
    assert data["dice"] == "d6"
    assert 1 <= data["roll"] <= 6


def test_roll_d100_in_range():
    out = _run("roll", "d100")
    assert out.returncode == 0
    data = json.loads(out.stdout)
    assert data["dice"] == "d100"
    assert 1 <= data["roll"] <= 100


def test_roll_invalid_dice_exits_1():
    out = _run("roll", "foo")
    assert out.returncode == 1


def test_roll_d1_exits_1():
    out = _run("roll", "d1")
    assert out.returncode == 1


def test_roll_reproducible_with_seed():
    r1 = _run("roll", "d10", "--seed", "42")
    r2 = _run("roll", "d10", "--seed", "42")
    assert r1.returncode == 0
    assert r2.returncode == 0
    assert json.loads(r1.stdout)["roll"] == json.loads(r2.stdout)["roll"]
