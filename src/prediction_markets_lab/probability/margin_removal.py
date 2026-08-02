"""Remove bookmaker margin (overround) from raw implied probabilities.

V1 implements the proportional (basic) margin-removal method only:

    p_i = q_i / sum(q_j)

Alternative methods (Shin, power, odds-ratio) are documented as future
work in docs/PROBABILITY_METHODOLOGY.md and must not be used without
separate validation, per project instructions section 8.
"""

from __future__ import annotations

from typing import Sequence


def proportional_margin_removal(raw_probabilities: Sequence[float]) -> list[float]:
    """Remove margin proportionally so probabilities sum to 1.0.

    This is the V1 default margin-removal method. It divides each raw
    implied probability by the sum of all raw implied probabilities in
    the market.

    Args:
        raw_probabilities: Raw implied probabilities (q_i) for every
            outcome in a single market, typically produced by
            odds_conversion.decimal_odds_list_to_implied_probabilities.

    Returns:
        A list of margin-free probabilities (p_i) summing to 1.0, in the
        same order as the input.

    Raises:
        ValueError: If raw_probabilities is empty, contains a
            non-positive value, or sums to zero.
    """
    if not raw_probabilities:
        raise ValueError("raw_probabilities must contain at least one value")
    if any(p <= 0 for p in raw_probabilities):
        raise ValueError("all raw_probabilities must be strictly positive")

    total = sum(raw_probabilities)
    if total <= 0:
        raise ValueError("sum of raw_probabilities must be positive")

    return [p / total for p in raw_probabilities]


def margin_free_probabilities_from_odds(decimal_odds: Sequence[float]) -> list[float]:
    """Convenience wrapper: decimal odds straight to margin-free probabilities.

    Args:
        decimal_odds: Decimal odds for every outcome in a single market.

    Returns:
        Margin-free probabilities (p_i) summing to 1.0.
    """
    from prediction_markets_lab.probability.odds_conversion import (
        decimal_odds_list_to_implied_probabilities,
    )

    raw = decimal_odds_list_to_implied_probabilities(decimal_odds)
    return proportional_margin_removal(raw)
