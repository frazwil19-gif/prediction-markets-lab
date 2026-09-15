"""Tests for prediction_markets_lab.performance.binary_classification --
the tennis (binary-outcome) metrics module built for Workstream A4."""
import math

import numpy as np
import pytest

from prediction_markets_lab.performance.binary_classification import (
    binary_auc,
    binary_brier_score,
    binary_brier_score_single,
    binary_calibration_bins,
    binary_log_loss,
    binary_log_loss_single,
    expected_calibration_error,
    fit_calibration_intercept_slope,
)


def test_log_loss_uniform_prediction_matches_known_constant():
    preds = [0.5] * 100
    actuals = [1] * 50 + [0] * 50
    assert binary_log_loss(preds, actuals) == pytest.approx(math.log(2), abs=1e-9)


def test_log_loss_perfect_prediction_near_zero():
    preds = [0.999999999, 0.000000001]
    actuals = [1, 0]
    assert binary_log_loss(preds, actuals) < 1e-6


def test_log_loss_confidently_wrong_is_heavily_penalised():
    confident_right = binary_log_loss_single(0.99, 1)
    confident_wrong = binary_log_loss_single(0.99, 0)
    assert confident_wrong > confident_right * 100


def test_log_loss_rejects_invalid_actual():
    with pytest.raises(ValueError):
        binary_log_loss_single(0.5, 2)


def test_brier_score_bounds_and_known_values():
    assert binary_brier_score_single(1.0, 1) == pytest.approx(0.0)
    assert binary_brier_score_single(0.0, 1) == pytest.approx(1.0)
    assert binary_brier_score_single(0.5, 1) == pytest.approx(0.25)
    assert binary_brier_score([0.7, 0.3], [1, 0]) == pytest.approx((0.09 + 0.09) / 2)


def test_calibration_bins_perfectly_calibrated_data():
    # Construct data where each of 5 equal-count bins has predicted
    # probability exactly equal to observed frequency.
    preds, actuals = [], []
    for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
        n = 100
        n_pos = int(round(p * n))
        preds.extend([p] * n)
        actuals.extend([1] * n_pos + [0] * (n - n_pos))
    bins = binary_calibration_bins(preds, actuals, n_bins=5)
    assert len(bins) == 5
    for b in bins:
        assert b.gap < 0.02  # allow tiny rounding from n_pos=round()
    assert expected_calibration_error(bins) < 0.02


def test_calibration_bins_detects_overconfidence():
    # Model predicts 0.9 but only 50% actually happen -- badly overconfident.
    preds = [0.9] * 200
    actuals = [1] * 100 + [0] * 100
    bins = binary_calibration_bins(preds, actuals, n_bins=1)
    assert bins[0].mean_predicted_probability == pytest.approx(0.9)
    assert bins[0].observed_frequency == pytest.approx(0.5)
    assert bins[0].gap == pytest.approx(0.4)


def test_auc_perfect_separation_is_one():
    preds = [0.1, 0.2, 0.3, 0.8, 0.9, 0.95]
    actuals = [0, 0, 0, 1, 1, 1]
    assert binary_auc(preds, actuals) == pytest.approx(1.0)


def test_auc_random_guessing_is_near_half():
    rng = np.random.default_rng(42)
    preds = rng.uniform(0, 1, 2000).tolist()
    actuals = rng.integers(0, 2, 2000).tolist()
    auc = binary_auc(preds, actuals)
    assert 0.45 < auc < 0.55


def test_auc_inverted_prediction_is_near_zero():
    preds = [0.9, 0.8, 0.7, 0.2, 0.1, 0.05]  # backwards relative to actuals
    actuals = [0, 0, 0, 1, 1, 1]
    assert binary_auc(preds, actuals) == pytest.approx(0.0)


def test_auc_raises_with_single_class():
    with pytest.raises(ValueError):
        binary_auc([0.1, 0.9], [1, 1])


def test_calibration_intercept_slope_recovers_well_calibrated_truth():
    """Generate data from a KNOWN true logistic model, fit predicted
    probabilities exactly equal to the true model's probabilities, and
    verify the fitted calibration comes back close to intercept=0,
    slope=1 -- i.e. a genuinely well-calibrated model should not appear
    to need recalibration."""
    rng = np.random.default_rng(7)
    n = 5000
    x = rng.normal(0, 1, n)
    true_p = 1.0 / (1.0 + np.exp(-(0.3 + 1.1 * x)))
    y = rng.binomial(1, true_p)
    intercept, slope = fit_calibration_intercept_slope(true_p.tolist(), y.tolist())
    assert intercept == pytest.approx(0.0, abs=0.15)
    assert slope == pytest.approx(1.0, abs=0.15)


def test_calibration_intercept_slope_detects_overconfidence():
    """An overconfident model (predictions pushed toward 0/1 relative to
    the true generating probabilities) should show a fitted slope < 1."""
    rng = np.random.default_rng(11)
    n = 5000
    x = rng.normal(0, 1, n)
    true_logit = 0.2 + 0.8 * x
    true_p = 1.0 / (1.0 + np.exp(-true_logit))
    y = rng.binomial(1, true_p)
    overconfident_p = 1.0 / (1.0 + np.exp(-2.0 * true_logit))  # slope doubled -> overconfident
    intercept, slope = fit_calibration_intercept_slope(overconfident_p.tolist(), y.tolist())
    assert slope < 0.7  # should recover something well below 1


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        binary_log_loss([0.5, 0.5], [1])
    with pytest.raises(ValueError):
        binary_brier_score([0.5, 0.5], [1])
    with pytest.raises(ValueError):
        binary_calibration_bins([0.5] * 20, [1] * 19, n_bins=5)
