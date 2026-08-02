import pytest

from prediction_markets_lab.probability.odds_conversion import (
    decimal_odds_list_to_implied_probabilities,
    decimal_odds_to_implied_probability,
    overround,
)


def test_decimal_odds_to_implied_probability_basic():
    assert decimal_odds_to_implied_probability(2.0) == pytest.approx(0.5)
    assert decimal_odds_to_implied_probability(4.0) == pytest.approx(0.25)


def test_decimal_odds_to_implied_probability_rejects_invalid_odds():
    with pytest.raises(ValueError):
        decimal_odds_to_implied_probability(1.0)
    with pytest.raises(ValueError):
        decimal_odds_to_implied_probability(0.5)


def test_decimal_odds_list_to_implied_probabilities():
    result = decimal_odds_list_to_implied_probabilities([2.0, 4.0, 4.0])
    assert result == pytest.approx([0.5, 0.25, 0.25])


def test_decimal_odds_list_rejects_empty():
    with pytest.raises(ValueError):
        decimal_odds_list_to_implied_probabilities([])


def test_overround_positive_for_bookmaker_market():
    # A three-way market priced with a typical bookmaker margin.
    margin = overround([2.10, 3.40, 3.60])
    assert margin > 0.0


def test_overround_zero_for_fair_market():
    # A perfectly fair two-way market (no margin).
    margin = overround([2.0, 2.0])
    assert margin == pytest.approx(0.0)
