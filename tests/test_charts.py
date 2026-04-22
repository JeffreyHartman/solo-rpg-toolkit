import pytest

from solo_roll.charts import (
    classify_outcome,
    is_random_event,
    read_d100,
    thresholds,
)


def test_thresholds_formula_mid():
    result = thresholds(yes_threshold=75)
    assert result.yes_threshold == 75
    assert result.exceptional_yes_cap == 15  # 75 // 5
    assert result.exceptional_no_floor == 95  # 100 - ((100 - 75) // 5) = 100 - 5


def test_thresholds_formula_low():
    result = thresholds(yes_threshold=5)
    assert result.exceptional_yes_cap == 1   # 5 // 5
    assert result.exceptional_no_floor == 81 # 100 - ((100 - 5) // 5) = 100 - 19


def test_thresholds_formula_high():
    result = thresholds(yes_threshold=95)
    assert result.exceptional_yes_cap == 19  # 95 // 5
    assert result.exceptional_no_floor == 99 # 100 - ((100 - 95) // 5) = 100 - 1


def test_read_d100_double_zero_is_100():
    assert read_d100(0, 0) == 100


def test_read_d100_standard_pairs():
    assert read_d100(4, 3) == 43
    assert read_d100(9, 0) == 90
    assert read_d100(0, 7) == 7
    assert read_d100(1, 1) == 11


def test_read_d100_rejects_out_of_range():
    with pytest.raises(ValueError):
        read_d100(10, 0)
    with pytest.raises(ValueError):
        read_d100(-1, 0)


def test_classify_outcome_exceptional_yes():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(10, t) == ("exceptional_yes", True)


def test_classify_outcome_yes():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(43, t) == ("yes", False)


def test_classify_outcome_no():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(80, t) == ("no", False)


def test_classify_outcome_exceptional_no():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(97, t) == ("exceptional_no", True)


def test_classify_outcome_boundary_exact_yes_threshold_is_yes():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(75, t) == ("yes", False)


def test_classify_outcome_boundary_exact_exceptional_yes_cap_is_exceptional():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(15, t) == ("exceptional_yes", True)


def test_classify_outcome_boundary_exact_exceptional_no_floor_is_exceptional():
    t = thresholds(yes_threshold=75)
    assert classify_outcome(95, t) == ("exceptional_no", True)


def test_is_random_event_doubles_under_cf_fires():
    assert is_random_event(4, 4, cf=5) is True


def test_is_random_event_doubles_above_cf_does_not_fire():
    assert is_random_event(4, 4, cf=3) is False


def test_is_random_event_doubles_equal_cf_fires():
    assert is_random_event(5, 5, cf=5) is True


def test_is_random_event_non_doubles_never_fires():
    assert is_random_event(4, 3, cf=9) is False
    assert is_random_event(0, 1, cf=9) is False


def test_is_random_event_double_zero_does_not_fire_unless_cf_allows():
    # 0 == 0 is doubles. 0 <= any CF (>=1) so it fires at any CF.
    assert is_random_event(0, 0, cf=1) is True
