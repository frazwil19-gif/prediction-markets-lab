import json

import pytest

from prediction_markets_lab.backtesting.frozen_strategy import load_and_freeze_current_strategy
from prediction_markets_lab.backtesting.replay import BacktestCandidate, ReplayRun
from prediction_markets_lab.backtesting.historical_loader import LoadReport
from prediction_markets_lab.backtesting.report import (
    build_manifest,
    build_performance_report,
    probability_band_for,
    write_backtest_outputs,
)


@pytest.fixture(scope="module")
def strategy():
    return load_and_freeze_current_strategy()


def _candidate(**overrides):
    base = dict(
        match_id="m1", selection="home", event_date="2020-09-12", competition_code="E0",
        competition_name="Premier League", season="2020_21", home_team="A", away_team="B",
        accepted_bookmaker_count=5, consensus_probability=0.6, decimal_odds=1.8, venue="B365",
        net_ev=0.05, probability_edge_pp=3.0, confidence_label="High", data_quality_ok=True,
        research_grade="A", money_decision="PAPER_ONLY", money_qualified=False, money_rejection_reason="",
        recommended_stake_gbp=0.0, actual_won=True, kickoff_iso="2020-09-12T15:00:00+00:00",
        scan_timestamp_iso="2020-09-12T14:00:00+00:00",
    )
    base.update(overrides)
    return BacktestCandidate(**base)


def test_probability_band_boundaries():
    assert probability_band_for(0.10) == "<50%"
    assert probability_band_for(0.499) == "<50%"
    assert probability_band_for(0.50) == "50-54.9%"
    assert probability_band_for(0.549) == "50-54.9%"
    assert probability_band_for(0.55) == "55-59.9%"
    assert probability_band_for(0.80) == "80%+"
    assert probability_band_for(1.0) == "80%+"


def test_performance_report_handles_zero_money_qualified_bets_honestly(strategy):
    """The governing instruction requires 'NO MONEY BETS QUALIFIED TODAY',
    never a fabricated bet, when nothing qualifies -- the backtest report
    must handle this the same way, not error or synthesize a fake bet."""
    candidates = [_candidate(money_qualified=False, money_decision="PAPER_ONLY")]
    run = ReplayRun(
        price_timing="closing", apply_risk_gates=True, frozen_strategy=strategy,
        load_report=LoadReport(1, 0, 0, 0, 1), candidates=candidates,
        starting_bankroll_gbp=10.0, ending_bankroll_gbp=10.0,
    )
    report = build_performance_report(run)
    assert report["betting_performance"]["overall"]["n_bets"] == 0
    assert "note" in report["betting_performance"]["overall"]
    # Must not raise despite zero staked bets, and must be JSON-serialisable.
    json.dumps(report)


def test_performance_report_computes_real_metrics_when_bets_exist(strategy):
    won = _candidate(
        match_id="w1", money_qualified=True, money_decision="BET", staked_gbp=0.25,
        net_change_gbp=0.25 * (1.8 - 1), bankroll_after_gbp=10.20, actual_won=True,
    )
    lost = _candidate(
        match_id="l1", money_qualified=True, money_decision="BET", staked_gbp=0.25,
        net_change_gbp=-0.25, bankroll_after_gbp=9.95, actual_won=False,
    )
    run = ReplayRun(
        price_timing="closing", apply_risk_gates=True, frozen_strategy=strategy,
        load_report=LoadReport(2, 0, 0, 0, 2), candidates=[won, lost],
        starting_bankroll_gbp=10.0, ending_bankroll_gbp=9.95,
    )
    report = build_performance_report(run)
    overall = report["betting_performance"]["overall"]
    assert overall["n_bets"] == 2
    assert overall["n_won"] == 1
    assert overall["n_lost"] == 1
    assert overall["win_rate"] == pytest.approx(0.5)
    assert overall["total_staked_gbp"] == pytest.approx(0.5)
    json.dumps(report)


def test_manifest_records_config_hash_and_coverage(strategy):
    run = ReplayRun(
        price_timing="closing", apply_risk_gates=True, frozen_strategy=strategy,
        load_report=LoadReport(10, 1, 2, 0, 7), candidates=[_candidate()],
        starting_bankroll_gbp=10.0, ending_bankroll_gbp=10.0,
    )
    manifest = build_manifest(run, "test-run-001", "unit test dataset")
    assert manifest["strategy"]["config_hash"] == strategy.config_hash
    assert manifest["coverage"]["matches_included"] == 7
    json.dumps(manifest)


def test_write_backtest_outputs_creates_every_expected_file(strategy, tmp_path):
    run = ReplayRun(
        price_timing="closing", apply_risk_gates=True, frozen_strategy=strategy,
        load_report=LoadReport(1, 0, 0, 0, 1), candidates=[_candidate()],
        starting_bankroll_gbp=10.0, ending_bankroll_gbp=10.0,
    )
    written = write_backtest_outputs(run, "test-run-002", "unit test dataset", tmp_path)
    for kind in ("manifest", "predictions", "bets", "bankroll", "performance", "calibration", "report"):
        assert kind in written
        assert written[kind].exists()
    assert written["manifest"].parent.name == "test-run-002"
    assert written["manifest"].parent.parent.name == strategy.strategy_name


def test_idempotent_rerun_produces_identical_manifest_hash(strategy, tmp_path):
    """Re-running the report writer twice on the same ReplayRun must never
    silently duplicate or drift the recorded config hash."""
    run = ReplayRun(
        price_timing="closing", apply_risk_gates=True, frozen_strategy=strategy,
        load_report=LoadReport(1, 0, 0, 0, 1), candidates=[_candidate()],
        starting_bankroll_gbp=10.0, ending_bankroll_gbp=10.0,
    )
    written_first = write_backtest_outputs(run, "test-run-003", "unit test dataset", tmp_path)
    manifest_first = json.loads(written_first["manifest"].read_text())
    written_second = write_backtest_outputs(run, "test-run-003", "unit test dataset", tmp_path)
    manifest_second = json.loads(written_second["manifest"].read_text())
    assert manifest_first["strategy"]["config_hash"] == manifest_second["strategy"]["config_hash"]
