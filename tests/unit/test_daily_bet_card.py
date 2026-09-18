"""Tests for reports.daily_bet_card (Daily Engine V1 build, 2026-09-18)."""

from __future__ import annotations

from datetime import datetime

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.reports.daily_bet_card import (
    DailyBetCardContext,
    render_daily_bet_card,
)
from prediction_markets_lab.risk.staking import StakingConfig


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


def _build(selection: str, probs: list[float], odds: float, bookmakers: int):
    consensus = calculate_consensus(probs)
    return build_recommendation(
        market_id=f"TEST-{selection}",
        scan_timestamp="2026-09-18T09:00:00",
        event_date="2026-09-18",
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
    )


def test_card_contains_header_and_ranked_selection():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [strong])
    assert "DAILY BET CARD" in text
    assert "RANKED SELECTIONS" in text
    assert "OPTIONAL MULTI" in text
    assert "REJECT / WATCH SUMMARY" in text
    assert "home" in text
    assert f"£{10.0:.2f}" in text


def test_reject_candidate_appears_only_in_watch_summary_not_ranked():
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [reject])
    ranked_section = text.split("RANKED SELECTIONS")[1].split("OPTIONAL MULTI")[0]
    assert "away" not in ranked_section
    watch_section = text.split("REJECT / WATCH SUMMARY")[1]
    assert "away" in watch_section


def test_no_qualifying_candidates_says_so_explicitly():
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [reject])
    assert "no candidate cleared Grade B or better" in text


def test_system_warnings_are_rendered_when_present():
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [reject], system_warnings=["test warning"])
    assert "System warnings:" in text
    assert "test warning" in text
