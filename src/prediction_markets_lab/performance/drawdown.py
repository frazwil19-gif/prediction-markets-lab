"""Drawdown and losing-streak reporting over a sequence of settled bets.

Filled in 2026-09-20 (Production Infrastructure Build, Section 3/8/4) --
previously a Stage 1 placeholder (see docs/ROADMAP.md). Used by both the
live paper/real performance reports and the historical backtest replay,
so the same drawdown definition applies everywhere in this project.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrawdownReport:
    """Drawdown diagnostics over one bankroll curve."""

    max_drawdown_gbp: float
    max_drawdown_pct: float
    ending_balance_gbp: float
    peak_balance_gbp: float


def bankroll_curve(starting_balance_gbp: float, pnl_sequence: list[float]) -> list[float]:
    """Return the running bankroll after each pnl in sequence order.

    Args:
        starting_balance_gbp: Bankroll before the first bet in the sequence.
        pnl_sequence: Net profit/loss for each settled bet, in
            chronological order (void bets should contribute 0.0, not be
            omitted, so the sequence stays aligned with any parallel list
            of bet metadata a caller is tracking).

    Returns:
        A list the same length as pnl_sequence: the bankroll balance
        immediately after each entry. Does NOT include the starting
        balance itself as a leading entry.
    """
    curve: list[float] = []
    running = starting_balance_gbp
    for pnl in pnl_sequence:
        running += pnl
        curve.append(running)
    return curve


def compute_drawdown(starting_balance_gbp: float, pnl_sequence: list[float]) -> DrawdownReport:
    """Compute max drawdown (absolute and percentage) over a pnl sequence.

    Args:
        starting_balance_gbp: Bankroll before the first bet.
        pnl_sequence: Net profit/loss for each settled bet, in
            chronological order.

    Returns:
        A DrawdownReport. If pnl_sequence is empty, max_drawdown_gbp and
        max_drawdown_pct are both 0.0, and ending/peak balance both equal
        starting_balance_gbp.
    """
    curve = [starting_balance_gbp] + bankroll_curve(starting_balance_gbp, pnl_sequence)
    peak = curve[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for balance in curve:
        peak = max(peak, balance)
        dd = peak - balance
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak) if peak > 0 else 0.0
    return DrawdownReport(
        max_drawdown_gbp=max_dd,
        max_drawdown_pct=max_dd_pct,
        ending_balance_gbp=curve[-1],
        peak_balance_gbp=peak,
    )


def longest_losing_streak(results: list[str], loss_label: str = "lost") -> int:
    """Longest run of consecutive losing results, in sequence order.

    Args:
        results: A result string per settled bet, in chronological order
            (e.g. "won"/"lost"/"void").
        loss_label: The result string that counts as a loss. Any other
            value (including "void") breaks a streak without extending
            it -- a push/void is neither a win nor a loss.

    Returns:
        The longest consecutive run of loss_label entries. 0 if results
        is empty or contains no losses.
    """
    longest = 0
    current = 0
    for result in results:
        if result == loss_label:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest
