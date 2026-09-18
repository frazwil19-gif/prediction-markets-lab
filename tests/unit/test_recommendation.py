"""Tests for decisions.recommendation (Daily Engine V1 build, 2026-09-18).

Integration-style: exercises the real consensus/EV/confidence/data-quality/
liquidity/grading/staking modules together, the same composition
scripts/run_daily_scan.py calls for every candidate.
"""

from __future__ import annotations

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.consensus import calculate_consensus
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


def _common_kwargs(**overrides):
    kwargs = dict(
        market_id="E0-2026-09-18-TEST-1X2",
        scan_timestamp="2026-09-18T09:00:00",
        event_date="2026-09-18",
        sport="football",
        competition="Premier League",
        event="Team A v Team B",
        market_type="1x2",
        selection="home",
        staking_config=_staking_config(),
        grading_thresholds=GradingThresholds(),
        confidence_thresholds=ConfidenceThresholds(),
        data_quality_thresholds=DataQualityThresholds(),
        quote_age_minutes=5.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_strong_edge_with_broad_agreement_grades_highly_and_stakes():
    consensus = calculate_consensus([0.60, 0.61, 0.59, 0.60, 0.60])  # 5 bookmakers, tight agreement
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=2.20, commission=0.0),
        )
    )
    assert result.market_record.grade in ("A+", "A")
    assert result.stake_gbp > 0.0
    assert result.market_record.confidence_score == "High"
    assert result.market_record.exchange == "Bet365"  # generalised venue field, not "Betfair"/"Smarkets"


def test_zero_edge_grades_c_watchlist_and_unstaked():
    # net_ev == 0.0 clears the Reject floor (>= 0.00) but not the Grade B
    # floor (>= 0.02) -- grading.py's own boundary, per config/thresholds.yaml.
    probability = 1.0 / 1.80
    consensus = calculate_consensus([probability] * 4)
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=4,
            best_price=PriceQuote(venue="William Hill", decimal_odds=1.80, commission=0.0),
        )
    )
    assert result.market_record.grade == "C"
    assert result.stake_gbp == 0.0


def test_stale_quote_forces_reject_even_with_strong_edge():
    consensus = calculate_consensus([0.60, 0.61, 0.59, 0.60, 0.60])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=2.20, commission=0.0),
            quote_age_minutes=10_000.0,
        )
    )
    assert result.market_record.grade == "Reject"
    assert result.stake_gbp == 0.0
    assert "old" in result.market_record.data_quality_score


def test_manually_flagged_info_risk_caps_grade_at_b():
    # no_material_info_risk=False cannot force a full Reject (grading.py
    # treats it as an A+/A safety gate only, downgrading to paper-trade-only
    # B rather than discarding a numerically strong candidate outright).
    consensus = calculate_consensus([0.60, 0.61, 0.59, 0.60, 0.60])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=2.20, commission=0.0),
            no_material_info_risk=False,
        )
    )
    assert result.market_record.grade == "B"
    assert result.stake_gbp == 0.0


def test_exchange_price_with_inadequate_size_marks_liquidity_inadequate():
    consensus = calculate_consensus([0.60, 0.61, 0.59, 0.60, 0.60])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(
                venue="Betfair", decimal_odds=2.20, commission=0.02, available_size_gbp=0.01
            ),
        )
    )
    assert result.market_record.liquidity_score == "inadequate"
    assert result.market_record.grade == "Reject"
