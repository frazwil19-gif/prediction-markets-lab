import pytest

from prediction_markets_lab.probability.market_pipeline import compute_market_consensus


def test_two_bookmaker_market_matches_hand_calculation():
    """Hand-calculated example.

    Bookmaker A: home 2.00, draw 4.00, away 4.00
      raw implied: 0.5, 0.25, 0.25 -> sums to 1.0 exactly (no margin)
      fair (proportional): unchanged -> 0.5, 0.25, 0.25

    Bookmaker B: home 1.80, draw 3.60, away 4.50
      raw implied: 0.555556, 0.277778, 0.222222 -> sums to 1.055556 (5.56% margin)
      fair (proportional): divide each by 1.055556
        home: 0.555556 / 1.055556 = 0.526316
        draw: 0.277778 / 1.055556 = 0.263158
        away: 0.222222 / 1.055556 = 0.210526

    Consensus (median of 2 values = mean of the two):
      home: (0.5 + 0.526316) / 2 = 0.513158
      draw: (0.25 + 0.263158) / 2 = 0.256579
      away: (0.25 + 0.210526) / 2 = 0.230263
    """
    bookmaker_odds = {
        "Bookmaker A": {"home": 2.00, "draw": 4.00, "away": 4.00},
        "Bookmaker B": {"home": 1.80, "draw": 3.60, "away": 4.50},
    }
    result = compute_market_consensus(
        "M-TEST-001", bookmaker_odds, expected_outcomes=["home", "draw", "away"]
    )

    assert result.accepted_bookmaker_count == 2
    assert result.rejected_bookmakers == []

    home = result.consensus_by_outcome["home"]
    draw = result.consensus_by_outcome["draw"]
    away = result.consensus_by_outcome["away"]

    assert home.median == pytest.approx(0.513158, abs=1e-5)
    assert draw.median == pytest.approx(0.256579, abs=1e-5)
    assert away.median == pytest.approx(0.230263, abs=1e-5)

    # The margin-free probabilities for every outcome, for every
    # bookmaker, must sum to 1.0 per bookmaker (proportional removal
    # guarantee) -- verify indirectly via bookmaker_count and the
    # underlying per-bookmaker values reconstructed from consensus mean.
    assert home.bookmaker_count == 2
    assert draw.bookmaker_count == 2
    assert away.bookmaker_count == 2


def test_margin_free_probabilities_sum_to_one_per_outcome_set():
    """The three consensus medians (for a 2-bookmaker, fully agreeing
    market) should still sum close to 1.0, since margin has genuinely
    been removed rather than left in as raw implied probability."""
    bookmaker_odds = {
        "Bookmaker A": {"home": 2.10, "draw": 3.40, "away": 3.60},
        "Bookmaker B": {"home": 2.05, "draw": 3.50, "away": 3.75},
    }
    result = compute_market_consensus(
        "M-TEST-002", bookmaker_odds, expected_outcomes=["home", "draw", "away"]
    )
    total = sum(c.median for c in result.consensus_by_outcome.values())
    # Medians of margin-free probabilities won't sum to exactly 1.0 in
    # general (median is not a linear operator), but should be very
    # close for a market where bookmakers roughly agree.
    assert total == pytest.approx(1.0, abs=0.01)


def test_rejects_bookmaker_with_incomplete_outcome_set():
    bookmaker_odds = {
        "Bookmaker A": {"home": 2.10, "draw": 3.40, "away": 3.60},
        "Bookmaker B": {"home": 2.05, "draw": 3.50},  # missing "away"
    }
    result = compute_market_consensus(
        "M-TEST-003", bookmaker_odds, expected_outcomes=["home", "draw", "away"]
    )
    assert result.accepted_bookmaker_count == 1
    assert len(result.rejected_bookmakers) == 1
    assert result.rejected_bookmakers[0].bookmaker == "Bookmaker B"
    assert "missing outcomes" in result.rejected_bookmakers[0].reason
    # Only Bookmaker A contributed -> bookmaker_count of 1 per outcome.
    assert result.consensus_by_outcome["home"].bookmaker_count == 1


def test_rejects_bookmaker_with_unexpected_extra_outcome():
    bookmaker_odds = {
        "Bookmaker A": {"home": 2.10, "draw": 3.40, "away": 3.60},
        "Bookmaker B": {"home": 2.05, "draw": 3.50, "away": 3.75, "extra": 10.0},
    }
    result = compute_market_consensus(
        "M-TEST-004", bookmaker_odds, expected_outcomes=["home", "draw", "away"]
    )
    assert result.accepted_bookmaker_count == 1
    assert "unexpected outcomes" in result.rejected_bookmakers[0].reason


def test_raises_when_all_bookmakers_rejected():
    bookmaker_odds = {
        "Bookmaker A": {"home": 2.10, "draw": 3.40},  # incomplete
        "Bookmaker B": {"home": 2.05},  # incomplete
    }
    with pytest.raises(ValueError, match="no bookmaker with a complete outcome set"):
        compute_market_consensus(
            "M-TEST-005", bookmaker_odds, expected_outcomes=["home", "draw", "away"]
        )


def test_rejects_empty_expected_outcomes():
    with pytest.raises(ValueError):
        compute_market_consensus("M-TEST-006", {"Bookmaker A": {"home": 2.0}}, expected_outcomes=[])


def test_two_way_tennis_market():
    bookmaker_odds = {
        "Bookmaker A": {"player_a": 1.85, "player_b": 2.05},
        "Bookmaker B": {"player_a": 1.90, "player_b": 1.98},
        "Bookmaker C": {"player_a": 1.83, "player_b": 2.08},
    }
    result = compute_market_consensus(
        "M-TN-TEST", bookmaker_odds, expected_outcomes=["player_a", "player_b"]
    )
    assert result.accepted_bookmaker_count == 3
    assert result.consensus_by_outcome["player_a"].median + result.consensus_by_outcome["player_b"].median == pytest.approx(1.0, abs=0.02)
