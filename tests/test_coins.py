"""Tests for `coins.parse_coin_slot`, the reader shared by the coin roll and the import check."""
import pytest

from solo_roll.coins import parse_coin_slot


@pytest.mark.parametrize(
    "result, index, expected",
    [
        ("1d4 gp / 2d6 x 10 gp", 0, (1, 4, 1)),
        ("1d4 gp / 2d6 x 10 gp", 1, (2, 6, 10)),
        ("1d4 gp / 2d6 x 10 gp", 2, None),
        ("2d6x10", 0, (2, 6, 10)),
        ("2d6 x10 gp", 0, (2, 6, 10)),
        ("2d6 x 10", 0, (2, 6, 10)),
        ("1d4 x 2k", 0, (1, 4, 2000)),
        ("1d4x2k gp", 0, (1, 4, 2000)),
        ("3d4", 0, (3, 4, 1)),
        ("Some prose.", 0, None),
        ("Reroll twice", 0, None),
        ("1d4 gp / many", 1, None),
    ],
)
def test_parse_coin_slot(result, index, expected):
    assert parse_coin_slot(result, index) == expected
