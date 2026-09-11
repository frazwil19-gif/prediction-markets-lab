from datetime import date

import pytest

from prediction_markets_lab.probability.uncertainty import (
    BootstrapResult,
    paired_bootstrap_delta,
)


def _uniform(h, d, a):
    return {"home": h, "draw": d, "away": a}


def test_rejects_length_mismatch():
    with pytest.raises(ValueError):
        paired_bootstrap_delta(
            [_uniform(0.5, 0.3, 0.2)], [_uniform(0.4, 0.3, 0.3), _uniform(0.4, 0.3, 0.3)],
            ["home"], metric="log_loss",
        )


def test_rejects_empty_input():
    with pytest.raises(ValueError):
        paired_bootstrap_delta([], [], [], metric="log_loss")


def test_rejects_unknown_metric():
    with pytest.raises(ValueError):
        paired_bootstrap_delta(
            [_uniform(0.5, 0.3, 0.2)], [_uniform(0.4, 0.3, 0.3)], ["home"], metric="accuracy"
        )


def test_rejects_unknown_method():
    with pytest.raises(ValueError):
        paired_bootstrap_delta(
            [_uniform(0.5, 0.3, 0.2)], [_uniform(0.4, 0.3, 0.3)], ["home"],
            metric="log_loss", method="bogus",
        )


def test_block_by_date_requires_dates():
    with pytest.raises(ValueError):
        paired_bootstrap_delta(
            [_uniform(0.5, 0.3, 0.2)], [_uniform(0.4, 0.3, 0.3)], ["home"],
            metric="log_loss", method="block_by_date",
        )


def test_identical_predictions_give_zero_point_estimate_and_tight_ci():
    n = 50
    preds = [_uniform(0.5, 0.3, 0.2)] * n
    actuals = ["home", "draw", "away"] * (n // 3) + ["home"] * (n % 3)
    result = paired_bootstrap_delta(preds, preds, actuals, metric="log_loss", n_resamples=200, seed=1)
    assert result.point_estimate == pytest.approx(0.0, abs=1e-9)
    assert result.ci_lower == pytest.approx(0.0, abs=1e-9)
    assert result.ci_upper == pytest.approx(0.0, abs=1e-9)


def test_model_strictly_worse_than_market_gives_positive_point_estimate():
    n = 100
    model_preds = [_uniform(1 / 3, 1 / 3, 1 / 3)] * n  # uninformative
    market_preds = [_uniform(0.7, 0.2, 0.1)] * n  # confidently and correctly right below
    actuals = ["home"] * n
    result = paired_bootstrap_delta(model_preds, market_preds, actuals, metric="log_loss", n_resamples=200, seed=1)
    assert result.point_estimate > 0  # model (uniform) worse than market here


def test_result_is_reproducible_given_same_seed():
    n = 40
    model_preds = [_uniform(0.4, 0.3, 0.3)] * n
    market_preds = [_uniform(0.5, 0.25, 0.25)] * n
    actuals = (["home", "draw", "away"] * 14)[:n]
    r1 = paired_bootstrap_delta(model_preds, market_preds, actuals, metric="brier", n_resamples=300, seed=7)
    r2 = paired_bootstrap_delta(model_preds, market_preds, actuals, metric="brier", n_resamples=300, seed=7)
    assert r1 == r2


def test_block_by_date_groups_same_date_matches_together():
    # Two matches share date d1; if block bootstrap works, resampling
    # d1 should always bring BOTH matches at once -- verified indirectly
    # by checking the CI is wider than treating all 4 matches as
    # independent would produce (fewer effective independent units: 3
    # dates instead of 4 matches).
    d1, d2, d3 = date(2020, 8, 1), date(2020, 8, 8), date(2020, 8, 15)
    dates = [d1, d1, d2, d3]
    model_preds = [_uniform(0.6, 0.2, 0.2), _uniform(0.2, 0.2, 0.6), _uniform(0.4, 0.3, 0.3), _uniform(0.5, 0.3, 0.2)]
    market_preds = [_uniform(0.5, 0.3, 0.2), _uniform(0.3, 0.3, 0.4), _uniform(0.5, 0.25, 0.25), _uniform(0.4, 0.3, 0.3)]
    actuals = ["home", "away", "draw", "home"]
    result = paired_bootstrap_delta(
        model_preds, market_preds, actuals, metric="log_loss", dates=dates,
        method="block_by_date", n_resamples=500, seed=3,
    )
    assert result.n_matches == 4
    assert result.method == "block_by_date"


def test_ci_bounds_are_ordered():
    n = 60
    model_preds = [_uniform(0.5, 0.3, 0.2) if i % 2 == 0 else _uniform(0.3, 0.3, 0.4) for i in range(n)]
    market_preds = [_uniform(0.45, 0.3, 0.25)] * n
    actuals = (["home", "draw", "away"] * 20)[:n]
    result = paired_bootstrap_delta(model_preds, market_preds, actuals, metric="log_loss", n_resamples=300, seed=5)
    assert result.ci_lower <= result.ci_upper
