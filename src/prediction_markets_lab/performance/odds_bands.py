"""Odds-band bucketing for performance tracking (Section 3, Production
Infrastructure Build, 2026-09-20).

"Track performance by odds bands... The purpose is to discover where the
best combination of probability, confidence, payout, value and risk
actually exists." This module defines the operator's own suggested bands
as configuration-adjacent constants (not magic numbers scattered across
call sites) and a single lookup function every performance report uses,
so the band boundaries are defined exactly once.
"""

from __future__ import annotations

# (label, inclusive lower bound, exclusive upper bound -- except the final
# band, which has no upper bound).
ODDS_BANDS: tuple[tuple[str, float, float], ...] = (
    ("1.01-1.19", 1.01, 1.20),
    ("1.20-1.32", 1.20, 1.33),
    ("1.33-1.49", 1.33, 1.50),
    ("1.50-1.74", 1.50, 1.75),
    ("1.75-1.99", 1.75, 2.00),
    ("2.00-2.49", 2.00, 2.50),
    ("2.50+", 2.50, float("inf")),
)


def band_for_odds(decimal_odds: float) -> str:
    """Return the odds-band label a given decimal price falls into.

    Args:
        decimal_odds: A decimal price, expected to be > 1.0.

    Returns:
        The matching band label from ODDS_BANDS.

    Raises:
        ValueError: If decimal_odds is below the first band's lower bound
            (1.01) -- an odds value this low should never reach a
            performance report; surfacing it loudly here is preferable to
            silently mis-bucketing it.
    """
    if decimal_odds < 1.01:
        raise ValueError(f"decimal_odds {decimal_odds!r} is below the lowest defined band (1.01)")
    for label, low, high in ODDS_BANDS:
        if low <= decimal_odds < high:
            return label
    return ODDS_BANDS[-1][0]
