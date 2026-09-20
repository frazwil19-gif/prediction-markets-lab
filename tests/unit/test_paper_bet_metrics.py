"""Tests for performance.paper_bet_metrics (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

import math

from prediction_markets_lab.performance.paper_bet_metrics import (
    binary_brier_score,
    binary_log_loss,
    mean_binary_brier_score,
    mean_binary_log_loss,
)


def test_binary_brier_perfect_and_worst():
    assert binary_brier_score(1.0, True) == 0.0
    assert binary_brier_score(0.0, True) == 1.0


def test_binary_log_loss_matches_formula():
    assert math.isclose(binary_log_loss(0.5, True), -math.log(0.5))
    assert math.isclose(binary_log_loss(0.5, False), -math.log(0.5))


def test_mean_functions_handle_empty_and_mismatch():
    assert mean_binary_brier_score([], []) is None
    assert mean_binary_log_loss([0.5], [True, False]) is None


def test_mean_binary_brier_basic():
    assert mean_binary_brier_score([1.0, 0.0], [True, True]) == 0.5
