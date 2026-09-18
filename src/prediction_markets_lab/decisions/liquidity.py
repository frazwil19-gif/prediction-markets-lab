"""Liquidity assessment for opportunities.

V1 implementation (2026-09-18, Daily Engine V1 build). The original
Stage-1 placeholder assumed an exchange order book (Betfair/Smarkets)
would always be the price source, with a human checking depth manually.
The V1 price source is a fixed-odds bookmaker (see
docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md), which publishes
no order book at all -- a bookmaker accepting a stake of a few pounds on
a mainstream fixture is not a liquidity risk the way an exchange's
back/lay ladder can be. This module defaults to "adequate" for a
bookmaker price and only applies a real depth check when an
exchange-style `available_size_gbp` figure is actually supplied (e.g.
from templates/exchange_price_entry.csv, still usable for a genuine
exchange price), preserving the original exchange-liquidity check for
when it is actually relevant.
"""

from __future__ import annotations


def assess_liquidity(stake_gbp: float, available_size_gbp: float | None = None) -> bool:
    """Check whether the required stake can plausibly be placed.

    Args:
        stake_gbp: The stake this recommendation would require.
        available_size_gbp: Available depth at the quoted price, if the
            price source is an exchange order book. None (the default)
            for a fixed-odds bookmaker quote, which publishes no such
            figure.

    Returns:
        True if the stake can plausibly be placed at the quoted price.
        For a fixed-odds bookmaker (available_size_gbp is None), always
        True at V1's very small stake sizes. For an exchange price, True
        only if available_size_gbp covers stake_gbp.

    Raises:
        ValueError: If stake_gbp is not positive, or available_size_gbp
            is provided but negative.
    """
    if stake_gbp <= 0:
        raise ValueError("stake_gbp must be positive")
    if available_size_gbp is None:
        return True
    if available_size_gbp < 0:
        raise ValueError("available_size_gbp must be non-negative")
    return available_size_gbp >= stake_gbp
