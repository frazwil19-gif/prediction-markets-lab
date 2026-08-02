"""Expected value calculations for exchange back bets.

For a GBP 1 back bet at decimal odds O, estimated probability p, and
exchange commission c (charged on net winnings only, as on Betfair and
Smarkets):

    EV = p * (O - 1) * (1 - c) - (1 - p)

This module keeps probability edge, expected value, and profit strictly
separate, per project instructions section 9. It does not calculate
realised profit; see performance/roi.py (future stage) for that.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedValueResult:
    """Full EV breakdown for a single candidate bet, per unit stake."""

    probability: float
    decimal_odds: float
    commission: float
    exchange_implied_probability: float
    gross_ev: float
    net_ev: float
    expected_roi: float
    break_even_probability: float
    probability_edge_pp: float
    edge_relative_to_market: float


def gross_expected_value(probability: float, decimal_odds: float) -> float:
    """Expected value per unit stake with no commission applied.

    Args:
        probability: Estimated (final) probability the selection wins,
            strictly between 0 and 1.
        decimal_odds: Decimal odds offered, must be > 1.0.

    Returns:
        Gross EV per unit stake: p * (O - 1) - (1 - p).
    """
    _validate_probability(probability)
    _validate_odds(decimal_odds)
    return probability * (decimal_odds - 1.0) - (1.0 - probability)


def net_expected_value(
    probability: float, decimal_odds: float, commission: float
) -> float:
    """Commission-adjusted expected value per unit stake.

    Args:
        probability: Estimated (final) probability the selection wins,
            strictly between 0 and 1.
        decimal_odds: Decimal odds offered, must be > 1.0.
        commission: Exchange commission rate charged on net winnings,
            e.g. 0.02 for 2%. Must be in [0, 1).

    Returns:
        Net EV per unit stake: p * (O - 1) * (1 - c) - (1 - p).
    """
    _validate_probability(probability)
    _validate_odds(decimal_odds)
    _validate_commission(commission)
    return probability * (decimal_odds - 1.0) * (1.0 - commission) - (1.0 - probability)


def break_even_probability(decimal_odds: float, commission: float) -> float:
    """The probability at which net EV is exactly zero for given odds and commission.

    Solves 0 = p * (O - 1) * (1 - c) - (1 - p) for p.

    Args:
        decimal_odds: Decimal odds offered, must be > 1.0.
        commission: Exchange commission rate, in [0, 1).

    Returns:
        The break-even probability.
    """
    _validate_odds(decimal_odds)
    _validate_commission(commission)
    numerator = 1.0
    denominator = (decimal_odds - 1.0) * (1.0 - commission) + 1.0
    return numerator / denominator


def probability_edge(estimated_probability: float, market_probability: float) -> float:
    """Edge in percentage points between estimated and market probability.

    Args:
        estimated_probability: The model/final probability estimate.
        market_probability: The exchange implied (or consensus) probability
            being compared against.

    Returns:
        (estimated_probability - market_probability) * 100, in percentage
        points. Positive means the estimate is more favourable than the
        market price implies.
    """
    _validate_probability(estimated_probability)
    _validate_probability(market_probability)
    return (estimated_probability - market_probability) * 100.0


def edge_relative_to_market(
    estimated_probability: float, market_probability: float
) -> float:
    """Edge as a proportion of the market probability (relative edge).

    Args:
        estimated_probability: The model/final probability estimate.
        market_probability: The exchange implied probability.

    Returns:
        (estimated_probability - market_probability) / market_probability.

    Raises:
        ValueError: If market_probability is not strictly positive.
    """
    _validate_probability(estimated_probability)
    _validate_probability(market_probability)
    if market_probability <= 0:
        raise ValueError("market_probability must be strictly positive")
    return (estimated_probability - market_probability) / market_probability


def evaluate(
    probability: float,
    decimal_odds: float,
    commission: float,
) -> ExpectedValueResult:
    """Produce the full EV breakdown for a single candidate bet.

    Args:
        probability: Estimated (final) probability the selection wins.
        decimal_odds: Decimal odds offered by the exchange, must be > 1.0.
        commission: Exchange commission rate, in [0, 1).

    Returns:
        An ExpectedValueResult with gross EV, net EV, expected ROI,
        exchange implied probability, break-even probability, probability
        edge (percentage points) and relative edge.
    """
    _validate_probability(probability)
    _validate_odds(decimal_odds)
    _validate_commission(commission)

    exchange_implied = 1.0 / decimal_odds
    gross_ev = gross_expected_value(probability, decimal_odds)
    net_ev = net_expected_value(probability, decimal_odds, commission)
    # Expected ROI is net EV per unit stake, expressed as a percentage.
    expected_roi = net_ev * 100.0
    break_even = break_even_probability(decimal_odds, commission)
    edge_pp = probability_edge(probability, exchange_implied)
    relative_edge = edge_relative_to_market(probability, exchange_implied)

    return ExpectedValueResult(
        probability=probability,
        decimal_odds=decimal_odds,
        commission=commission,
        exchange_implied_probability=exchange_implied,
        gross_ev=gross_ev,
        net_ev=net_ev,
        expected_roi=expected_roi,
        break_even_probability=break_even,
        probability_edge_pp=edge_pp,
        edge_relative_to_market=relative_edge,
    )


def _validate_probability(p: float) -> None:
    if not (0.0 < p < 1.0):
        raise ValueError(f"probability must be strictly between 0 and 1, got {p!r}")


def _validate_odds(o: float) -> None:
    if o <= 1.0:
        raise ValueError(f"decimal_odds must be greater than 1.0, got {o!r}")


def _validate_commission(c: float) -> None:
    if not (0.0 <= c < 1.0):
        raise ValueError(f"commission must be in [0, 1), got {c!r}")
