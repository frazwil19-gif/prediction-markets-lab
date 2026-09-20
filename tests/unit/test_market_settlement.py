"""Tests for settlement.market_settlement (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.settlement.market_settlement import (
    compute_pnl_gbp,
    determine_1x2_result,
    determine_over_under_result,
    determine_result,
)


def test_1x2_home_draw_away():
    assert determine_1x2_result(2, 1) == "home"
    assert determine_1x2_result(1, 2) == "away"
    assert determine_1x2_result(1, 1) == "draw"


def test_1x2_missing_score_is_void():
    assert determine_1x2_result(None, 1) == "void"


def test_over_under_25():
    assert determine_over_under_result(2, 1, line=2.5) == "over"
    assert determine_over_under_result(1, 1, line=2.5) == "under"


def test_over_under_exact_push_is_void():
    assert determine_over_under_result(2, 1, line=3.0) == "void"


def test_determine_result_dispatch():
    assert determine_result("1x2", 2, 0) == "home"
    assert determine_result("over_under_2_5", 3, 0) == "over"


def test_determine_result_unsupported_market_raises():
    with pytest.raises(ValueError):
        determine_result("asian_handicap", 1, 0)


def test_compute_pnl_win_loss_void():
    assert compute_pnl_gbp(1.0, 2.20, "home", "home") == pytest.approx(1.20)
    assert compute_pnl_gbp(1.0, 2.20, "home", "away") == -1.0
    assert compute_pnl_gbp(1.0, 2.20, "home", "void") == 0.0
