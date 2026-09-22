"""The frozen-V1 historical replay harness.

Reuses the ACTUAL production decision pipeline
(probability.market_pipeline.compute_market_consensus ->
decisions.recommendation.build_recommendation, which itself calls
confidence/data_quality/liquidity/grading/payout_policy/
money_qualification) against real historical 1X2 data
(backtesting.historical_loader) under a frozen, hashed configuration
(backtesting.frozen_strategy) -- see research/backtesting/
BACKTEST_DATA_FEASIBILITY_AUDIT.md and LEAKAGE_AUDIT.md for the design
this module implements and the limitations it discloses rather than
hides.

No threshold, grading rule, or money-qualification rule is
re-implemented here -- this module's only job is to (a) shape historical
rows into the exact inputs those modules already expect, and (b) settle
the result and simulate a bankroll AFTER the recommendation has already
been computed, never before (see the leakage audit's settlement-ordering
verification).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from prediction_markets_lab.backtesting.frozen_strategy import FrozenStrategy, rebuild_threshold_objects
from prediction_markets_lab.backtesting.historical_loader import (
    HistoricalMatch,
    LoadReport,
    actual_result_letter_matches,
    load_matches_for_replay,
    simulated_scan_timestamp_iso,
)
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.market_pipeline import compute_market_consensus
from prediction_markets_lab.risk.bankroll import BankrollState
from prediction_markets_lab.risk.decision_gates import check_risk_gates
from prediction_markets_lab.risk.exposure import ExposureState
from prediction_markets_lab.risk.loss_locks import check_loss_locks

EXPECTED_OUTCOMES_1X2 = ["home", "draw", "away"]


@dataclass(frozen=True)
class BacktestCandidate:
    """One (historical match, selection) candidate, fully recommended and settled."""

    match_id: str
    selection: str
    event_date: str
    competition_code: str
    competition_name: str
    season: str
    home_team: str
    away_team: str
    accepted_bookmaker_count: int
    consensus_probability: float
    decimal_odds: float
    venue: str
    net_ev: float
    probability_edge_pp: float
    confidence_label: str
    data_quality_ok: bool
    research_grade: str
    money_decision: str
    money_qualified: bool
    money_rejection_reason: str
    recommended_stake_gbp: float
    actual_won: bool
    kickoff_iso: str | None
    scan_timestamp_iso: str | None
    # Populated only for money-qualified candidates during the bankroll walk.
    risk_gate_passed: bool | None = None
    risk_gate_reason: str | None = None
    staked_gbp: float = 0.0
    net_change_gbp: float = 0.0
    bankroll_after_gbp: float | None = None


@dataclass
class ReplayRun:
    """The full output of one frozen-V1 replay run."""

    price_timing: str
    apply_risk_gates: bool
    frozen_strategy: FrozenStrategy
    load_report: LoadReport
    candidates: list[BacktestCandidate] = field(default_factory=list)
    excluded_matches: list[dict] = field(default_factory=list)
    starting_bankroll_gbp: float = 0.0
    ending_bankroll_gbp: float = 0.0
    bankroll_exhausted: bool = False
    bankroll_exhausted_at_match_id: str | None = None


def _best_price_among_accepted(
    match: HistoricalMatch, outcome: str, rejected_bookmakers: set[str]
) -> tuple[str, float]:
    """The best (highest) decimal odds for `outcome` among bookmakers NOT
    rejected by compute_market_consensus for this match (see LEAKAGE_AUDIT.md
    -- best price must be drawn only from accepted bookmakers)."""
    candidates = {
        bookmaker: odds[outcome]
        for bookmaker, odds in match.bookmaker_odds.items()
        if bookmaker not in rejected_bookmakers
    }
    best_bookmaker = max(candidates, key=candidates.get)
    return best_bookmaker, candidates[best_bookmaker]


def _iso_week_key(iso_date: str) -> tuple[int, int]:
    y, m, d = (int(x) for x in iso_date.split("-"))
    iso = date(y, m, d).isocalendar()
    return (iso[0], iso[1])


def build_candidates(
    matches: list[HistoricalMatch], strategy: FrozenStrategy
) -> tuple[list[BacktestCandidate], list[dict]]:
    """Run every historical match through the real production recommendation
    pipeline, in chronological order, producing one candidate per
    (match, outcome). Does NOT simulate the bankroll -- see simulate_bankroll.

    Returns:
        (candidates, excluded_matches) -- excluded_matches records any
        match that could not be processed (e.g. compute_market_consensus
        rejects every bookmaker), with a reason, never silently dropped.
    """
    rebuilt = rebuild_threshold_objects(strategy)

    ordered = sorted(matches, key=lambda m: (m.match_date, m.match_id))

    candidates: list[BacktestCandidate] = []
    excluded: list[dict] = []

    for match in ordered:
        scan_ts = simulated_scan_timestamp_iso(match)
        if scan_ts is None:
            excluded.append(
                {
                    "match_id": match.match_id,
                    "reason": "no kickoff timestamp recovered -- cannot construct a simulated scan timestamp",
                }
            )
            continue

        try:
            market_result = compute_market_consensus(
                match.match_id, match.bookmaker_odds, EXPECTED_OUTCOMES_1X2
            )
        except ValueError as exc:
            excluded.append({"match_id": match.match_id, "reason": str(exc)})
            continue

        rejected_names = {r.bookmaker for r in market_result.rejected_bookmakers}

        for outcome in EXPECTED_OUTCOMES_1X2:
            consensus = market_result.consensus_by_outcome.get(outcome)
            if consensus is None:
                continue
            venue, decimal_odds = _best_price_among_accepted(match, outcome, rejected_names)

            result = build_recommendation(
                market_id=f"{match.match_id}:{outcome}",
                scan_timestamp=scan_ts,
                event_date=match.match_date,
                sport="football",
                competition=match.competition_name,
                event=f"{match.home_team_raw} v {match.away_team_raw}",
                market_type="1x2",
                selection=outcome,
                consensus=consensus,
                accepted_bookmaker_count=market_result.accepted_bookmaker_count,
                best_price=PriceQuote(venue=venue, decimal_odds=decimal_odds, commission=0.0, available_size_gbp=None),
                quote_age_minutes=0.0,
                staking_config=rebuilt["staking"],
                grading_thresholds=rebuilt["grading"],
                confidence_thresholds=rebuilt["confidence"],
                data_quality_thresholds=rebuilt["data_quality"],
                payout_policy_thresholds=rebuilt["payout_policy"],
                money_qualification_thresholds=rebuilt["money_qualification"],
                kickoff_iso=match.kickoff_iso,
            )
            record = result.market_record

            candidates.append(
                BacktestCandidate(
                    match_id=match.match_id,
                    selection=outcome,
                    event_date=match.match_date,
                    competition_code=match.competition_code,
                    competition_name=match.competition_name,
                    season=match.season,
                    home_team=match.home_team_raw,
                    away_team=match.away_team_raw,
                    accepted_bookmaker_count=market_result.accepted_bookmaker_count,
                    consensus_probability=record.consensus_probability,
                    decimal_odds=record.exchange_odds,
                    venue=record.exchange,
                    net_ev=record.net_ev,
                    probability_edge_pp=record.probability_edge,
                    confidence_label=record.confidence_score,
                    data_quality_ok=record.data_quality_score == "ok",
                    research_grade=record.research_grade,
                    money_decision=record.money_decision,
                    money_qualified=record.money_qualified,
                    money_rejection_reason=record.money_rejection_reason,
                    recommended_stake_gbp=result.stake_gbp,
                    # Settlement happens strictly AFTER the recommendation above has
                    # already been fully built and recorded -- see LEAKAGE_AUDIT.md.
                    actual_won=actual_result_letter_matches(outcome, match.full_time_result),
                    kickoff_iso=match.kickoff_iso,
                    scan_timestamp_iso=scan_ts,
                )
            )

    return candidates, excluded


def simulate_bankroll(
    candidates: list[BacktestCandidate], strategy: FrozenStrategy, apply_risk_gates: bool
) -> tuple[list[BacktestCandidate], float, bool, str | None]:
    """Walk money-qualified BET candidates in chronological order, applying
    the actual production stake per grade, and (optionally) the existing
    risk.decision_gates exposure/loss-lock checks.

    IMPORTANT DISCLOSURE (see the backtest report's manifest): risk.
    decision_gates / risk.exposure / risk.loss_locks are tested production
    modules that are NOT currently wired into scripts/run_daily_scan.py's
    automated live path -- a pre-existing gap, out of scope to fix in this
    phase (Section 20 forbids automation-interface changes). This
    simulation applies them anyway when apply_risk_gates=True, because the
    master research directive explicitly requires "no duplicate exposure"
    and configurable staking risk controls, and the governing backtest
    instruction explicitly names "risk/staking rules" as part of the
    frozen strategy to simulate. Set apply_risk_gates=False to reproduce
    exactly what the live automated scan currently permits (no exposure/
    loss-lock gating at all).

    Returns:
        (candidates_with_settlement_fields_filled, ending_bankroll_gbp,
        bankroll_exhausted, exhausted_at_match_id).
    """
    rebuilt = rebuild_threshold_objects(strategy)
    staking = rebuilt["staking"]

    bankroll = BankrollState(
        current_balance=staking.starting_bankroll_gbp, peak_balance=staking.starting_bankroll_gbp
    )
    exposure = ExposureState()
    current_day: str | None = None
    current_week: tuple[int, int] | None = None
    daily_loss_gbp = 0.0
    weekly_loss_gbp = 0.0
    exhausted = False
    exhausted_at: str | None = None

    updated: list[BacktestCandidate] = []
    for candidate in candidates:
        if not candidate.money_qualified or exhausted:
            updated.append(candidate)
            continue

        if candidate.event_date != current_day:
            current_day = candidate.event_date
            exposure.clear()
            daily_loss_gbp = 0.0
        week_key = _iso_week_key(candidate.event_date)
        if week_key != current_week:
            current_week = week_key
            weekly_loss_gbp = 0.0

        stake = candidate.recommended_stake_gbp
        if stake <= 0:
            updated.append(candidate)
            continue

        if apply_risk_gates:
            loss_lock_status = check_loss_locks(
                daily_loss_gbp, weekly_loss_gbp, staking.daily_loss_stop_gbp, staking.weekly_loss_stop_gbp
            )
            gate = check_risk_gates(stake, exposure, loss_lock_status, staking)
            if not gate.passed:
                updated.append(
                    BacktestCandidate(**{**candidate.__dict__, "risk_gate_passed": False, "risk_gate_reason": gate.reason})
                )
                continue

        if candidate.actual_won:
            net_change = stake * (candidate.decimal_odds - 1.0)
        else:
            net_change = -stake

        if bankroll.current_balance + net_change < 0:
            # Bankroll cannot go negative -- cap the loss at what remains and
            # halt further staking for the rest of the run. This is a real,
            # reportable outcome (bankroll exhausted), never silently
            # absorbed or hidden by letting the balance go negative.
            net_change = -bankroll.current_balance
            exhausted = True
            exhausted_at = candidate.match_id

        exposure.add_stake(stake)
        if net_change < 0:
            daily_loss_gbp += -net_change
            weekly_loss_gbp += -net_change
        bankroll = bankroll.apply_change(net_change)

        updated.append(
            BacktestCandidate(
                **{
                    **candidate.__dict__,
                    "risk_gate_passed": True if apply_risk_gates else None,
                    "staked_gbp": stake,
                    "net_change_gbp": net_change,
                    "bankroll_after_gbp": bankroll.current_balance,
                }
            )
        )
        if exhausted:
            break

    # Any candidates after an exhaustion break were never visited by the
    # loop above -- append them unchanged so the full candidate list length
    # is always preserved (every candidate is reported, never dropped).
    processed_ids = {(c.match_id, c.selection) for c in updated}
    for candidate in candidates:
        if (candidate.match_id, candidate.selection) not in processed_ids:
            updated.append(candidate)

    return updated, bankroll.current_balance, exhausted, exhausted_at


def run_replay(price_timing: str, apply_risk_gates: bool, strategy: FrozenStrategy) -> ReplayRun:
    """End-to-end: load historical data, build candidates, simulate the bankroll."""
    matches, load_report = load_matches_for_replay(price_timing)
    candidates, excluded = build_candidates(matches, strategy)
    settled_candidates, ending_bankroll, exhausted, exhausted_at = simulate_bankroll(
        candidates, strategy, apply_risk_gates
    )
    rebuilt = rebuild_threshold_objects(strategy)
    return ReplayRun(
        price_timing=price_timing,
        apply_risk_gates=apply_risk_gates,
        frozen_strategy=strategy,
        load_report=load_report,
        candidates=settled_candidates,
        excluded_matches=excluded,
        starting_bankroll_gbp=rebuilt["staking"].starting_bankroll_gbp,
        ending_bankroll_gbp=ending_bankroll,
        bankroll_exhausted=exhausted,
        bankroll_exhausted_at_match_id=exhausted_at,
    )
