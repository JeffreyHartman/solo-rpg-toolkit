"""Tests for `harness.cli.main`: the demo campaign and the server bind address."""
import pytest

pytest.importorskip("fastapi")

from harness_fixtures import make_campaign, open_engine  # noqa: E402

from solo_roll.harness.cli import main  # noqa: E402


def test_serve_binds_all_interfaces_and_prints_the_lan_url(tmp_path, capsys):
    campaign = make_campaign(tmp_path)
    calls = []

    code = main(
        ["serve", str(campaign), "--port", "8123"],
        run=lambda app, host, port: calls.append((host, port)),
        lan_ip=lambda: "192.168.1.40",
    )

    assert code == 0
    assert calls == [("0.0.0.0", 8123)]
    assert "http://192.168.1.40:8123/" in capsys.readouterr().out


def test_serve_on_a_folder_with_no_campaign_exits_with_an_error(tmp_path, capsys):
    code = main(["serve", str(tmp_path)], run=lambda *a, **k: None, lan_ip=lambda: "10.0.0.2")

    assert code == 1
    assert "campaign.json" in capsys.readouterr().err


def test_demo_creates_a_campaign_the_engine_can_walk(tmp_path):
    assert main(["demo", str(tmp_path / "demo")]) == 0

    engine = open_engine(tmp_path / "demo")
    first = engine.available_actions()[0]
    engine.act(first["command"])

    assert engine.state()["party"]["area"] == first["command"]["to"]


@pytest.fixture
def referee_args(monkeypatch):
    pytest.importorskip("claude_agent_sdk")
    seen = []

    class Recorder:
        def __init__(self, engine, paths, model, effort):
            seen.append((model, effort))

        async def close(self):
            pass

    monkeypatch.setattr("solo_roll.harness.referee.sdk.AgentSdkReferee", Recorder)
    return seen


def serve(campaign, *flags):
    return main(["serve", str(campaign), *flags], run=lambda *a, **k: None, lan_ip=lambda: "10.0.0.2")


def test_serve_starts_the_referee_with_the_campaign_model_and_effort(tmp_path, referee_args):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)
    engine.change_setting("referee", "model", "opus")
    engine.change_setting("referee", "effort", "high")

    serve(campaign)

    assert referee_args == [("opus", "high")]


def test_serve_flags_change_the_campaign_model_and_effort(tmp_path, referee_args):
    campaign = make_campaign(tmp_path)

    serve(campaign, "--model", "haiku", "--effort", "medium")

    assert referee_args == [("haiku", "medium")]
    assert open_engine(campaign).settings()["referee"]["model"] == "haiku"


def test_serve_with_a_campaign_folder_and_no_campaign_starts_on_the_library(tmp_path, capsys):
    apps = []

    code = main(
        ["serve", "--campaigns", str(tmp_path / "campaigns"), "--referee", "none"],
        run=lambda app, host, port: apps.append(app),
        lan_ip=lambda: "10.0.0.2",
    )

    assert code == 0
    from fastapi.testclient import TestClient

    with TestClient(apps[0]).websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "library"


def test_serve_needs_a_campaign_or_a_campaign_folder(capsys):
    assert main(["serve"], run=lambda *a, **k: None) == 1
    assert "--campaigns" in capsys.readouterr().err


def test_serve_reads_flextale_tables_from_the_data_folder_main_is_given(tmp_path):
    from fastapi.testclient import TestClient
    from flextale_fakes import MAP, write_tables

    from solo_roll.harness.campaign import create_campaign

    write_tables(tmp_path / "xdg" / "solo-rpg-toolkit" / "flextale")
    campaign = create_campaign(tmp_path / "campaign", ["ose", "flextale"], MAP, "start", [{"name": "Brannoc"}])
    apps = []

    main(
        ["serve", str(campaign), "--referee", "none"],
        run=lambda app, host, port: apps.append(app),
        lan_ip=lambda: "10.0.0.2",
        env={"XDG_DATA_HOME": str(tmp_path / "xdg")},
        home=tmp_path / "home",
    )

    with TestClient(apps[0]).websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "act", "command": {"type": "explore", "exit": "e1"}})
        reply = ws.receive_json()

    assert reply["type"] == "events", reply


def test_each_campaign_the_library_opens_gets_its_own_dice(tmp_path):
    from fastapi.testclient import TestClient

    apps = []
    main(
        ["serve", "--campaigns", str(tmp_path / "campaigns"), "--referee", "none", "--seed", "7"],
        run=lambda app, host, port: apps.append(app),
        lan_ip=lambda: "10.0.0.2",
        env={},
        home=tmp_path / "home",
    )
    abilities = []
    with TestClient(apps[0]).websocket_connect("/ws") as ws:
        ws.receive_json()
        for name in ("First Delve", "Second Delve"):
            ws.send_json({"type": "new_campaign", "name": name, "ruleset": "ose", "generators": []})
            ws.receive_json()
            ws.send_json({"type": "act", "command": {
                "type": "procedure", "name": "create_character",
                "inputs": {"class": "Fighter", "character_name": "Brannoc"}}})
            abilities.append(ws.receive_json()["state"]["party"]["members"][0]["abilities"])

    assert abilities[0] != abilities[1]
