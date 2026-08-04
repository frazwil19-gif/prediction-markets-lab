import pytest

from prediction_markets_lab.ingestion.schema_validation import validate_market_odds


def test_valid_football_market():
    result = validate_market_odds([2.10, 3.40, 3.60], expected_outcome_count=3)
    assert result.valid
    assert result.reason is None


def test_rejects_wrong_outcome_count():
    result = validate_market_odds([2.10, 3.40], expected_outcome_count=3)
    assert not result.valid
    assert "expected 3 outcomes" in result.reason


def test_rejects_odds_at_or_below_one():
    result = validate_market_odds([1.0, 3.40, 3.60], expected_outcome_count=3)
    assert not result.valid


def test_rejects_implausibly_high_overround():
    # Deliberately absurd odds implying a huge margin.
    result = validate_market_odds([1.05, 1.05, 1.05], expected_outcome_count=3)
    assert not result.valid
    assert "overround" in result.reason


def test_accepts_two_way_tennis_market():
    result = validate_market_odds([1.85, 2.05], expected_outcome_count=2)
    assert result.valid
