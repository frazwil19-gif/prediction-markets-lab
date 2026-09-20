"""Tests for performance.odds_bands (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.performance.odds_bands import band_for_odds


def test_bands_cover_documented_ranges():
    assert band_for_odds(1.01) == "1.01-1.19"
    assert band_for_odds(1.19) == "1.01-1.19"
    assert band_for_odds(1.20) == "1.20-1.32"
    assert band_for_odds(1.33) == "1.33-1.49"
    assert band_for_odds(1.50) == "1.50-1.74"
    assert band_for_odds(1.75) == "1.75-1.99"
    assert band_for_odds(2.00) == "2.00-2.49"
    assert band_for_odds(2.50) == "2.50+"
    assert band_for_odds(10.0) == "2.50+"


def test_below_lowest_band_raises():
    with pytest.raises(ValueError):
        band_for_odds(1.00)
