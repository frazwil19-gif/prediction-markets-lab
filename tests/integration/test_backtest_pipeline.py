"""End-to-end integration test: real Cycle 1 data, through the actual
production decision pipeline, to a full report output set.

This is the only test in the suite that exercises the whole chain against
the real repository dataset -- deliberately kept to a small slice
(one season) for speed, since tests/unit already covers the individual
stages against synthetic fixtures and the real data's own coverage
properties.
"""

from __future__ import annotations

import json

import pytest

from prediction_markets_lab.backtesting.frozen_strategy import load_and_freeze_current_strategy
from prediction_markets_lab.backtesting import historical_loader as _hl
from prediction_markets_lab.backtesting.historical_loader import load_matches_for_replay
from prediction_markets_lab.backtesting.replay import build_candidates, simulate_bankroll, ReplayRun
from prediction_markets_lab.backtesting.report import write_backtest_outputs


# Real-data test: the processed Cycle 1 files are gitignored (regenerable, not committed), so they
# are absent on a clean GitHub Actions checkout. Skip there rather than fail the whole suite --
# this was silently failing CI (and therefore every scheduled workflow's test step) since 2026-09-22.
@pytest.mark.skipif(not (_hl.CYCLE_001_MATCHES.exists() and _hl.CYCLE_001_BOOKMAKER_MARKETS.exists()),
                    reason="processed Cycle 1 data not present (gitignored; local-only)")
def test_full_pipeline_on_one_real_season_produces_a_valid_report(tmp_path):
    strategy = load_and_freeze_current_strategy()
    matches, load_report = load_matches_for_replay("closing")
    one_season = [m for m in matches if m.season == "2020_21" and m.competition_code == "E0"]
    assert len(one_season) > 300  # a real Premier League season

    candidates, excluded = build_candidates(one_season, strategy)
    assert len(candidates) == len(one_season) * 3  # home/draw/away per match
    assert excluded == []  # every 2020_21 E0 match has a complete bookmaker panel

    settled, ending_bankroll, exhausted, exhausted_at = simulate_bankroll(
        candidates, strategy, apply_risk_gates=True
    )
    assert len(settled) == len(candidates)

    run = ReplayRun(
        price_timing="closing",
        apply_risk_gates=True,
        frozen_strategy=strategy,
        load_report=load_report,
        candidates=settled,
        starting_bankroll_gbp=strategy.bankroll["starting_bankroll_gbp"],
        ending_bankroll_gbp=ending_bankroll,
        bankroll_exhausted=exhausted,
        bankroll_exhausted_at_match_id=exhausted_at,
    )
    written = write_backtest_outputs(run, "integration-test-run", "E0 2020_21 only (test)", tmp_path)

    manifest = json.loads(written["manifest"].read_text())
    # load_report reflects the full dataset load (not the one-season slice
    # replayed here) -- assert on the strategy/hash fields this manifest is
    # actually responsible for recording instead of coverage counts.
    assert manifest["strategy"]["config_hash"] == strategy.config_hash
    assert manifest["run_id"] == "integration-test-run"

    performance = json.loads(written["performance"].read_text())
    assert performance["probability_quality"]["all_candidates"]["n"] == len(candidates)
    # Report must never fabricate a bet where none qualified/exists.
    if performance["betting_performance"]["overall"]["n_bets"] == 0:
        assert "note" in performance["betting_performance"]["overall"]

    assert "PROXY BACKTEST" in written["report"].read_text()
