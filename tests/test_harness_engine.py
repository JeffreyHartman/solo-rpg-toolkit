"""Tests for `harness.engine.Engine` through `act`, `state` and `available_actions`."""
import pytest
from harness_fixtures import make_campaign, open_engine

from solo_roll.harness.engine import open_campaign
from solo_roll.harness.errors import IllegalActionError, PluginError, UnknownCommandError
from solo_roll.harness.plugins.ose import OsePlugin
from solo_roll.rng import ScriptedDice


def test_move_to_a_connected_area_changes_the_party_position(tmp_path):
    engine = open_engine(make_campaign(tmp_path))

    events = engine.act({"type": "move", "to": "hall"})

    assert events[0]["type"] == "moved"
    assert (events[0]["from"], events[0]["to"]) == ("gate", "hall")
    assert engine.state()["party"]["area"] == "hall"


def test_a_move_without_a_connection_is_refused_and_changes_nothing(tmp_path):
    engine = open_engine(make_campaign(tmp_path))
    before = engine.state()

    with pytest.raises(IllegalActionError):
        engine.act({"type": "move", "to": "crypt"})

    assert engine.state() == before


def test_entering_an_unknown_area_reveals_it(tmp_path):
    engine = open_engine(make_campaign(tmp_path))
    assert engine.state()["map"]["areas"]["hall"]["known"] is False

    events = engine.act({"type": "move", "to": "hall"})

    assert events[1] == {"type": "area_revealed", "area": "hall", "text": "New area: Long Hall."}
    assert engine.state()["map"]["areas"]["hall"]["known"] is True


def test_available_actions_offer_one_move_per_exit_of_the_current_area(tmp_path):
    engine = open_engine(make_campaign(tmp_path))
    engine.act({"type": "move", "to": "hall"})

    actions = {a["id"]: a for a in engine.available_actions() if a["command"]["type"] == "move"}

    assert set(actions) == {"move:gate", "move:crypt"}
    assert actions["move:gate"]["label"] == "Go to Gatehouse"
    assert actions["move:crypt"]["label"] == "Take the north stair"
    assert actions["move:crypt"]["command"] == {"type": "move", "to": "crypt"}


def test_running_an_available_action_command_moves_the_party(tmp_path):
    engine = open_engine(make_campaign(tmp_path))
    [action] = [a for a in engine.available_actions() if a["command"]["type"] == "move"]

    engine.act(action["command"])

    assert engine.state()["party"]["area"] == "hall"


def test_state_survives_reopening_the_campaign(tmp_path):
    campaign = make_campaign(tmp_path)
    open_engine(campaign).act({"type": "move", "to": "hall"})

    assert open_engine(campaign).state()["party"]["area"] == "hall"


def test_an_unknown_command_type_raises(tmp_path):
    engine = open_engine(make_campaign(tmp_path))

    with pytest.raises(UnknownCommandError):
        engine.act({"type": "dance"})


def test_a_campaign_naming_an_unknown_plugin_fails_to_open(tmp_path):
    campaign = make_campaign(tmp_path)

    with pytest.raises(PluginError):
        open_campaign(campaign, ScriptedDice([]), {})


def test_two_plugins_cannot_claim_the_same_command(tmp_path):
    campaign = make_campaign(tmp_path)
    (campaign / "campaign.json").write_text('{"plugins": ["ose", "ose-again"]}')

    with pytest.raises(PluginError):
        open_campaign(campaign, ScriptedDice([]), {"ose": OsePlugin, "ose-again": OsePlugin})


def test_a_move_appends_its_event_text_to_the_session_raw_log(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    engine.act({"type": "move", "to": "hall"})
    engine.act({"type": "move", "to": "gate"})

    log = (campaign / "vault" / "Sessions" / "Raw" / "Session 001.md").read_text()
    lines = [line for line in log.splitlines() if line.startswith("- ")]
    assert lines == [
        "- The party moves from Gatehouse to Long Hall.",
        "- New area: Long Hall.",
        "- The party moves from Long Hall to Gatehouse.",
    ]


def test_state_note_shows_the_party_position_after_a_move(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    engine.act({"type": "move", "to": "hall"})

    note = (campaign / "vault" / "State.md").read_text()
    assert "Written by the engine" in note
    assert "Position: Long Hall" in note
    assert "Brannoc" in note


def test_a_refused_command_writes_nothing_to_the_vault(tmp_path):
    campaign = make_campaign(tmp_path)
    engine = open_engine(campaign)

    with pytest.raises(IllegalActionError):
        engine.act({"type": "move", "to": "crypt"})

    assert not (campaign / "vault" / "Sessions" / "Raw" / "Session 001.md").exists()


class DicePlugin:
    """A test plugin whose `roll` command reports one d6 from the engine's dice."""

    name = "dice-test"
    kind = "generator"

    def register(self, registry):
        registry.add_command("roll", self._roll)

    @staticmethod
    def _roll(state, command, ctx):
        value = ctx.dice.roll(1, 6)
        return [{"type": "rolled", "value": value, "text": f"Rolled {value}."}]


def test_command_handlers_roll_with_the_injected_dice(tmp_path):
    campaign = make_campaign(tmp_path)
    (campaign / "campaign.json").write_text('{"plugins": ["ose", "dice-test"]}')
    engine = open_campaign(
        campaign, ScriptedDice([4]), {"ose": OsePlugin, "dice-test": DicePlugin}
    )

    assert engine.act({"type": "roll"})[0]["value"] == 4
