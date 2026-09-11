import pytest

from prediction_markets_lab.performance.calibration import (
    CalibrationBin,
    compute_calibration_bins,
    compute_outcome_calibration,
)


def test_rejects_length_mismatch():
    with pytest.raises(ValueError):
        compute_calibration_bins([0.5, 0.6], [True], n_bins=1)


def test_rejects_empty_input():
    with pytest.raises(ValueError):
        compute_calibration_bins([], [], n_bins=1)


def test_rejects_n_bins_less_than_one():
    with pytest.raises(ValueError):
        compute_calibration_bins([0.5], [True], n_bins=0)


def test_rejects_n_bins_exceeding_n_matches():
    with pytest.raises(ValueError):
        compute_calibration_bins([0.5, 0.6], [True, False], n_bins=3)


def test_perfectly_calibrated_input_has_zero_gap_everywhere():
    # 10 matches, predicted probability == exact fraction of the bin that
    # actually occurs: with n_bins=2 and this construction, every bin's
    # mean predicted probability should equal its observed frequency.
    preds = [0.2] * 5 + [0.8] * 5
    actuals = ([False] * 4 + [True]) + ([False] + [True] * 4)
    bins = compute_calibration_bins(preds, actuals, n_bins=2)
    assert len(bins) == 2
    for b in bins:
        assert b.mean_predicted_probability == pytest.approx(b.observed_frequency, abs=1e-9)
        assert b.gap == pytest.approx(0.0, abs=1e-9)


def test_bins_are_ordered_by_increasing_predicted_probability():
    preds = [0.9, 0.1, 0.5, 0.3, 0.7]
    actuals = [True, False, True, False, True]
    bins = compute_calibration_bins(preds, actuals, n_bins=5)
    means = [b.mean_predicted_probability for b in bins]
    assert means == sorted(means)


def test_bin_sizes_differ_by_at_most_one_when_uneven():
    n = 11
    preds = [i / n for i in range(n)]
    actuals = [i % 2 == 0 for i in range(n)]
    bins = compute_calibration_bins(preds, actuals, n_bins=4)
    sizes = [b.n for b in bins]
    assert sum(sizes) == n
    assert max(sizes) - min(sizes) <= 1


def test_every_match_is_counted_exactly_once():
    preds = [0.1, 0.9, 0.4, 0.6, 0.5, 0.5, 0.2, 0.8]
    actuals = [True, False, True, True, False, False, True, False]
    bins = compute_calibration_bins(preds, actuals, n_bins=3)
    assert sum(b.n for b in bins) == len(preds)


def test_completely_miscalibrated_model_has_large_gap():
    # Confidently predicts 0.9 for an outcome that never happens.
    preds = [0.9] * 20
    actuals = [False] * 20
    bins = compute_calibration_bins(preds, actuals, n_bins=1)
    assert bins[0].gap == pytest.approx(0.9, abs=1e-9)


def _uniform(h, d, a):
    return {"home": h, "draw": d, "away": a}


def test_compute_outcome_calibration_rejects_unknown_outcome():
    with pytest.raises(ValueError):
        compute_outcome_calibration([_uniform(0.5, 0.3, 0.2)], ["home"], outcome="bogus")


def test_compute_outcome_calibration_rejects_length_mismatch():
    with pytest.raises(ValueError):
        compute_outcome_calibration(
            [_uniform(0.5, 0.3, 0.2), _uniform(0.4, 0.3, 0.3)], ["home"], outcome="home"
        )


def test_compute_outcome_calibration_ece_zero_for_perfect_calibration():
    n = 10
    predictions = [_uniform(0.2, 0.3, 0.5)] * n
    # Exactly 20% home, matching the stated home probability.
    actuals = (["home"] * 2) + (["away"] * 8)
    report = compute_outcome_calibration(predictions, actuals, outcome="home", n_bins=1)
    assert report.n_matches == n
    assert report.expected_calibration_error == pytest.approx(0.0, abs=1e-9)


def test_compute_outcome_calibration_extracts_correct_outcome_probability():
    predictions = [_uniform(0.6, 0.25, 0.15), _uniform(0.3, 0.3, 0.4)]
    actuals = ["home", "away"]
    report = compute_outcome_calibration(predictions, actuals, outcome="away", n_bins=1)
    assert report.bins[0].mean_predicted_probability == pytest.approx((0.15 + 0.4) / 2, abs=1e-9)
    assert report.bins[0].observed_frequency == pytest.approx(0.5, abs=1e-9)


def test_calibration_bin_is_frozen_dataclass():
    b = CalibrationBin(
        bin_index=0, n=5, mean_predicted_probability=0.5, observed_frequency=0.4,
        min_predicted_probability=0.1, max_predicted_probability=0.9,
    )
    with pytest.raises(Exception):
        b.n = 10
