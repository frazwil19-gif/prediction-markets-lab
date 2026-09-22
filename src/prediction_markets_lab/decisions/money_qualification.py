"""Real-money qualification gate (TARGETED PRODUCTION CHANGE -- DAILY MONEY
WINDOW + MONEY/PAPER SEPARATION instruction, 2026-09-22).

This is a NEW, deterministic layer downstream of the existing A+/A/B/C/
Reject research grade (decisions/grading.py, unchanged, KEEP) and the
existing payout floor (decisions/payout_policy.py, unchanged, KEEP). It
never re-implements or loosens either of those -- it only decides, given
an already-graded candidate, whether it also clears the stricter,
separate bar for a REAL-MONEY recommendation on the actionable Daily
Money Card.

Why this exists, in the operator's own words: "The backend may
investigate a broad candidate universe. The money strategy should be
selective. Do not confuse 'interesting research bet' with 'bet Fraser
should actually place.'" Two real examples from the first live card are
exactly what this gate exists to keep off the money card while still
letting them stand as legitimate research/paper candidates: Ipswich (a)
v Manchester City at 14.00 (~7.8% estimated probability), and Leeds (a)
v Arsenal at 10.00 (~10.9%) -- both genuinely graded B/C candidates by
the existing engine, neither is what Fraser wants to risk money on.

Gate order (all are checked; every failure is recorded, not just the
first -- "do not silently discard candidates"):

    kickoff inside the configured money-event horizon?
    -> research grade actionable (A+/A/B)?
    -> confidence eligible ("High" outright, "Medium" only if every
       other requirement below is also strong)?
    -> mechanical data quality ok?
    -> estimated probability at/above the (confidence-dependent) floor?
    -> odds at/above the existing payout floor (and, for a Medium-
       confidence candidate, inside the existing preferred payout
       range)?
    -> net EV at/above the (confidence-dependent) value floor?

Every threshold here is the operator's own initial, explicitly-NOT-
assumed-optimal starting configuration (config/thresholds.yaml's
money_qualification section) -- evidence from paper trading and the
historical backtest should challenge these over time, tracked
prospectively by probability/odds band, never hand-tuned on a handful of
results. This module makes no attempt to be "smart" about which
rejection reason is most important; every failing check is recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from prediction_markets_lab.decisions.payout_policy import PayoutPolicyThresholds

MoneyDecision = Literal["BET", "WATCH", "PAPER_ONLY", "REJECT"]

# Mirrors decisions/payout_policy.py's own ACTIONABLE_GRADES -- a money bet
# can never be considered for a candidate the research engine itself did
# not consider actionable in the first place.
ACTIONABLE_RESEARCH_GRADES = frozenset({"A+", "A", "B"})


@dataclass(frozen=True)
class MoneyQualificationThresholds:
    """Configurable money-qualification thresholds. Mirrors
    config/thresholds.yaml's money_qualification section."""

    event_horizon_hours: float = 24.0
    min_probability: float = 0.50
    min_probability_medium_confidence: float = 0.60
    min_net_ev: float = 0.02
    min_net_ev_medium_confidence: float = 0.05
    eligible_confidence_labels: frozenset[str] = field(default_factory=lambda: frozenset({"High"}))
    conditional_confidence_labels: frozenset[str] = field(default_factory=lambda: frozenset({"Medium"}))
    require_preferred_odds_band_for_conditional_confidence: bool = True

    def __post_init__(self) -> None:
        if self.event_horizon_hours <= 0:
            raise ValueError("event_horizon_hours must be positive")
        if not (0.0 < self.min_probability < 1.0):
            raise ValueError("min_probability must be strictly between 0 and 1")
        if not (0.0 < self.min_probability_medium_confidence < 1.0):
            raise ValueError("min_probability_medium_confidence must be strictly between 0 and 1")
        if self.min_probability_medium_confidence < self.min_probability:
            raise ValueError(
                "min_probability_medium_confidence must be >= min_probability "
                "(Medium confidence requires a STRICTER, not looser, floor)"
            )
        if self.min_net_ev_medium_confidence < self.min_net_ev:
            raise ValueError(
                "min_net_ev_medium_confidence must be >= min_net_ev "
                "(Medium confidence requires a STRICTER, not looser, floor)"
            )
        if self.eligible_confidence_labels & self.conditional_confidence_labels:
            raise ValueError(
                "eligible_confidence_labels and conditional_confidence_labels must not overlap"
            )


@dataclass(frozen=True)
class MoneyQualificationResult:
    """The outcome of the money-qualification gate for one candidate."""

    money_qualified: bool
    money_decision: MoneyDecision
    money_rejection_reasons: list[str]


