"""End-to-end recommendation assembly.

V1 implementation (2026-09-18, Daily Engine V1 build). Formalises what
this module's original Stage-1 docstring described: combining
probability.consensus (via probability.market_pipeline), ev.expected_value,
decisions.confidence, decisions.data_quality, decisions.liquidity,
decisions.grading, and risk.staking into a single storage.schemas.
MarketRecord (a Daily Card row) plus its recommended stake. Previously
this composition was done ad hoc inside scripts/generate_daily_shortlist.py;
scripts/run_daily_scan.py (V1) calls this module for every candidate
selection instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds, assess_confidence
from prediction_markets_lab.decisions.data_quality import (
    DataQualityThresholds,
    assess_data_quality,
)
from prediction_markets_lab.decisions.grading import (
    GradingInput,
    GradingResult,
    GradingThresholds,
    grade_opportunity,
)
from prediction_markets_lab.decisions.payout_policy import PayoutPolicyThresholds, apply_payout_floor
from prediction_markets_lab.decisions.liquidity import assess_liquidity
from prediction_markets_lab.ev.expected_value import evaluate
from prediction_markets_lab.probability.consensus import ConsensusResult
from prediction_markets_lab.risk.staking import StakingConfig, recommended_stake_gbp
from prediction_markets_lab.storage.schemas import MarketRecord


@dataclass(frozen=True)
class PriceQuote:
    """The single best currently-obtainable price for one selection.

    `venue` is any bookmaker or exchange name (storage.schemas.Exchange
    was generalised from a two-exchange Literal to a free-form str on
    2026-09-18 for exactly this reason -- see
    docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md point 4/10).
    V1's price source is a fixed-odds bookmaker, so `available_size_gbp`
    is normally None and `commission` is normally 0.0; both remain
    usable for a genuine exchange price.
    """

    venue: str
    decimal_odds: float
    commission: float = 0.0
    available_size_gbp: float | None = None


@dataclass(frozen=True)
class RecommendationResult:
    """A single fully-assembled Daily Card row, plus its recommended stake."""

    market_record: MarketRecord
    stake_gbp: float


def build_recommendation(
    *,
    market_id: str,
    scan_timestamp: str,
    event_date: str,
    sport: str,
    competition: str,
    event: str,
    market_type: str,
    selection: str,
    consensus: ConsensusResult,
    accepted_bookmaker_count: int,
    best_price: PriceQuote,
    quote_age_minutes: float,
    staking_config: StakingConfig,
    grading_thresholds: GradingThresholds,
    confidence_thresholds: ConfidenceThresholds,
    data_quality_thresholds: DataQualityThresholds,
    no_material_info_risk: bool = True,
    market_rules_match: bool = True,
    payout_policy_thresholds: PayoutPolicyThresholds = PayoutPolicyThresholds(),
) -> RecommendationResult:
    """Assemble one candidate's full Daily Card row and recommended stake.

    Args:
        market_id: Identifier for this specific proposition.
        scan_timestamp: ISO timestamp this scan ran.
        event_date: ISO date of the fixture.
        sport: Sport tag (e.g. "football").
        competition: Competition name.
        event: Human-readable fixture description (e.g. "Team A v Team B").
        market_type: Market family (e.g. "1x2", "over_under_2_5").
        selection: The specific selection within the market.
        consensus: The margin-free, cross-bookmaker consensus for this
            selection (probability.consensus.ConsensusResult).
        accepted_bookmaker_count: Number of bookmakers accepted into the
            consensus for this market (may differ from
            consensus.bookmaker_count if some bookmakers were rejected
            for other outcomes but not this one -- pass the market's
            accepted count, not the per-outcome one, for an honest data
            quality read).
        best_price: The single best currently-obtainable price to bet
            this selection at.
        quote_age_minutes: Minutes since best_price was entered/quoted.
        staking_config: The active risk.staking.StakingConfig.
        grading_thresholds: The active decisions.grading.GradingThresholds.
        confidence_thresholds: The active
            decisions.confidence.ConfidenceThresholds.
        data_quality_thresholds: The active
            decisions.data_quality.DataQualityThresholds.
        no_material_info_risk: Whether there is no known team-news/
            postponement risk not yet reflected in the price. This stays
            a human-owned judgement for V1 (see decisions.grading's
            module docstring) -- default True (no known risk flagged);
            pass False explicitly when a human has flagged a concern.
        market_rules_match: Whether the selection/market definition used
            for the consensus exactly matches the one best_price is
            quoted for (e.g. the same Asian Handicap line). Also a
            human-owned check for V1; default True.
        payout_policy_thresholds: The active decisions.payout_policy.
            PayoutPolicyThresholds -- demotes an otherwise A+/A/B grade to
            C (watch-only) if the price is below the configured payout
            floor. Callers should normally load config/thresholds.yaml's
            payout_policy section rather than relying on this default.

    Returns:
        A RecommendationResult with the fully populated MarketRecord
        (grade, EV, confidence/data-quality/liquidity labels all
        computed) and its recommended stake.
    """
    ev_result = evaluate(
        probability=consensus.consensus_probability,
        decimal_odds=best_price.decimal_odds,
        commission=best_price.commission,
    )

    confidence_label = assess_confidence(
        bookmaker_count=accepted_bookmaker_count,
        consensus_std_dev=consensus.std_dev,
        thresholds=confidence_thresholds,
    )
    data_quality = assess_data_quality(
        bookmaker_count=accepted_bookmaker_count,
        quote_age_minutes=quote_age_minutes,
        thresholds=data_quality_thresholds,
    )
    liquidity_adequate = assess_liquidity(
        stake_gbp=staking_config.normal_stake_gbp,
        available_size_gbp=best_price.available_size_gbp,
    )

    evidence = GradingInput(
        net_ev=ev_result.net_ev,
        probability_edge_pp=ev_result.probability_edge_pp,
        bookmaker_count=accepted_bookmaker_count,
        data_quality_ok=data_quality.ok,
        no_material_info_risk=no_material_info_risk,
        exchange_price_current=quote_age_minutes <= data_quality_thresholds.max_quote_age_minutes,
        market_rules_match=market_rules_match,
        liquidity_adequate=liquidity_adequate,
    )
    grading_result = grade_opportunity(evidence, grading_thresholds)
    demoted_grade, demoted_reason = apply_payout_floor(
        grading_result.grade,
        grading_result.reason,
        best_price.decimal_odds,
        payout_policy_thresholds,
    )
    if demoted_grade != grading_result.grade:
        grading_result = GradingResult(demoted_grade, demoted_reason)
    stake_gbp = recommended_stake_gbp(grading_result.grade, staking_config)

    record = MarketRecord(
        market_id=market_id,
        scan_timestamp=scan_timestamp,
        event_date=event_date,
        sport=sport,
        competition=competition,
        event=event,
        market_type=market_type,
        selection=selection,
        bookmaker_count=accepted_bookmaker_count,
        consensus_probability=consensus.consensus_probability,
        consensus_mean=consensus.mean,
        consensus_median=consensus.median,
        consensus_std=consensus.std_dev,
        final_probability=consensus.consensus_probability,
        exchange=best_price.venue,
        exchange_odds=best_price.decimal_odds,
        exchange_implied_probability=ev_result.exchange_implied_probability,
        commission=best_price.commission,
        probability_edge=ev_result.probability_edge_pp,
        gross_ev=ev_result.gross_ev,
        net_ev=ev_result.net_ev,
        confidence_score=confidence_label,
        data_quality_score="ok" if data_quality.ok else "; ".join(data_quality.reasons),
        liquidity_score="adequate" if liquidity_adequate else "inadequate",
        grade=grading_result.grade,
        decision=grading_result.reason,
        rejection_reason=grading_result.reason if grading_result.grade == "Reject" else "",
    )
    return RecommendationResult(market_record=record, stake_gbp=stake_gbp)
