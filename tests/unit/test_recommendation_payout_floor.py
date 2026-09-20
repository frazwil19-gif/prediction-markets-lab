"""Integration tests: decisions.recommendation + decisions.payout_policy
(Production Infrastructure Build, 2026-09-20, Section 3).
"""

from __future__ import annotations

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.payout_policy import PayoutPolicyThresholds
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
        market_id="E0-TEST-1X2",
        scan_timestamp="2026-09-20T09:00:00",
        event_date="2026-09-20",
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


def test_strong_edge_but_low_odds_is_demoted_to_c_watch_only():
    # High, tightly-agreed consensus probability (0.95) against a low
    # price (1.10) -- clears the EV/edge/bookmaker-count bars easily, but
    # 1.10 is well below the 1.33 payout floor, so this must be demoted.
    consensus = calculate_consensus([0.95, 0.95, 0.95, 0.95, 0.95])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=1.10, commission=0.0),
        )
    )
    assert result.market_record.grade == "C"
    assert result.stake_gbp == 0.0
    assert "payout floor" in result.market_record.decision


def test_strong_edge_above_floor_keeps_actionable_grade():
    consensus = calculate_consensus([0.60, 0.61, 0.59, 0.60, 0.60])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=2.20, commission=0.0),
        )
    )
    assert result.market_record.grade in ("A+", "A")


def test_custom_payout_thresholds_respected():
    consensus = calculate_consensus([0.60, 0.61, 0.59, 0.60, 0.60])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=2.20, commission=0.0),
            payout_policy_thresholds=PayoutPolicyThresholds(
                normal_min_decimal_odds=3.00, preferred_min_decimal_odds=3.00, preferred_max_decimal_odds=5.00
            ),
        )
    )
    assert result.market_record.grade == "C"
