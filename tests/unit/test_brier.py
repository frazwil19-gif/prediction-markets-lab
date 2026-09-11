"""Tests for performance.brier (multiclass/vector Brier score, Stage 3B)."""

import math

import pytest

from prediction_markets_lab.performance.brier import brier_score_single, multiclass_brier_score


def test_brier_score_single_perfect_confident_prediction_is_zero():
    score = brier_score_single({"home": 1.0, "draw": 0.0, "away": 0.0}, "home")
    assert math.isclose(score, 0.0, abs_tol=1e-12)


def test_brier_score_single_confident_wrong_prediction_is_two():
    score = brier_score_single({"home": 1.0, "draw": 0.0, "away": 0.0}, "away")
    assert math.isclose(score, 2.0, abs_tol=1e-12)


def test_brier_score_single_uniform_prediction():
    # (1/3 - 1)^2 + (1/3 - 0)^2 + (1/3 - 0)^2 = 4/9 + 1/9 + 1/9 = 6/9 = 2/3
    score = brier_score_single({"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3}, "home")
    assert math.isclose(score, 2 / 3, rel_tol=1e-9)


def test_brier_score_single_rejects_bad_outcome():
    with pytest.raises(ValueError):
        brier_score_single({"home": 0.5, "draw": 0.3, "away": 0.2}, "nonsense")


def test_brier_score_single_rejects_bad_sum():
    with pytest.raises(ValueError):
        brier_score_single({"home": 0.5, "draw": 0.5, "away": 0.5}, "home")


def test_multiclass_brier_score_mean_of_two_matches():
    preds = [
        {"home": 1.0, "draw": 0.0, "away": 0.0},
        {"home": 1.0, "draw": 0.0, "away": 0.0},
    ]
    actuals = ["home", "away"]  # one perfect (0.0), one fully wrong (2.0)
    assert math.isclose(multiclass_brier_score(preds, actuals), 1.0, rel_tol=1e-9)


def test_multiclass_brier_score_rejects_length_mismatch():
    with pytest.raises(ValueError):
        multiclass_brier_score([{"home": 1.0, "draw": 0.0, "away": 0.0}], ["home", "away"])


def test_multiclass_brier_score_rejects_empty_input():
    with pytest.raises(ValueError):
        multiclass_brier_score([], [])
