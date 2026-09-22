"""Tests for storage.paper_ledger's money_qualified column (TARGETED
PRODUCTION CHANGE -- DAILY MONEY WINDOW + MONEY/PAPER SEPARATION,
2026-09-22)."""

from __future__ import annotations

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.risk.staking import StakingConfig
from prediction_markets_lab.storage.paper_ledger import load_paper_bets, record_qualifying_candidates


def _staking_config() -> StakingConfig:
    return StakingConfig(
        starting_bankroll_gbp=10.0,
        normal_stake_gbp=0.25,
        maximum_stake_gbp=0.50,
        maximum_daily_exposure_gbp=0.75,
        maximum_open_bets=3,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )


def _build(market_id: str, selection: str, probs: list[float], odds: float, bookmakers: int, kickoff_iso):
    consensus = calculate_consensus(probs)
    return build_recommendation(
        market_id=market_id,
        scan_timestamp="2026-09-22T09:00:00+00:00",
        event_date="2026-09-22",
        sport="football",
        competition="Premier League",
        event="Team A v Team B",
        market_type="1x2",
        selection=selection,
        consensus=consensus,
        accepted_bookmaker_count=bookmakers,
        best_price=PriceQuote(venue="Bet365", decimal_odds=odds, commission=0.0),
        quote_age_minutes=5.0,
        staking_config=_staking_config(),
        grading_thresholds=GradingThresholds(),
        confidence_thresholds=ConfidenceThresholds(),
        data_quality_thresholds=DataQualityThresholds(),
        kickoff_iso=kickoff_iso,
    )


def test_money_qualified_and_real_kickoff_time_are_recorded(tmp_path):
    money_bet = _build(
        "M-1", "home", [0.65, 0.66, 0.64, 0.65, 0.65], 1.80, 5, "2026-09-22T18:00:00+00:00"
    )
    longshot = _build(
        "M-2", "away", [0.078, 0.08, 0.075, 0.079], 14.00, 4, "2026-09-22T18:00:00+00:00"
    )
    ledger_path = tmp_path / "paper_bets.csv"

    record_qualifying_candidates(
        ledger_path, [money_bet, longshot], scan_id="scan-1", created_at="2026-09-22T09:00:00+00:00"
    )
    rows = {row["selection"]: row for row in load_paper_bets(ledger_path)}

    assert rows["home"]["money_qualified"] == "True"
    assert rows["home"]["kickoff"] == "2026-09-22T18:00:00+00:00"
    assert rows["away"]["money_qualified"] == "False"


def test_missing_kickoff_records_not_money_qualified(tmp_path):
    no_kickoff_bet = _build(
        "M-3", "home", [0.65, 0.66, 0.64, 0.65, 0.65], 1.80, 5, kickoff_iso=None
    )
    ledger_path = tmp_path / "paper_bets.csv"

    record_qualifying_candidates(
        ledger_path, [no_kickoff_bet], scan_id="scan-1", created_at="2026-09-22T09:00:00+00:00"
    )
    rows = load_paper_bets(ledger_path)
    assert rows[0]["money_qualified"] == "False"
    # No real kickoff timestamp was available -- falls back to the
    # date-only event_date, exactly as before this change.
    assert rows[0]["kickoff"] == "2026-09-22"