def _parse_iso_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, tolerating a trailing 'Z' (The Odds
    API's own format) and a naive timestamp (assumed UTC -- every
    timestamp this project generates internally is already UTC; see
    scripts/run_daily_scan.py's use of datetime.now(timezone.utc))."""
    normalised = value.strip()
    if normalised.endswith("Z"):
        normalised = normalised[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalised)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def assess_money_qualification(
    *,
    research_grade: str,
    estimated_probability: float,
    confidence_label: str,
    data_quality_ok: bool,
    decimal_odds: float,
    net_ev: float,
    kickoff_iso: str | None,
    scan_timestamp_iso: str,
    payout_policy_thresholds: PayoutPolicyThresholds,
    thresholds: MoneyQualificationThresholds,
) -> MoneyQualificationResult:
    """Decide whether one already-graded candidate qualifies for real money.

    Args:
        research_grade: The grade decisions.grading.grade_opportunity (and
            decisions.payout_policy.apply_payout_floor) already assigned --
            never recomputed here.
        estimated_probability: The model/consensus probability used for
            this candidate (storage.schemas.MarketRecord.final_probability
            or consensus_probability).
        confidence_label: decisions.confidence.assess_confidence's label
            ("High", "Medium", or "Low") for this candidate.
        data_quality_ok: decisions.data_quality.assess_data_quality's
            mechanical result for this candidate.
        decimal_odds: The best currently-obtainable price.
        net_ev: The candidate's net EV (ev.expected_value's result).
        kickoff_iso: The fixture's full ISO kickoff timestamp, if known
            (live odds-api scans only -- see ingestion/the_odds_api_loader.py).
            None (manual-mode scans, or a live event missing a usable
            timestamp) always fails the horizon check -- a money bet is
            never approved on an unverifiable kickoff time.
        scan_timestamp_iso: ISO timestamp this scan/candidate was priced at.
        payout_policy_thresholds: The active PayoutPolicyThresholds (reused,
            not duplicated -- see module docstring).
        thresholds: The active MoneyQualificationThresholds.

    Returns:
        A MoneyQualificationResult. money_decision is "REJECT" only when
        the underlying research grade itself was never actionable (C or
        Reject); "WATCH" when everything else is strong but the fixture
        currently sits outside the money horizon (worth resurfacing as it
        approaches); "PAPER_ONLY" for every other failure; "BET" only
        when every gate passes.
    """
    reasons: list[str] = []

    horizon_only_failure = False

    if kickoff_iso is None or not kickoff_iso.strip():
        reasons.append("kickoff timestamp is unavailable -- cannot verify the money-event horizon")
    else:
        kickoff_dt = _parse_iso_timestamp(kickoff_iso)
        scan_dt = _parse_iso_timestamp(scan_timestamp_iso)
        if kickoff_dt <= scan_dt:
            reasons.append(
                "kickoff is not after the scan timestamp (the event may have already started or finished)"
            )
        else:
            hours_to_kickoff = (kickoff_dt - scan_dt).total_seconds() / 3600.0
            if hours_to_kickoff > thresholds.event_horizon_hours:
                reasons.append(
                    f"kickoff is {hours_to_kickoff:.1f}h away -- outside the configured "
                    f"{thresholds.event_horizon_hours:.0f}h money-event horizon"
                )
                horizon_only_failure = True

    if research_grade not in ACTIONABLE_RESEARCH_GRADES:
        reasons.append(
            f"research grade {research_grade!r} is not in the actionable set "
            f"{sorted(ACTIONABLE_RESEARCH_GRADES)}"
        )

    is_eligible_confidence = confidence_label in thresholds.eligible_confidence_labels
    is_conditional_confidence = confidence_label in thresholds.conditional_confidence_labels

    if is_eligible_confidence:
        min_probability_required: float | None = thresholds.min_probability
        min_net_ev_required: float | None = thresholds.min_net_ev
    elif is_conditional_confidence:
        min_probability_required = thresholds.min_probability_medium_confidence
        min_net_ev_required = thresholds.min_net_ev_medium_confidence
    else:
        reasons.append(
            f"confidence {confidence_label!r} is not eligible for real-money qualification "
            f"(requires one of {sorted(thresholds.eligible_confidence_labels)}, or "
            f"{sorted(thresholds.conditional_confidence_labels)} with every other requirement strong)"
        )
        min_probability_required = None
        min_net_ev_required = None

    if not data_quality_ok:
        reasons.append("data quality did not pass the mechanical data-quality check")

    if min_probability_required is not None and estimated_probability < min_probability_required:
        qualifier = " (the stricter Medium-confidence floor)" if is_conditional_confidence else ""
        reasons.append(
            f"estimated probability {estimated_probability:.1%} is below the "
            f"{min_probability_required:.0%} money-qualification floor{qualifier}"
        )

    if decimal_odds < payout_policy_thresholds.normal_min_decimal_odds:
        reasons.append(
            f"odds {decimal_odds:.2f} are below the configured payout floor of "
            f"{payout_policy_thresholds.normal_min_decimal_odds:.2f}"
        )
    elif (
        is_conditional_confidence
        and thresholds.require_preferred_odds_band_for_conditional_confidence
        and not (
            payout_policy_thresholds.preferred_min_decimal_odds
            <= decimal_odds
            <= payout_policy_thresholds.preferred_max_decimal_odds
        )
    ):
        reasons.append(
            "Medium-confidence candidates require odds inside the preferred range "
            f"{payout_policy_thresholds.preferred_min_decimal_odds:.2f}-"
            f"{payout_policy_thresholds.preferred_max_decimal_odds:.2f}; odds are {decimal_odds:.2f}"
        )

    if min_net_ev_required is not None and net_ev < min_net_ev_required:
        qualifier = " (the stricter Medium-confidence floor)" if is_conditional_confidence else ""
        reasons.append(
            f"net EV {net_ev:.2%} is below the {min_net_ev_required:.2%} "
            f"money-qualification value floor{qualifier}"
        )

    money_qualified = not reasons
    money_decision: MoneyDecision
    if money_qualified:
        money_decision = "BET"
    elif research_grade not in ACTIONABLE_RESEARCH_GRADES:
        money_decision = "REJECT"
    elif horizon_only_failure and len(reasons) == 1:
        money_decision = "WATCH"
    else:
        money_decision = "PAPER_ONLY"

    return MoneyQualificationResult(
        money_qualified=money_qualified,
        money_decision=money_decision,
        money_rejection_reasons=reasons,
    )
