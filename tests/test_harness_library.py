"""Tests for `harness.library.Library`: list, create and open campaigns in one folder."""
import pytest

from solo_roll.harness.campaign import CampaignPaths
from solo_roll.harness.errors import CampaignFileError, PluginError
from solo_roll.harness.library import Library
from solo_roll.harness.plugins import BUILTIN_PLUGINS
from solo_roll.rng import ScriptedDice

FIGHTER_ROLLS = [3, 3, 3, 4, 4, 4, 2, 2, 3, 5, 5, 4, 6, 5, 5, 3, 3, 4, 5]


class FakeModule:
    name = "tomb"
    kind = "module"

    def register(self, registry):
        pass


@pytest.fixture
def library(tmp_path):
    factories = {**BUILTIN_PLUGINS, "tomb": FakeModule}
    return Library(tmp_path / "campaigns", factories, dice=lambda: ScriptedDice(list(FIGHTER_ROLLS)))


def test_only_installed_plugins_are_offered_by_kind(library):
    assert library.installed() == {"ruleset": ["ose"], "generator": ["flextale"], "module": ["tomb"]}


def test_a_new_campaign_has_a_vault_a_referee_folder_and_an_empty_party(library):
    campaign_id = library.create("Tomb Delve", ruleset="ose", generators=["flextale"], module="tomb")

    paths = CampaignPaths(library.root / campaign_id)
    assert paths.vault.is_dir() and paths.referee.is_dir() and paths.state.exists()
    engine, _ = library.open(campaign_id)
    assert engine.state()["party"]["members"] == []
    assert engine.state()["map"]["open_exits"]
    assert library.campaigns() == [
        {"id": campaign_id, "name": "Tomb Delve", "plugins": ["ose", "flextale", "tomb"], "members": [], "session": 1}
    ]


@pytest.mark.parametrize(
    "args",
    [
        {"ruleset": "flextale", "generators": []},
        {"ruleset": "ose", "generators": ["ose"]},
        {"ruleset": "ose", "generators": [], "module": "flextale"},
        {"ruleset": "nope", "generators": []},
    ],
)
def test_a_plugin_of_the_wrong_kind_or_not_installed_is_refused(library, args):
    with pytest.raises(PluginError):
        library.create("Bad", **args)

    assert library.campaigns() == []


def test_two_campaigns_cannot_share_a_name(library):
    library.create("Delve", ruleset="ose", generators=[])

    with pytest.raises(CampaignFileError):
        library.create("delve", ruleset="ose", generators=[])


def test_a_saved_campaign_opens_where_it_stopped(library):
    campaign_id = library.create("Delve", ruleset="ose", generators=[])
    engine, _ = library.open(campaign_id)
    engine.act({"type": "procedure", "name": "create_character", "class": "Fighter", "character_name": "Brannoc"})

    reopened, _ = library.open(campaign_id)

    assert [m["name"] for m in reopened.state()["party"]["members"]] == ["Brannoc"]
    assert library.campaigns()[0]["members"] == ["Brannoc"]


def test_opening_an_unknown_campaign_is_refused(library):
    with pytest.raises(CampaignFileError):
        library.open("missing")
    with pytest.raises(CampaignFileError):
        library.open("../escape")
