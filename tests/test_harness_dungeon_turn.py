"""Tests for the OSE dungeon turn through `Engine.act`: Search, Listen, Rest, light, and the wandering trigger."""
import json

import pytest
from harness_fixtures import make_campaign

from solo_roll.harness.engine import open_campaign
from solo_roll.harness.errors import PluginError, UnknownCommandError
from solo_roll.harness.plugins.ose import OsePlugin
from solo_roll.harness.registry import Registry
from solo_roll.rng import ScriptedDice

WANDERING_TABLE = {
    "name": "ose/w", "description": "d", "dice": "d6", "source": "test",
    "entries": ["bats", "spiders", "goblins", "jelly", "ghouls", "rats"],
}
REACTION_TABLE = {
    "name": "ose/reaction", "description": "d", "dice": "2d6", "source": "test",
    "ranges": [{"min": -20, "max": 30, "result": "Neutral"}],
}
SEARCH_TABLE = {
    "name": "ose/searching", "description": "d", "dice": "d6", "source": "OSE p12",
    "entries": ["Found."] + ["Nothing found."] * 5,
}
LISTEN_TABLE = {
    "name": "ose/listen-at-door", "description": "d", "dice": "d6", "source": "OSE p12",
    "entries": ["A sound is heard."] + ["Nothing heard."] * 5,
}


@pytest.fixture
def data_dir(tmp_path):
    root = tmp_path / "data"
    for table in (WANDERING_TABLE, REACTION_TABLE, SEARCH_TABLE, LISTEN_TABLE):
        path = root / "tables" / f"{table['name']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(table))
    return root


def engine_with(tmp_path, data_dir, rolls, **plugin_options):
    factories = {"ose": lambda: OsePlugin(data_dir=data_dir, **plugin_options)}
    return open_campaign(make_campaign(tmp_path), ScriptedDice(rolls), factories)


def run(engine, name):
    return engine.act({"type": "procedure", "name": name})


def test_search_is_an_available_action(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [])

    ids = [a["id"] for a in engine.available_actions()]

    assert {"search", "listen", "rest"} <= set(ids)


def test_search_shows_a_mechanics_card_for_the_roll(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [1])

    events = run(engine, "search")

    card = events[0]
    assert card["type"] == "mechanics"
    assert card["procedure"] == "search"
    assert (card["dice"], card["rolls"], card["total"]) == ("d6", [1], 1)
    assert card["result"] == "Found."
    assert card["source"] == "OSE p12"
    assert card["text"]


def test_search_takes_a_turn_and_burns_the_torch(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [2])

    events = run(engine, "search")

    assert [e["type"] for e in events] == ["mechanics", "turn"]
    dungeon = engine.state()["dungeon"]
    assert dungeon["turn"] == 1
    assert dungeon["light"][0]["turns_left"] == 5


def test_listen_rolls_the_listen_table_and_takes_a_turn(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [1])

    events = run(engine, "listen")

    assert events[0]["procedure"] == "listen"
    assert events[0]["result"] == "A sound is heard."
    assert engine.state()["dungeon"]["turn"] == 1


def test_rest_takes_a_turn_without_a_roll_and_resets_the_rest_clock(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [2], wandering=None)
    run(engine, "search")
    assert engine.state()["dungeon"]["turns_since_rest"] == 1

    events = run(engine, "rest")

    assert [e["type"] for e in events] == ["turn"]
    assert events[0]["rested"] is True
    assert engine.state()["dungeon"]["turns_since_rest"] == 0


def test_the_wandering_check_runs_on_the_second_turn_only(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [2, 2, 4])

    first = run(engine, "search")
    second = run(engine, "search")

    assert [e["type"] for e in first] == ["mechanics", "turn"]
    assert [e["type"] for e in second] == ["mechanics", "turn", "mechanics"]
    check = second[2]
    assert check["procedure"] == "wandering_check"
    assert (check["dice"], check["rolls"], check["result"]) == ("d6", [4], "No encounter")


def test_a_wandering_hit_rolls_the_monster_distance_surprise_and_reaction(tmp_path, data_dir):
    # search, search, check 1 (hit), monster d6 3, distance 2d6 (3+4), surprise 6 and 2, reaction 2d6 (3+3)
    rolls = [2, 2, 1, 3, 3, 4, 6, 2, 3, 3, 4, 5, 2]
    engine = engine_with(tmp_path, data_dir, rolls, wandering={"table": "ose/w", "interval": 2})
    run(engine, "search")

    events = run(engine, "search")

    encounter = next(e for e in events if e["type"] == "wandering_encounter")
    assert events[2]["result"] == "Wandering monster"
    assert encounter["type"] == "wandering_encounter"
    assert encounter["monster"] == "goblins"
    assert encounter["distance_feet"] == 70
    assert encounter["surprise"] == {"party": False, "monsters": True}
    assert encounter["reaction"] == "Neutral"


