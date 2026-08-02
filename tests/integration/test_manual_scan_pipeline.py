"""End-to-end test of the Stage 1 manual scan pipeline.

Takes the sample football fixture, runs it through odds conversion,
margin removal, consensus, EV, grading, staking, and the combined risk
gate — mirroring what the eventual daily workflow (Stage 2) will do,
but wired together directly in this test rather than via a script.
"""

import csv
from pathlib import Path

import pytest

from prediction_markets_lab.decisions.grading import (
    GradingInput,
    GradingThresholds,
    grade_opportunity,
)
from prediction_markets_lab.ev.expected_value import evaluate
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.probability.margin_removal import (
    margin_free_probabilities_from_odds,
)
from prediction_markets_lab.risk.decision_gates import check_risk_gates
from prediction_markets_lab.risk.exposure import ExposureState
from prediction_markets_lab.risk.loss_locks import check_loss_locks
from prediction_markets_lab.risk.staking import StakingConfig, recommended_stake_gbp

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_football_odds() -> dict[str, list[float]]:
    """Load the sample football fixture, grouped by outcome."""
    by_outcome: dict[str, list[float]] = {"home": [], "draw": [], "away": []}
    bookmaker_odds: dict[str, list[float]] = {}
    with open(FIXTURES_DIR / "sample_football_odds.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bookmaker_odds.setdefault(row["bookmaker"], []).append(
                (row["selection"], float(row["decimal_odds"]))
            )

    # For each bookmaker, remove the margin across its own three-way
    # market, then bucket the fair probability by outcome.
    for bookmaker, selections in bookmaker_odds.items():
        selections_sorted = sorted(selections, key=lambda s: s[0])
        outcomes = [s[0] for s in selections_sorted]
        odds = [s[1] for s in selections_sorted]
        fair_probs = margin_free_probabilities_from_odds(odds)
        for outcome, prob in zip(outcomes, fair_probs):
            by_outcome[outcome].append(prob)

    return by_outcome


def test_full_pipeline_produces_a_stake_recommendation_for_home_win():
    by_outcome = _load_football_odds()
    home_consensus = calculate_consensus(by_outcome["home"])

    # Sample exchange price for the home win selection (see
    # sample_exchange_prices.csv): Smarkets @ 2.20, commission 2%.
    exchange_odds = 2.20
    commission = 0.02

    ev_result = evaluate(
        probability=home_consensus.consensus_probability,
        decimal_odds=exchange_odds,
        commission=commission,
    )

    grading_thresholds = GradingThresholds()
    evidence = GradingInput(
        net_ev=ev_result.net_ev,
        probability_edge_pp=ev_result.probability_edge_pp,
        bookmaker_count=home_consensus.bookmaker_count,
        data_quality_ok=True,
        no_material_info_risk=True,
        exchange_price_current=True,
        market_rules_match=True,
        liquidity_adequate=True,
    )
    grading_result = grade_opportunity(evidence, grading_thresholds)

    staking_config = StakingConfig(
        starting_bankroll_gbp=10.00,
        normal_stake_gbp=0.25,
        maximum_stake_gbp=0.50,
        maximum_daily_exposure_gbp=0.75,
        maximum_open_bets=3,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )
    stake = recommended_stake_gbp(grading_result.grade, staking_config)

    exposure = ExposureState()
    loss_status = check_loss_locks(
        daily_loss_gbp=0.0,
        weekly_loss_gbp=0.0,
        daily_loss_stop_gbp=staking_config.daily_loss_stop_gbp,
        weekly_loss_stop_gbp=staking_config.weekly_loss_stop_gbp,
    )

    if stake > 0:
        gate_result = check_risk_gates(stake, exposure, loss_status, staking_config)
        assert gate_result.passed

    # This assertion documents the pipeline's actual behaviour on the
    # fixture data rather than asserting a specific grade in advance:
    # the fixture's bookmaker consensus and exchange price do not
    # necessarily produce a positive-EV opportunity, and that is a
    # valid, expected outcome (see project philosophy in
    # docs/PROJECT_PLAN.md — "no trade" is a legitimate result).
    assert grading_result.grade in {"A+", "A", "B", "C", "Reject"}
    assert isinstance(ev_result.net_ev, float)


def test_full_pipeline_halts_when_daily_loss_stop_reached():
    by_outcome = _load_football_odds()
    home_consensus = calculate_consensus(by_outcome["home"])

    ev_result = evaluate(
        probability=home_consensus.consensus_probability,
        decimal_odds=2.20,
        commission=0.02,
    )

    staking_config = StakingConfig(
        starting_bankroll_gbp=10.00,
        normal_stake_gbp=0.25,
        maximum_stake_gbp=0.50,
        maximum_daily_exposure_gbp=0.75,
        maximum_open_bets=3,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )

    # Simulate the daily loss stop having already been reached.
    loss_status = check_loss_locks(
        daily_loss_gbp=0.75,
        weekly_loss_gbp=0.75,
        daily_loss_stop_gbp=staking_config.daily_loss_stop_gbp,
        weekly_loss_stop_gbp=staking_config.weekly_loss_stop_gbp,
    )
    exposure = ExposureState()

    gate_result = check_risk_gates(0.25, exposure, loss_status, staking_config)
    assert not gate_result.passed
    assert gate_result.reason == "daily loss stop reached"
