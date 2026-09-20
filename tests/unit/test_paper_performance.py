"""Tests for performance.paper_performance (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

from prediction_markets_lab.performance.paper_performance import build_performance_report


def _row(**overrides) -> dict:
    base = {
        "bet_id": "b1",
        "grade": "A",
        "sport": "football",
        "competition": "Premier League",
        "market": "1x2",
        "selection": "home",
        "quoted_odds": "2.20",
        "estimated_probability": "0.55",
        "recommended_stake": "0.25",
        "status": "settled",
        "result": "won",
        "actual_pnl": "0.30",
        "paper_bankroll_after_settlement": "10.30",
    }
    base.update(overrides)
    return base


def test_report_basic_totals():
    rows = [
        _row(),
        _row(
            bet_id="b2",
            result="lost",
            actual_pnl="-0.25",
            paper_bankroll_after_settlement="10.05",
        ),
    ]
    report = build_performance_report(rows, starting_bankroll_gbp=10.0)
    assert report["overall"]["bet_count"] == 2
    assert report["overall"]["decided_count"] == 2
    assert report["overall"]["win_rate"] == 0.5
    assert report["current_paper_bankroll_gbp"] == 10.05


def test_pending_bets_excluded_from_settled_metrics():
    rows = [_row(), _row(bet_id="b2", status="pending", result="", actual_pnl="", paper_bankroll_after_settlement="")]
    report = build_performance_report(rows, starting_bankroll_gbp=10.0)
    assert report["pending_bet_count"] == 1
    assert report["overall"]["bet_count"] == 1


def test_by_grade_and_odds_band_breakdowns_present():
    rows = [_row()]
    report = build_performance_report(rows, starting_bankroll_gbp=10.0)
    assert "A" in report["by_grade"]
    assert "2.00-2.49" in report["by_odds_band"]


def test_void_bet_excluded_from_win_rate_but_counted_in_stake():
    rows = [_row(bet_id="b3", result="void", actual_pnl="0.00", paper_bankroll_after_settlement="10.00")]
    report = build_performance_report(rows, starting_bankroll_gbp=10.0)
    assert report["overall"]["decided_count"] == 0
    assert report["overall"]["win_rate"] is None
    assert report["overall"]["bet_count"] == 1


def test_empty_ledger_does_not_crash():
    report = build_performance_report([], starting_bankroll_gbp=10.0)
    assert report["overall"]["bet_count"] == 0
    assert report["current_paper_bankroll_gbp"] == 10.0
