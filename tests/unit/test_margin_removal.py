import pytest

from prediction_markets_lab.probability.margin_removal import (
    margin_free_probabilities_from_odds,
    proportional_margin_removal,
)


def test_proportional_margin_removal_sums_to_one():
    raw = [0.5, 0.35, 0.30]  # sums to 1.15 (15% overround)
    fair = proportional_margin_removal(raw)
    assert sum(fair) == pytest.approx(1.0)


def test_proportional_margin_removal_preserves_relative_order():
    raw = [0.5, 0.35, 0.30]
    fair = proportional_margin_removal(raw)
    assert fair[0] > fair[1] > fair[2]


def test_proportional_margin_removal_no_margin_is_unchanged():
    raw = [0.5, 0.5]
    fair = proportional_margin_removal(raw)
    assert fair == pytest.approx([0.5, 0.5])


def test_proportional_margin_removal_rejects_empty():
    with pytest.raises(ValueError):
        proportional_margin_removal([])


def test_proportional_margin_removal_rejects_non_positive():
    with pytest.raises(ValueError):
        proportional_margin_removal([0.5, 0.0])
    with pytest.raises(ValueError):
        proportional_margin_removal([0.5, -0.1])


def test_margin_free_probabilities_from_odds_sums_to_one():
    fair = margin_free_probabilities_from_odds([2.10, 3.40, 3.60])
    assert sum(fair) == pytest.approx(1.0)
    assert all(0.0 < p < 1.0 for p in fair)