def test_no_wandering_config_means_no_check(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [2, 2], wandering=None)

    run(engine, "search")
    events = run(engine, "search")

    assert [e["type"] for e in events] == ["mechanics", "turn"]


def test_the_torch_goes_out_after_six_turns(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [], wandering=None)
    for _ in range(5):
        run(engine, "rest")

    events = run(engine, "rest")

    assert [e["type"] for e in events] == ["turn", "light_out", "darkness"]
    assert engine.state()["dungeon"]["light"] == []


def test_the_state_note_shows_the_turn_and_the_light(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [], wandering=None)
    run(engine, "rest")

    note = (tmp_path / "campaign" / "vault" / "State.md").read_text()

    assert "Turn: 1" in note
    assert "Light: torch (Brannoc), 5 turns left" in note


def test_the_state_note_reports_darkness(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [], wandering=None)
    for _ in range(6):
        run(engine, "rest")

    note = (tmp_path / "campaign" / "vault" / "State.md").read_text()

    assert "Light: none (darkness)" in note


def test_the_raw_log_records_the_mechanics_card_text(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [1], wandering=None)

    run(engine, "search")

    log = (tmp_path / "campaign" / "vault" / "Sessions" / "Raw" / "Session 001.md").read_text()
    assert "Search: rolled 1 on d6. Found." in log


def test_a_failed_procedure_leaves_the_turn_unchanged(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [], wandering=None)  # no scripted roll for the search

    with pytest.raises(RuntimeError):
        run(engine, "search")

    assert engine.state()["dungeon"]["turn"] == 0


def test_an_unknown_procedure_is_refused(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [])

    with pytest.raises(UnknownCommandError):
        run(engine, "dance")


def test_the_default_wandering_table_ships_with_the_ose_data():
    from solo_roll import OSE_DATA_DIR
    from solo_roll.harness.plugins.ose.dungeon_turn import DEFAULT_WANDERING
    from solo_roll.tables import load_table

    assert load_table(DEFAULT_WANDERING["table"], OSE_DATA_DIR)["entries"]


class _PingPlugin:
    """A plugin whose `ping` procedure emits a `ping` event and whose trigger answers it."""

    name = "ping"
    kind = "ruleset"

    def __init__(self, loop=False):
        self._loop = loop

    def register(self, registry):
        registry.add_procedure("ping", lambda state, cmd, ctx: [{"type": "ping", "text": "ping"}])
        reply = "ping" if self._loop else "pong"
        registry.add_trigger("ping", lambda state, event, ctx: [{"type": reply, "text": reply}])
        registry.add_trigger("pong", lambda state, event, ctx: [{"type": "echo", "text": "echo"}])


def test_trigger_events_follow_their_source_event_and_fire_further_triggers(tmp_path):
    engine = open_campaign(make_campaign(tmp_path), ScriptedDice([]), {"ose": _PingPlugin})

    events = engine.act({"type": "procedure", "name": "ping"})

    assert [e["type"] for e in events] == ["ping", "pong", "echo"]


def test_triggers_that_fire_each_other_forever_are_stopped(tmp_path):
    engine = open_campaign(make_campaign(tmp_path), ScriptedDice([]), {"ose": lambda: _PingPlugin(loop=True)})

    with pytest.raises(PluginError):
        engine.act({"type": "procedure", "name": "ping"})


def test_a_procedure_with_an_unknown_confirm_level_is_not_accepted():
    with pytest.raises(PluginError):
        Registry().add_procedure("x", lambda s, c, ctx: [], confirm="sometimes")


def test_moving_takes_a_dungeon_turn_and_burns_the_torch(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [], wandering=None)

    events = engine.act({"type": "move", "to": "hall"})

    assert [e["type"] for e in events] == ["area_revealed", "moved", "turn"]
    dungeon = engine.state()["dungeon"]
    assert dungeon["turn"] == 1
    assert dungeon["light"][0]["turns_left"] == 5


def test_moving_runs_the_wandering_check_on_the_second_turn(tmp_path, data_dir):
    engine = engine_with(tmp_path, data_dir, [2, 4])
    run(engine, "search")

    events = engine.act({"type": "move", "to": "hall"})

    assert [e["procedure"] for e in events if e["type"] == "mechanics"] == ["wandering_check"]


def test_a_wandering_encounter_starts_combat_with_the_rolled_monsters(tmp_path, data_dir):
    # search, search, check 1 (hit), monster 3, distance 3+4, surprise 6 and 2, reaction 3+3, hp d8 4, initiative 5 vs 2
    rolls = [2, 2, 1, 3, 3, 4, 6, 2, 3, 3, 4, 5, 2]
    engine = engine_with(tmp_path, data_dir, rolls, wandering={"table": "ose/w", "interval": 2})
    run(engine, "search")

    events = run(engine, "search")

    combat = engine.state()["combat"]
    assert "combat_started" in [e["type"] for e in events]
    assert combat["area"] == "gate"
    assert [(m["name"], m["hp"]) for m in combat["monsters"]] == [("goblins", 4)]
    assert combat["outcome"] is None
