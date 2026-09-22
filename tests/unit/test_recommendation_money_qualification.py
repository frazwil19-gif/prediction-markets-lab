"""Integration tests: decisions.recommendation + decisions.money_qualification
(TARGETED PRODUCTION CHANGE -- DAILY MONEY WINDOW + MONEY/PAPER SEPARATION,
2026-09-22).
"""

from __future__ import annotations

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.money_qualification import MoneyQualificationThresholds
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
        scan_timestamp="2026-09-22T09:00:00+00:00",
        event_date="2026-09-22",
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


def test_strong_near_term_candidate_is_money_qualified_and_bet():
    consensus = calculate_consensus([0.65, 0.66, 0.64, 0.65, 0.65])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=1.80, commission=0.0),
            kickoff_iso="2026-09-22T18:00:00+00:00",
        )
    )
    m = result.market_record
    assert m.grade in ("A+", "A")
    assert m.research_grade == m.grade
    assert m.money_qualified is True
    assert m.money_decision == "BET"
    assert m.money_rejection_reason == ""
    assert m.kickoff_time == "2026-09-22T18:00:00+00:00"


def test_far_future_kickoff_keeps_research_grade_but_fails_money_gate():
    consensus = calculate_consensus([0.65, 0.66, 0.64, 0.65, 0.65])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=1.80, commission=0.0),
            kickoff_iso="2026-10-18T15:00:00+00:00",  # weeks away
        )
    )
    m = result.market_record
    # Research grade is untouched by the money gate.
    assert m.grade in ("A+", "A")
    assert m.research_grade == m.grade
    assert m.money_qualified is False
    assert m.money_decision in ("WATCH", "PAPER_ONLY")
    assert "money-event horizon" in m.money_rejection_reason


def test_missing_kickoff_never_qualifies_but_research_grade_stands():
    consensus = calculate_consensus([0.65, 0.66, 0.64, 0.65, 0.65])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=1.80, commission=0.0),
            # kickoff_iso not passed -- defaults to None, e.g. a manual-mode scan.
        )
    )
    m = result.market_record
    assert m.grade in ("A+", "A")
    assert m.money_qualified is False
    assert m.kickoff_time is None


def test_longshot_stays_actionable_research_grade_but_paper_only_for_money():
    # Low probability, high odds -- can still clear the EV/edge bars (grade
    # B or better) but must never become a money bet.
    consensus = calculate_consensus([0.078, 0.08, 0.075, 0.079])
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=4,
            best_price=PriceQuote(venue="Bet365", decimal_odds=14.00, commission=0.0),
            kickoff_iso="2026-09-22T18:00:00+00:00",
        )
    )
    m = result.market_record
    assert m.money_qualified is False
    if m.grade in ("A+", "A", "B"):
        assert m.money_decision == "PAPER_ONLY"
    else:
        assert m.money_decision == "REJECT"


def test_custom_money_qualification_thresholds_are_respected():
    consensus = calculate_consensus([0.55, 0.56, 0.54, 0.55, 0.55])
    strict = MoneyQualificationThresholds(min_probability=0.90, min_probability_medium_confidence=0.90)
    result = build_recommendation(
        **_common_kwargs(
            consensus=consensus,
            accepted_bookmaker_count=5,
            best_price=PriceQuote(venue="Bet365", decimal_odds=1.80, commission=0.0),
            kickoff_iso="2026-09-22T18:00:00+00:00",
            money_qualification_thresholds=strict,
        )
    )
    assert result.market_record.money_qualified is False
    assert "probability" in result.market_record.money_rejection_reason
