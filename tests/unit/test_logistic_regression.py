"""Tests for prediction_markets_lab.models.logistic_regression -- the
from-scratch IRLS logistic fit used by Workstream A4's tennis baselines."""
import numpy as np
import pytest

from prediction_markets_lab.models.logistic_regression import fit_logistic_regression


def test_recovers_known_single_feature_model():
    rng = np.random.default_rng(3)
    n = 20000
    x = rng.normal(0, 1, n)
    true_intercept, true_slope = 0.4, 1.3
    p = 1.0 / (1.0 + np.exp(-(true_intercept + true_slope * x)))
    y = rng.binomial(1, p)

    model = fit_logistic_regression(x.reshape(-1, 1), y.tolist(), ["x"], l2_penalty=1e-8)
    assert model.intercept == pytest.approx(true_intercept, abs=0.05)
    assert model.coefficients[0] == pytest.approx(true_slope, abs=0.05)


def test_recovers_known_two_feature_model_and_predict_proba_matches():
    rng = np.random.default_rng(5)
    n = 30000
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    true_intercept, true_b1, true_b2 = -0.2, 0.9, -0.5
    logit = true_intercept + true_b1 * x1 + true_b2 * x2
    p = 1.0 / (1.0 + np.exp(-logit))
    y = rng.binomial(1, p)

    features = np.column_stack([x1, x2])
    model = fit_logistic_regression(features, y.tolist(), ["x1", "x2"], l2_penalty=1e-8)
    assert model.intercept == pytest.approx(true_intercept, abs=0.05)
    assert model.coefficients[0] == pytest.approx(true_b1, abs=0.05)
    assert model.coefficients[1] == pytest.approx(true_b2, abs=0.05)

    # predict_proba on a fresh point should match the closed-form sigmoid.
    test_point = np.array([[1.0, -1.0]])
    predicted = model.predict_proba(test_point)[0]
    expected = 1.0 / (1.0 + np.exp(-(model.intercept + model.coefficients[0] * 1.0 + model.coefficients[1] * -1.0)))
    assert predicted == pytest.approx(expected)


def test_rejects_nan_features():
    x = np.array([[1.0], [np.nan], [3.0]])
    with pytest.raises(ValueError):
        fit_logistic_regression(x, [1, 0, 1], ["x"])


def test_rejects_mismatched_lengths():
    x = np.array([[1.0], [2.0]])
    with pytest.raises(ValueError):
        fit_logistic_regression(x, [1, 0, 1], ["x"])


def test_rejects_empty_input():
    with pytest.raises(ValueError):
        fit_logistic_regression(np.empty((0, 1)), [], ["x"])


def test_perfectly_separable_data_does_not_crash_thanks_to_ridge():
    """A perfect separator would send unregularised logistic regression's
    coefficients to infinity and never converge -- the small default L2
    penalty must keep this finite and convergent."""
    x = np.array([-3.0, -2.0, -1.0, 1.0, 2.0, 3.0]).reshape(-1, 1)
    y = [0, 0, 0, 1, 1, 1]
    model = fit_logistic_regression(x, y, ["x"])
    assert np.isfinite(model.intercept)
    assert np.isfinite(model.coefficients[0])
    assert model.coefficients[0] > 0  # correct direction at least
