import pytest

from prediction_markets_lab.probability.consensus import (
    calculate_consensus,
    calculate_consensus_per_outcome,
)


def test_calculate_consensus_median_and_mean():
    probs = [0.45, 0.47, 0.50, 0.44, 0.60]  # 0.60 is a stale outlier
    result = calculate_consensus(probs)
    assert result.median == pytest.approx(0.47)
    assert result.consensus_probability == pytest.approx(result.median)
    assert result.mean == pytest.approx(sum(probs) / len(probs))
    assert result.bookmaker_count == 5
    assert result.minimum == pytest.approx(0.44)
    assert result.maximum == pytest.approx(0.60)


def test_median_is_robust_to_a_single_stale_outlier():
    # The outlier (0.90) should barely move the median but heavily
    # skews the mean — demonstrating why median is the V1 default.
    probs = [0.45, 0.46, 0.47, 0.48, 0.90]
    result = calculate_consensus(probs)
    assert result.median == pytest.approx(0.47)
    assert result.mean > result.median  # mean is pulled upward by outlier


def test_calculate_consensus_weighted_mean():
    probs = [0.40, 0.50]
    weights = [3.0, 1.0]  # first bookmaker weighted 3x
    result = calculate_consensus(probs, weights=weights)
    assert result.weighted_mean == pytest.approx((0.40 * 3 + 0.50 * 1) / 4)


def test_calculate_consensus_weighted_mean_none_by_default():
    result = calculate_consensus([0.4, 0.5])
    assert result.weighted_mean is None


def test_calculate_consensus_rejects_empty():
    with pytest.raises(ValueError):
        calculate_consensus([])


def test_calculate_consensus_rejects_out_of_range_probability():
    with pytest.raises(ValueError):
        calculate_consensus([0.5, 1.2])
    with pytest.raises(ValueError):
        calculate_consensus([0.5, 0.0])


def test_calculate_consensus_rejects_mismatched_weights():
    with pytest.raises(ValueError):
        calculate_consensus([0.4, 0.5], weights=[1.0])


def test_calculate_consensus_per_outcome():
    by_outcome = {
        "home": [0.45, 0.47, 0.50],
        "draw": [0.25, 0.24, 0.26],
        "away": [0.30, 0.29, 0.24],
    }
    results = calculate_consensus_per_outcome(by_outcome)
    assert set(results.keys()) == {"home", "draw", "away"}
    assert results["home"].bookmaker_count == 3
