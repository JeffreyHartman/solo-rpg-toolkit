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
