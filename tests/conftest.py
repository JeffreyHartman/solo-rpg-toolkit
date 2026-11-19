from collections.abc import Callable
from pathlib import Path

import pytest

from solo_roll.campaign import _resolve_repo_root
from solo_roll.rng import ScriptedDice


@pytest.fixture
def ose_template() -> Path:
    """The templates/ose directory of this checkout."""
    return _resolve_repo_root() / "templates" / "ose"


@pytest.fixture
def example_template() -> Path:
    """The example-campaign directory of this checkout."""
    return _resolve_repo_root() / "example-campaign"


@pytest.fixture
def scripted_dice() -> Callable[[list[int]], ScriptedDice]:
    def _make(values: list[int]) -> ScriptedDice:
        return ScriptedDice(values)
    return _make
