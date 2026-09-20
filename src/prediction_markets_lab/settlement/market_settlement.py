"""Deterministic market settlement logic (Section 7, Production
Infrastructure Build, 2026-09-20).

Pure functions only -- no I/O, no ledger mutation -- so they are trivial
to unit test and safe to reuse from both the live paper-ledger settlement
runner (settle_paper_ledger.py) and a future historical backtest replay
(both need "given a final score, what is the settlement outcome and
profit/loss for this specific selection").
"""

from __future__ import annotations

# A settlement outcome is one of: the exact selection string that won
# ("home"/"draw"/"away"/"over"/"under"), or "void" (postponed/abandoned/
# no usable score, or a genuine push -- see determine_over_under_result).
# It is NEVER a guess: a market_type this module does not recognise
# raises rather than silently returning "void".

SUPPORTED_MARKET_TYPES = frozenset({"1x2", "over_under_2_5"})


def determine_1x2_result(home_score: int | None, away_score: int | None) -> str:
    """Return "home", "draw", "away", or "void" (missing/unusable score)."""
    if home_score is None or away_score is None:
        return "void"
    if home_score > away_score:
        return "home"
    if away_score > home_score:
        return "away"
    return "draw"


def determine_over_under_result(
    home_score: int | None, away_score: int | None, line: float = 2.5
) -> str:
    """Return "over", "under", or "void" (missing score, or an exact push).

    An exact push can only happen if `line` is a whole number (e.g. 3.0)
    -- V1's configured line is 2.5, an impossible total-goals count, so a
    push is not expected in practice, but the check is not removed:
    silently mis-settling a push as a win or loss would be worse than a
    rare, correctly-handled void.
    """
    if home_score is None or away_score is None:
        return "void"
    total = home_score + away_score
    if total > line:
        return "over"
    if total < line:
        return "under"
    return "void"  # exact push


def determine_result(market_type: str, home_score: int | None, away_score: int | None) -> str:
    """Dispatch to the correct settlement function for a given market_type.

    Raises:
        ValueError: If market_type is not one this module knows how to
            settle -- never silently returns "void" for an unsupported
            market, which would be indistinguishable from a genuine
            postponement.
    """
    if market_type == "1x2":
        return determine_1x2_result(home_score, away_score)
    if market_type == "over_under_2_5":
        return determine_over_under_result(home_score, away_score, line=2.5)
    raise ValueError(
        f"market_type {market_type!r} is not supported by market_settlement "
        f"(supported: {sorted(SUPPORTED_MARKET_TYPES)})"
    )


def compute_pnl_gbp(stake_gbp: float, quoted_odds: float, selection: str, winning_selection: str) -> float:
    """Profit/loss in GBP for one settled bet.

    Args:
        stake_gbp: The stake actually recommended/placed.
        quoted_odds: The decimal odds the bet was recorded at.
        selection: The selection this bet was on (e.g. "home").
        winning_selection: The outcome of determine_result -- either the
            winning selection string, or "void".

    Returns:
        stake_gbp * (quoted_odds - 1) if selection == winning_selection,
        -stake_gbp if it lost, or 0.0 if winning_selection is "void"
        (stake is conventionally returned in full on a void/push).
    """
    if winning_selection == "void":
        return 0.0
    if selection == winning_selection:
        return stake_gbp * (quoted_odds - 1.0)
    return -stake_gbp
