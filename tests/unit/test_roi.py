"""Tests for performance.roi (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

from prediction_markets_lab.performance.roi import roi_fraction


def test_roi_positive():
    assert roi_fraction(10.0, 2.0) == 0.2


def test_roi_negative():
    assert roi_fraction(10.0, -3.0) == -0.3


def test_roi_zero_staked_returns_none():
    assert roi_fraction(0.0, 0.0) is None
