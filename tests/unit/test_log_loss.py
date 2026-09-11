import math

import pytest

from prediction_markets_lab.performance.log_loss import (
    log_loss_single,
    multiclass_log_loss,
    validate_outcome_probabilities,
)


def test_log_loss_single_confident_correct_is_near_zero():
    loss = log_loss_single({"home": 0.98, "draw": 0.01, "away": 0.01}, "home")
    assert loss < 0.05


def test_log_loss_single_confident_wrong_is_large():
    loss = log_loss_single({"home": 0.98, "draw": 0.01, "away": 0.01}, "away")
    assert loss > 4.0


def test_log_loss_single_uniform_prediction_equals_ln3():
    loss = log_loss_single({"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3}, "draw")
    assert math.isclose(loss, math.log(3), rel_tol=1e-9)


def test_log_loss_single_rejects_bad_outcome():
    with pytest.raises(ValueError):
        log_loss_single({"home": 0.5, "draw": 0.3, "away": 0.2}, "nonsense")


def test_validate_outcome_probabilities_rejects_missing_key():
    with pytest.raises(ValueError):
        validate_outcome_probabilities({"home": 0.5, "draw": 0.5})


def test_validate_outcome_probabilities_rejects_negative():
    with pytest.raises(ValueError):
        validate_outcome_probabilities({"home": -0.1, "draw": 0.6, "away": 0.5})


def test_validate_outcome_probabilities_rejects_bad_sum():
    with pytest.raises(ValueError):
        validate_outcome_probabilities({"home": 0.5, "draw": 0.5, "away": 0.5})


def test_validate_outcome_probabilities_accepts_valid():
    validate_outcome_probabilities({"home": 0.4, "draw": 0.3, "away": 0.3})


def test_multiclass_log_loss_mean_of_two_matches():
    preds = [
        {"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3},
        {"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3},
    ]
    actuals = ["home", "away"]
    assert math.isclose(multiclass_log_loss(preds, actuals), math.log(3), rel_tol=1e-9)


def test_multiclass_log_loss_rejects_length_mismatch():
    with pytest.raises(ValueError):
        multiclass_log_loss([{"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3}], ["home", "away"])


def test_multiclass_log_loss_rejects_empty_input():
    with pytest.raises(ValueError):
        multiclass_log_loss([], [])


def test_multiclass_log_loss_never_produces_infinite_value():
    # A wildly overconfident wrong prediction must still return a finite,
    # heavily-penalised number, not -inf/NaN from log(0).
    preds = [{"home": 1.0, "draw": 0.0, "away": 0.0}]
    loss = multiclass_log_loss(preds, ["away"])
    assert math.isfinite(loss)
    assert loss > 30.0
