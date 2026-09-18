"""Tests for performance.bootstrap (Gate 1 build)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.performance.bootstrap import paired_bootstrap_mean_diff


def test_point_estimate_matches_raw_mean_difference():
    series_a = [1.0, 2.0, 3.0, 4.0]
    series_b = [0.5, 1.5, 2.5, 3.5]
    result = paired_bootstrap_mean_diff(series_a, series_b, seed=1, n_resamples=500)
    assert result.point_estimate == pytest.approx(0.5)


def test_ci_bounds_are_ordered():
    series_a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    series_b = [0.9, 1.8, 3.2, 3.9, 5.3, 5.7]
    result = paired_bootstrap_mean_diff(series_a, series_b, seed=7, n_resamples=1000)
    assert result.ci_lower <= result.point_estimate <= result.ci_upper


def test_identical_series_gives_zero_point_estimate_and_ci_includes_zero():
    series = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = paired_bootstrap_mean_diff(series, series, seed=3, n_resamples=1000)
    assert result.point_estimate == pytest.approx(0.0)
    assert not result.excludes_zero


def test_consistently_higher_series_excludes_zero():
    series_a = [10.0 + i for i in range(50)]
    series_b = [1.0 + i for i in range(50)]
    result = paired_bootstrap_mean_diff(series_a, series_b, seed=11, n_resamples=2000)
    assert result.point_estimate == pytest.approx(9.0)
    assert result.excludes_zero
    assert result.ci_lower > 0.0


def test_reproducible_with_same_seed():
    series_a = [1.0, 5.0, 2.0, 9.0, 3.0, 7.0]
    series_b = [2.0, 4.0, 1.0, 8.0, 5.0, 6.0]
    r1 = paired_bootstrap_mean_diff(series_a, series_b, seed=42, n_resamples=500)
    r2 = paired_bootstrap_mean_diff(series_a, series_b, seed=42, n_resamples=500)
    assert r1.ci_lower == r2.ci_lower
    assert r1.ci_upper == r2.ci_upper


def test_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        paired_bootstrap_mean_diff([1.0, 2.0], [1.0], seed=1)


def test_raises_on_empty_series():
    with pytest.raises(ValueError, match="zero matched pairs"):
        paired_bootstrap_mean_diff([], [], seed=1)


def test_raises_on_invalid_n_resamples():
    with pytest.raises(ValueError, match="n_resamples"):
        paired_bootstrap_mean_diff([1.0], [2.0], seed=1, n_resamples=0)


def test_raises_on_invalid_confidence_level():
    with pytest.raises(ValueError, match="confidence_level"):
        paired_bootstrap_mean_diff([1.0, 2.0], [1.0, 2.0], seed=1, confidence_level=1.5)
