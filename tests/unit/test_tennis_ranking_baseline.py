"""Tests for prediction_markets_lab.models.tennis_ranking_baseline --
Workstream A4's baseline A (ranking-only, no Elo, no market data)."""
from datetime import date
from math import log

import numpy as np
import pytest

from prediction_markets_lab.models.tennis_ranking_baseline import (
    RankingBaselineMatchInput,
    fit_ranking_baseline,
    has_usable_ranking,
    predict_ranking_baseline,
)


def _match(match_id, a_points, b_points, outcome_a_won, d=date(2021, 1, 1)):
    return RankingBaselineMatchInput(match_id, d, a_points, b_points, outcome_a_won)


def test_has_usable_ranking_true_for_two_positive_points():
    assert has_usable_ranking(_match("m1", 1000.0, 500.0, 1)) is True


def test_has_usable_ranking_false_when_a_points_missing():
    assert has_usable_ranking(_match("m1", None, 500.0, 1)) is False


def test_has_usable_ranking_false_when_b_points_missing():
    assert has_usable_ranking(_match("m1", 1000.0, None, 1)) is False


def test_has_usable_ranking_false_for_nan_points():
    assert has_usable_ranking(_match("m1", float("nan"), 500.0, 1)) is False


def test_has_usable_ranking_false_for_zero_or_negative_points():
    assert has_usable_ranking(_match("m1", 0.0, 500.0, 1)) is False
    assert has_usable_ranking(_match("m1", -10.0, 500.0, 1)) is False


def test_fit_rejects_empty_training_set():
    with pytest.raises(ValueError):
        fit_ranking_baseline([])


def test_fit_rejects_matches_with_missing_ranking_points():
    matches = [
        _match("m1", 1000.0, 500.0, 1),
        _match("m2", None, 500.0, 0),
    ]
    with pytest.raises(ValueError, match="has_usable_ranking"):
        fit_ranking_baseline(matches)


def test_predict_rejects_matches_with_missing_ranking_points():
    model = fit_ranking_baseline([_match("m1", 1000.0, 500.0, 1), _match("m2", 500.0, 1000.0, 0)])
    with pytest.raises(ValueError, match="has_usable_ranking"):
        predict_ranking_baseline(model, [_match("m3", None, 500.0, 1)])


def test_predict_rejects_empty_matches():
    model = fit_ranking_baseline([_match("m1", 1000.0, 500.0, 1), _match("m2", 500.0, 1000.0, 0)])
    with pytest.raises(ValueError):
        predict_ranking_baseline(model, [])


def test_fit_recovers_known_logistic_relationship():
    # Generate outcomes from a KNOWN true intercept/slope on the
    # log-points-ratio feature, then check the fit recovers them --
    # the same style of ground-truth-recovery check used for
    # fit_logistic_regression itself, applied through this module's
    # feature construction.
    rng = np.random.default_rng(7)
    n = 20000
    a_points = rng.uniform(50, 5000, n)
    b_points = rng.uniform(50, 5000, n)
    true_intercept, true_slope = 0.1, 1.4
    feature = np.log(a_points) - np.log(b_points)
    p = 1.0 / (1.0 + np.exp(-(true_intercept + true_slope * feature)))
    outcomes = rng.binomial(1, p)

    matches = [
        _match(f"m{i}", float(a_points[i]), float(b_points[i]), int(outcomes[i]))
        for i in range(n)
    ]
    model = fit_ranking_baseline(matches)
    assert model.intercept == pytest.approx(true_intercept, abs=0.05)
    assert model.coefficients[0] == pytest.approx(true_slope, abs=0.05)


def test_predict_matches_manual_sigmoid_computation():
    training = [_match(f"m{i}", 2000.0 if i % 2 == 0 else 400.0, 400.0 if i % 2 == 0 else 2000.0, i % 2 == 0) for i in range(200)]
    model = fit_ranking_baseline(training)

    held_out = _match("held_out", 1200.0, 300.0, 1)
    [pred] = predict_ranking_baseline(model, [held_out])
    assert pred.match_id == "held_out"

    feature = log(1200.0) - log(300.0)
    expected = 1.0 / (1.0 + np.exp(-(model.intercept + model.coefficients[0] * feature)))
    assert pred.p_a_win == pytest.approx(expected)


def test_predict_is_monotonic_in_ranking_points_advantage():
    # A player with a bigger points advantage over their opponent must
    # never get a LOWER predicted win probability than one with a
    # smaller advantage, all else equal -- the model must have learned
    # a positive (not negative or zero) slope on real-shaped training data.
    rng = np.random.default_rng(11)
    n = 5000
    a_points = rng.uniform(50, 5000, n)
    b_points = rng.uniform(50, 5000, n)
    feature = np.log(a_points) - np.log(b_points)
    p = 1.0 / (1.0 + np.exp(-(0.0 + 1.0 * feature)))
    outcomes = rng.binomial(1, p)
    training = [_match(f"m{i}", float(a_points[i]), float(b_points[i]), int(outcomes[i])) for i in range(n)]
    model = fit_ranking_baseline(training)

    small_edge = _match("small", 1100.0, 1000.0, 1)
    big_edge = _match("big", 4000.0, 1000.0, 1)
    small_pred, big_pred = predict_ranking_baseline(model, [small_edge, big_edge])
    assert big_pred.p_a_win > small_pred.p_a_win
