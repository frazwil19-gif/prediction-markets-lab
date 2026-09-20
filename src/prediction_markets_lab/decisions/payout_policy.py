"""Payout / minimum-odds policy (Section 3, "MAJOR NEXT PHASE -- PRODUCTION
INFRASTRUCTURE BUILD" instruction, 2026-09-20).

The project's objective was never maximum probability alone: "We do NOT
want the card dominated by 1.05-1.15 selections where a GBP2 stake earns
pennies." This module implements a configurable payout floor that demotes
an otherwise-actionable grade (A+/A/B) to Grade C ("watch") when the price
is below a configured minimum -- it never rejects the candidate outright
(the underlying probability/EV read may still be correct and worth
tracking), and it never touches decisions.grading's own tested thresholds
or logic (KEEP, not rewritten -- see the production-infrastructure audit).

The initial floor values (1.33 decimal / 1/3 fractional as the normal
minimum, 1.40-2.50 as the preferred research range) are the operator's own
stated starting point, explicitly NOT assumed optimal -- they are
configuration (config/thresholds.yaml's payout_policy section), and
performance/odds_bands.py exists specifically so paper-trading and
backtest evidence can challenge them later.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PayoutPolicyThresholds:
    """Configurable payout-floor thresholds. Mirrors config/thresholds.yaml's payout_policy section."""

    normal_min_decimal_odds: float = 1.33
    preferred_min_decimal_odds: float = 1.40
    preferred_max_decimal_odds: float = 2.50

    def __post_init__(self) -> None:
        if self.normal_min_decimal_odds <= 1.0:
            raise ValueError("normal_min_decimal_odds must be > 1.0")
        if self.preferred_min_decimal_odds < self.normal_min_decimal_odds:
            raise ValueError("preferred_min_decimal_odds cannot be below normal_min_decimal_odds")
        if self.preferred_max_decimal_odds < self.preferred_min_decimal_odds:
            raise ValueError("preferred_max_decimal_odds cannot be below preferred_min_decimal_odds")


ACTIONABLE_GRADES = frozenset({"A+", "A", "B"})


def apply_payout_floor(
    grade: str, decision_reason: str, decimal_odds: float, thresholds: PayoutPolicyThresholds
) -> tuple[str, str]:
    """Demote an otherwise-actionable grade to 'C' if odds are below the normal floor.

    Args:
        grade: The grade decisions.grading.grade_opportunity already assigned.
        decision_reason: That grade's existing reason string, extended (not
            replaced) so the demotion is visible in the audit trail rather
            than silently overwriting the original grading rationale.
        decimal_odds: The best currently-obtainable price for this selection.
        thresholds: The active PayoutPolicyThresholds.

    Returns:
        (possibly-demoted grade, possibly-extended reason). Reject and C
        are never changed by this function -- there is nothing to demote
        a non-actionable grade to, and demoting Reject to C would be a
        promotion, which this function must never do.
    """
    if grade not in ACTIONABLE_GRADES:
        return grade, decision_reason
    if decimal_odds >= thresholds.normal_min_decimal_odds:
        return grade, decision_reason
    demoted_reason = (
        f"{decision_reason}; demoted from {grade} to C -- odds {decimal_odds:.2f} are below the "
        f"configured payout floor of {thresholds.normal_min_decimal_odds:.2f} (see "
        "config/thresholds.yaml's payout_policy section)"
    )
    return "C", demoted_reason
