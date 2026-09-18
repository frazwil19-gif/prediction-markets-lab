"""Tests for models.multinomial_logistic_regression (Gate 1 build)."""

from __future__ import annotations

import numpy as np
import pytest

from prediction_markets_lab.models.multinomial_logistic_regression import (
    fit_multinomial_logistic_regression,
)

CLASSES = ("home", "draw", "away")


def _separable_synthetic_dataset(n_per_class: int = 200, seed: int = 1):
    """A single feature whose value cleanly indicates the class, on a
    RAW scale (large numbers, mimicking an Elo rating gap) -- exercises
    both the model's ability to recover a strong signal and its internal
    feature standardisation (fitting/predicting must work identically on
    unstandardised input)."""
    rng = np.random.default_rng(seed)
    home_feature = rng.normal(loc=400.0, scale=20.0, size=n_per_class)
    draw_feature = rng.normal(loc=0.0, scale=20.0, size=n_per_class)
    away_feature = rng.normal(loc=-400.0, scale=20.0, size=n_per_class)
    features = np.concatenate([home_feature, draw_feature, away_feature]).reshape(-1, 1)
    outcomes = ["home"] * n_per_class + ["draw"] * n_per_class + ["away"] * n_per_class
    return features, outcomes


def test_recovers_strongly_separable_classes_with_high_accuracy():
    features, outcomes = _separable_synthetic_dataset()
    model = fit_multinomial_logistic_regression(
        features, outcomes, feature_names=["rating_gap"], classes=CLASSES, seed=0
    )
    probs = model.predict_proba(features)
    predicted = [CLASSES[i] for i in np.argmax(probs, axis=1)]
    accuracy = sum(p == a for p, a in zip(predicted, outcomes)) / len(outcomes)
    assert accuracy > 0.95


def test_predict_proba_rows_sum_to_one():
    features, outcomes = _separable_synthetic_dataset(n_per_class=30)
    model = fit_multinomial_logistic_regression(
        features, outcomes, feature_names=["rating_gap"], classes=CLASSES, seed=0
    )
    probs = model.predict_proba(features)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-8)
    assert (probs >= 0.0).all()


def test_predict_proba_dict_matches_array_output():
    features, outcomes = _separable_synthetic_dataset(n_per_class=10)
    model = fit_multinomial_logistic_regression(
        features, outcomes, feature_names=["rating_gap"], classes=CLASSES, seed=0
    )
    as_array = model.predict_proba(features[:3])
    as_dicts = model.predict_proba_dict(features[:3])
    for row_array, row_dict in zip(as_array, as_dicts):
        for i, cls in enumerate(CLASSES):
            assert row_dict[cls] == pytest.approx(row_array[i])


def test_raises_on_nan_features():
    features = np.array([[1.0, np.nan], [2.0, 3.0]])
    with pytest.raises(ValueError, match="NaN"):
        fit_multinomial_logistic_regression(
            features, ["home", "away"], feature_names=["a", "b"], classes=CLASSES
        )


def test_raises_on_row_count_mismatch():
    features = np.array([[1.0], [2.0], [3.0]])
    with pytest.raises(ValueError, match="rows"):
        fit_multinomial_logistic_regression(
            features, ["home", "away"], feature_names=["a"], classes=CLASSES
        )


def test_raises_on_feature_name_count_mismatch():
    features = np.array([[1.0, 2.0], [3.0, 4.0]])
    with pytest.raises(ValueError, match="feature_names"):
        fit_multinomial_logistic_regression(
            features, ["home", "away"], feature_names=["a"], classes=CLASSES
        )


def test_raises_on_non_positive_l2_penalty():
    features = np.array([[1.0], [2.0]])
    with pytest.raises(ValueError, match="l2_penalty"):
        fit_multinomial_logistic_regression(
            features, ["home", "away"], feature_names=["a"], classes=CLASSES, l2_penalty=0.0
        )


def test_raises_on_outcome_not_in_classes():
    features = np.array([[1.0], [2.0]])
    with pytest.raises(ValueError, match="not in classes"):
        fit_multinomial_logistic_regression(
            features, ["home", "draw"], feature_names=["a"], classes=("home", "away")
        )


def test_zero_variance_feature_does_not_crash_standardisation():
    features, outcomes = _separable_synthetic_dataset(n_per_class=20)
    constant_col = np.ones((features.shape[0], 1)) * 7.0
    features_with_constant = np.hstack([features, constant_col])
    model = fit_multinomial_logistic_regression(
        features_with_constant, outcomes, feature_names=["rating_gap", "constant"], classes=CLASSES, seed=0
    )
    assert model.feature_stds[1] == pytest.approx(1.0)
    probs = model.predict_proba(features_with_constant[:5])
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-8)


def test_missing_class_in_training_data_still_predicts_all_classes():
    """A fold whose training data happens to contain zero examples of one
    class (never expected for home/draw/away in practice, but the model
    must not silently break) still returns a valid 3-way probability."""
    features = np.array([[400.0], [-400.0], [420.0], [-380.0]])
    outcomes = ["home", "away", "home", "away"]  # zero "draw" examples
    model = fit_multinomial_logistic_regression(
        features, outcomes, feature_names=["rating_gap"], classes=CLASSES, seed=0
    )
    probs = model.predict_proba(np.array([[0.0]]))
    assert probs.shape == (1, 3)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-8)
