import pytest
from pathlib import Path
from solo_roll import DEFAULT_DATA_DIR
from solo_roll.charts import (
    FateChartError,
    KnownLikelihood,
    fate_check,
    load_fate_chart,
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


def test_fate_chart_loads_with_nine_likelihoods_and_nine_cfs():
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    assert len(chart.likelihoods) == 9
    for key in chart.likelihoods:
        assert len(chart.thresholds[key]) == 9
        for value in chart.thresholds[key]:
            assert 1 <= value <= 99


def test_fate_chart_likelihoods_match_known_set():
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    expected = {
        "has_to_be", "near_sure_thing", "very_likely", "likely",
        "50_50", "unlikely", "very_unlikely", "near_impossible", "no_way",
    }
    assert set(chart.likelihoods) == expected


def test_fate_chart_thresholds_monotonic_in_cf():
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    for key, row in chart.thresholds.items():
        for i in range(1, len(row)):
            assert row[i] >= row[i - 1], f"{key} not monotonic at CF {i+1}: {row}"


def test_fate_check_returns_complete_payload(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([4, 3])  # 43 -> yes at likely/CF5 (threshold 75)
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["likelihood"] == "likely"
    assert payload["cf"] == 5
    assert payload["yes_threshold"] == 75
    assert payload["exceptional_yes_cap"] == 15
    assert payload["exceptional_no_floor"] == 95
    assert payload["dice"] == [4, 3]
    assert payload["roll"] == 43
    assert payload["outcome"] == "yes"
    assert payload["exceptional"] is False
    assert payload["random_event_triggered"] is False


def test_fate_check_doubles_under_cf_triggers_event(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([4, 4])  # doubles, 4 <= CF 5
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["random_event_triggered"] is True


def test_fate_check_doubles_above_cf_does_not_trigger_event(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([7, 7])
    payload = fate_check("likely", cf=3, chart=chart, dice=dice)
    assert payload["random_event_triggered"] is False


def test_fate_check_exceptional_yes(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([0, 5])  # roll 5, <= exc_yes_cap 15 at likely/CF5
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["outcome"] == "exceptional_yes"
    assert payload["exceptional"] is True


def test_fate_check_exceptional_no(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([9, 7])  # roll 97, >= exc_no_floor 95 at likely/CF5
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["outcome"] == "exceptional_no"
    assert payload["exceptional"] is True


def test_fate_check_double_zero_rolls_100(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    dice = scripted_dice([0, 0])  # rolls 100 -> no or exceptional_no
    payload = fate_check("likely", cf=5, chart=chart, dice=dice)
    assert payload["roll"] == 100
    assert payload["outcome"] in ("no", "exceptional_no")


def test_fate_check_unknown_likelihood_raises(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    with pytest.raises(FateChartError):
        fate_check("definitely_not_a_key", cf=5, chart=chart, dice=scripted_dice([4, 3]))


def test_fate_check_cf_out_of_range_raises(scripted_dice):
    chart = load_fate_chart(DEFAULT_DATA_DIR)
    with pytest.raises(FateChartError):
        fate_check("likely", cf=0, chart=chart, dice=scripted_dice([4, 3]))
    with pytest.raises(FateChartError):
        fate_check("likely", cf=10, chart=chart, dice=scripted_dice([4, 3]))


def test_known_likelihoods_is_frozen_set():
    assert isinstance(KnownLikelihood, frozenset)
    assert "likely" in KnownLikelihood
