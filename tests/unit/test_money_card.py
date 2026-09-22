"""Tests for reports.money_card (TARGETED PRODUCTION CHANGE -- DAILY MONEY
WINDOW + MONEY/PAPER SEPARATION, 2026-09-22)."""

from __future__ import annotations

import json
from datetime import datetime

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.reports.daily_bet_card import DailyBetCardContext, build_daily_bet_card_contract
from prediction_markets_lab.reports.money_card import (
    build_money_card_contract,
    render_money_card_markdown,
    write_money_card_outputs,
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


def _build(selection: str, probs: list[float], odds: float, bookmakers: int, kickoff_iso: str | None):
    consensus = calculate_consensus(probs)
    return build_recommendation(
        market_id=f"TEST-{selection}",
        scan_timestamp="2026-09-22T09:00:00+00:00",
        event_date="2026-09-22",
        sport="football",
        competition="Premier League",
        event=f"Team {selection} fixture",
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


def test_money_card_contains_only_money_qualified_candidates():
    money_bet = _build("home", [0.65, 0.66, 0.64, 0.65, 0.65], 1.80, 5, "2026-09-22T18:00:00+00:00")
    longshot = _build("away", [0.078, 0.08, 0.075, 0.079], 14.00, 4, "2026-09-22T18:00:00+00:00")
    far_future = _build("draw", [0.65, 0.66, 0.64, 0.65, 0.65], 1.80, 5, "2026-10-18T15:00:00+00:00")

    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 22, 9, 0), bankroll_gbp=10.0, fixtures_scanned=3, markets_scanned=3
    )
    full_contract = build_daily_bet_card_contract(context, [money_bet, longshot, far_future])
    money_contract = build_money_card_contract(full_contract, money_event_horizon_hours=24.0)

    assert money_contract["money_qualified_count"] == 1
    assert len(money_contract["money_qualified_candidates"]) == 1
    assert money_contract["money_qualified_candidates"][0]["selection"] == "home"
    assert money_contract["research_candidates_analysed"] == 3
    assert money_contract["best_bet"]["selection"] == "home"


def test_empty_money_card_is_valid_and_says_so():
    longshot = _build("away", [0.078, 0.08, 0.075, 0.079], 14.00, 4, "2026-09-22T18:00:00+00:00")
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 22, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    full_contract = build_daily_bet_card_contract(context, [longshot])
    money_contract = build_money_card_contract(full_contract, money_event_horizon_hours=24.0)

    assert money_contract["money_qualified_count"] == 0
    assert money_contract["money_qualified_candidates"] == []
    assert money_contract["best_bet"] is None

    markdown = render_money_card_markdown(money_contract, date_label="2026-09-22")
    assert "NO MONEY BETS QUALIFIED TODAY" in markdown
    assert "DAILY MONEY CARD" in markdown


def test_money_card_markdown_shows_best_bet_when_present():
    money_bet = _build("home", [0.65, 0.66, 0.64, 0.65, 0.65], 1.80, 5, "2026-09-22T18:00:00+00:00")
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 22, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    full_contract = build_daily_bet_card_contract(context, [money_bet])
    money_contract = build_money_card_contract(full_contract, money_event_horizon_hours=24.0)
    markdown = render_money_card_markdown(money_contract, date_label="2026-09-22")
    assert "BEST BET" in markdown
    assert "home" in markdown
    assert "NO MONEY BETS QUALIFIED" not in markdown


def test_write_money_card_outputs_writes_both_files(tmp_path):
    money_bet = _build("home", [0.65, 0.66, 0.64, 0.65, 0.65], 1.80, 5, "2026-09-22T18:00:00+00:00")
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 22, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    full_contract = build_daily_bet_card_contract(context, [money_bet])
    money_contract = build_money_card_contract(full_contract, money_event_horizon_hours=24.0)
    markdown = render_money_card_markdown(money_contract, date_label="2026-09-22")

    out_dir = tmp_path / "2026-09-22"
    paths = write_money_card_outputs(out_dir, money_contract, markdown)

    assert paths["json"].exists()
    assert paths["md"].exists()
    loaded = json.loads(paths["json"].read_text())
    assert loaded["money_qualified_count"] == 1
    assert "DAILY MONEY CARD" in paths["md"].read_text()
