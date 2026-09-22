import pytest

from prediction_markets_lab.backtesting.metrics import bootstrap_mean_ci, bootstrap_ratio_ci


def test_bootstrap_mean_ci_point_estimate_matches_plain_mean():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = bootstrap_mean_ci(values, "test_stat", n_resamples=500, seed=1)
    assert result.point_estimate == pytest.approx(3.0)
    assert result.ci_lower <= result.point_estimate <= result.ci_upper


def test_bootstrap_mean_ci_deterministic_given_fixed_seed():
    values = [0.1, 0.4, 0.9, -0.2, 0.3, 0.7]
    a = bootstrap_mean_ci(values, "x", n_resamples=300, seed=42)
    b = bootstrap_mean_ci(values, "x", n_resamples=300, seed=42)
    assert a.ci_lower == b.ci_lower
    assert a.ci_upper == b.ci_upper


def test_bootstrap_mean_ci_rejects_empty_input():
    with pytest.raises(ValueError):
        bootstrap_mean_ci([], "empty")


def test_bootstrap_mean_ci_excludes_zero_flag():
    all_positive = bootstrap_mean_ci([1.0, 1.1, 0.9, 1.2, 0.95], "x", n_resamples=500, seed=7)
    assert all_positive.excludes_zero is True

    around_zero = bootstrap_mean_ci([1.0, -1.0, 0.5, -0.5, 0.0], "x", n_resamples=500, seed=7)
    assert around_zero.excludes_zero is False


def test_bootstrap_ratio_ci_matches_plain_ratio_point_estimate():
    numerators = [1.0, -1.0, 2.0, -1.0]
    denominators = [1.0, 1.0, 1.0, 1.0]
    result = bootstrap_ratio_ci(numerators, denominators, "roi", n_resamples=500, seed=3)
    assert result.point_estimate == pytest.approx(1.0 / 4.0)


def test_bootstrap_ratio_ci_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        bootstrap_ratio_ci([1.0, 2.0], [1.0], "x")


def test_bootstrap_ratio_ci_rejects_zero_total_denominator():
    with pytest.raises(ValueError):
        bootstrap_ratio_ci([1.0, -1.0], [0.0, 0.0], "x")
