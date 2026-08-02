"""Convert decimal odds into raw (overround-inclusive) implied probabilities.

These functions perform no margin removal. They are the first step in the
probability pipeline: raw implied probability -> margin removal -> consensus.
"""

from __future__ import annotations

from typing import Sequence


def decimal_odds_to_implied_probability(decimal_odds: float) -> float:
    """Convert a single decimal odds value into a raw implied probability.

    Args:
        decimal_odds: Decimal (European) odds, e.g. 2.50. Must be > 1.0.

    Returns:
        The raw implied probability q_i = 1 / O_i, before margin removal.

    Raises:
        ValueError: If decimal_odds is not greater than 1.0.
    """
    if decimal_odds <= 1.0:
        raise ValueError(
            f"decimal_odds must be greater than 1.0, got {decimal_odds!r}"
        )
    return 1.0 / decimal_odds


def decimal_odds_list_to_implied_probabilities(
    decimal_odds: Sequence[float],
) -> list[float]:
    """Convert a sequence of decimal odds into raw implied probabilities.

    Args:
        decimal_odds: Sequence of decimal odds for each outcome in a market.

    Returns:
        A list of raw implied probabilities, one per outcome, in the same
        order as the input. These will sum to more than 1.0 for any market
        with a positive bookmaker margin (overround).

    Raises:
        ValueError: If decimal_odds is empty, or any value is not > 1.0.
    """
    if not decimal_odds:
        raise ValueError("decimal_odds must contain at least one value")
    return [decimal_odds_to_implied_probability(o) for o in decimal_odds]


def overround(decimal_odds: Sequence[float]) -> float:
    """Calculate the bookmaker overround (total margin) for a market.

    Args:
        decimal_odds: Decimal odds for every outcome in a single market.

    Returns:
        The sum of raw implied probabilities minus 1.0. A value of 0.05
        means a 5% overround (bookmaker margin).
    """
    probabilities = decimal_odds_list_to_implied_probabilities(decimal_odds)
    return sum(probabilities) - 1.0
