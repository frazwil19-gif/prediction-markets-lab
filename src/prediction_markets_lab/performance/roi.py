"""ROI and yield calculations from settled bets.

Filled in 2026-09-20 (Production Infrastructure Build, Section 3/8) --
previously a Stage 1 placeholder deliberately deferred until there was
real settled-bet history to compute this from (see docs/ROADMAP.md).
Both "ROI" and "yield" are used interchangeably in betting-performance
reporting to mean the same ratio: net profit divided by total staked.
This module keeps a single implementation (roi_fraction) rather than two
near-duplicate functions, since the project's engineering standards
disfavour redundant logic.
"""

from __future__ import annotations


def roi_fraction(total_staked_gbp: float, total_profit_gbp: float) -> float | None:
    """Return net profit / total staked, or None if nothing was staked.

    Args:
        total_staked_gbp: Sum of stakes across every settled bet in scope
            (void bets' stakes are conventionally still counted as
            staked, per standard ROI/yield reporting -- callers should
            include void bets' stakes here if that is the desired
            convention, or exclude them beforehand if not).
        total_profit_gbp: Net profit (can be negative) across the same
            set of bets.

    Returns:
        The ROI/yield as a fraction (e.g. 0.05 = +5%), or None if
        total_staked_gbp is 0 -- there is nothing to divide by, and
        returning 0.0 would misleadingly read as "broke even" rather
        than "no data."
    """
    if total_staked_gbp == 0:
        return None
    return total_profit_gbp / total_staked_gbp
