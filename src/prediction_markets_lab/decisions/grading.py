"""Opportunity grading: A+, A, B, C, or Reject.

Implements the grading thresholds from project instructions section 10.
Grading is threshold-based and deterministic — no subjective adjustment
is permitted. All thresholds are configuration-driven (see
config/thresholds.yaml) and passed in explicitly rather than hard-coded,
per project coding standards (section 20).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Grade = Literal["A+", "A", "B", "C", "Reject"]


@dataclass(frozen=True)
class GradingThresholds:
    """Configurable thresholds for each grade tier.

    Mirrors config/thresholds.yaml.
    """

    a_plus_min_net_ev: float = 0.08
    a_plus_min_edge_pp: float = 4.0
    a_plus_min_bookmakers: int = 5

    a_min_net_ev: float = 0.05
    a_min_edge_pp: float = 3.0
    a_min_bookmakers: int = 4

    b_min_net_ev: float = 0.02
    c_min_net_ev: float = 0.00

    def __post_init__(self) -> None:
        if self.a_plus_min_net_ev < self.a_min_net_ev:
            raise ValueError("A+ net EV threshold must be >= A threshold")
        if self.a_plus_min_edge_pp < self.a_min_edge_pp:
            raise ValueError("A+ edge threshold must be >= A threshold")
        if self.a_plus_min_bookmakers < self.a_min_bookmakers:
            raise ValueError("A+ bookmaker count threshold must be >= A threshold")
        if self.b_min_net_ev < self.c_min_net_ev:
            raise ValueError("Grade B net EV threshold must be >= Grade C threshold")


@dataclass(frozen=True)
class GradingInput:
    """All evidence required to grade a single opportunity.

    data_quality_ok, no_material_info_risk, exchange_price_current, and
    market_rules_match are boolean gates: any False value on its own can
    prevent A+ or A regardless of numeric EV/edge, per section 10 and the
    safety/failure conditions in section 21.
    """

    net_ev: float
    probability_edge_pp: float
    bookmaker_count: int
    data_quality_ok: bool
    no_material_info_risk: bool
    exchange_price_current: bool
    market_rules_match: bool
    liquidity_adequate: bool


@dataclass(frozen=True)
class GradingResult:
    """The outcome of grading a single opportunity."""

    grade: Grade
    reason: str


def grade_opportunity(
    evidence: GradingInput, thresholds: GradingThresholds
) -> GradingResult:
    """Assign a grade (A+, A, B, C, or Reject) to a single opportunity.

    Args:
        evidence: All numeric and boolean evidence for this opportunity.
        thresholds: The configured grading thresholds to apply.

    Returns:
        A GradingResult containing the grade and a human-readable reason.
    """
    # Hard safety gates: any failure here blocks a live-trade grade,
    # regardless of how strong the EV/edge numbers look. See section 21.
    if not evidence.exchange_price_current:
        return GradingResult("Reject", "exchange price is not current/stale")
    if not evidence.market_rules_match:
        return GradingResult("Reject", "bookmaker and exchange market rules do not match")
    if not evidence.liquidity_adequate:
        return GradingResult("Reject", "exchange liquidity is insufficient")
    if not evidence.data_quality_ok:
        return GradingResult("Reject", "data quality is insufficient")

    if evidence.net_ev < thresholds.c_min_net_ev:
        return GradingResult(
            "Reject", f"net EV {evidence.net_ev:.2%} is below the minimum Grade C floor"
        )
    if evidence.net_ev < thresholds.b_min_net_ev:
        return GradingResult(
            "C", f"net EV {evidence.net_ev:.2%} is below Grade B threshold; watchlist only"
        )

    is_a_plus_eligible = (
        evidence.net_ev >= thresholds.a_plus_min_net_ev
        and evidence.probability_edge_pp >= thresholds.a_plus_min_edge_pp
        and evidence.bookmaker_count >= thresholds.a_plus_min_bookmakers
        and evidence.no_material_info_risk
    )
    if is_a_plus_eligible:
        return GradingResult("A+", "meets all Grade A+ thresholds and safety gates")

    is_a_eligible = (
        evidence.net_ev >= thresholds.a_min_net_ev
        and evidence.probability_edge_pp >= thresholds.a_min_edge_pp
        and evidence.bookmaker_count >= thresholds.a_min_bookmakers
        and evidence.no_material_info_risk
    )
    if is_a_eligible:
        return GradingResult("A", "meets all Grade A thresholds and safety gates")

    # Passed the B floor but not A: either numeric shortfall or unresolved
    # info risk keeps it to paper-trade-only.
    if not evidence.no_material_info_risk:
        return GradingResult(
            "B", "net EV/edge sufficient but unresolved material information risk exists"
        )
    return GradingResult(
        "B", "net EV/edge below Grade A thresholds; paper trade only"
    )
