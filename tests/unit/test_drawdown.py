"""Tests for performance.drawdown (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

from prediction_markets_lab.performance.drawdown import (
    bankroll_curve,
    compute_drawdown,
    longest_losing_streak,
)


def test_bankroll_curve():
    curve = bankroll_curve(10.0, [1.0, -2.0, 3.0])
    assert curve == [11.0, 9.0, 12.0]


def test_compute_drawdown_basic():
    report = compute_drawdown(10.0, [2.0, -5.0, 1.0])  # curve: 12, 7, 8; peak 12
    assert report.max_drawdown_gbp == 5.0
    assert round(report.max_drawdown_pct, 4) == round(5.0 / 12.0, 4)
    assert report.ending_balance_gbp == 8.0
    assert report.peak_balance_gbp == 12.0


def test_compute_drawdown_empty_sequence():
    report = compute_drawdown(10.0, [])
    assert report.max_drawdown_gbp == 0.0
    assert report.ending_balance_gbp == 10.0
    assert report.peak_balance_gbp == 10.0


def test_longest_losing_streak():
    assert longest_losing_streak(["won", "lost", "lost", "void", "lost", "lost", "lost", "won"]) == 3
    assert longest_losing_streak([]) == 0
    assert longest_losing_streak(["won", "won"]) == 0
