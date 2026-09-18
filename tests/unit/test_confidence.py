"""Tests for decisions.confidence (Daily Engine V1 build, 2026-09-18)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.decisions.confidence import (
    ConfidenceThresholds,
    assess_confidence,
)


def test_high_confidence_when_many_bookmakers_agree_closely():
    thresholds = ConfidenceThresholds()
    assert assess_confidence(6, 0.01, thresholds) == "High"


def test_medium_confidence_with_moderate_support():
    thresholds = ConfidenceThresholds()
    assert assess_confidence(4, 0.03, thresholds) == "Medium"


def test_low_confidence_with_thin_or_disagreeing_input():
    thresholds = ConfidenceThresholds()
    assert assess_confidence(2, 0.10, thresholds) == "Low"
    assert assess_confidence(6, 0.10, thresholds) == "Low"


def test_boundary_values_are_inclusive():
    thresholds = ConfidenceThresholds(
        high_min_bookmakers=5, high_max_std_dev=0.02, medium_min_bookmakers=3, medium_max_std_dev=0.05
    )
    assert assess_confidence(5, 0.02, thresholds) == "High"
    assert assess_confidence(3, 0.05, thresholds) == "Medium"


def test_raises_on_invalid_bookmaker_count():
    with pytest.raises(ValueError, match="bookmaker_count"):
        assess_confidence(0, 0.01, ConfidenceThresholds())


def test_raises_on_negative_std_dev():
    with pytest.raises(ValueError, match="consensus_std_dev"):
        assess_confidence(5, -0.01, ConfidenceThresholds())


def test_thresholds_reject_inconsistent_bookmaker_ordering():
    with pytest.raises(ValueError, match="high_min_bookmakers"):
        ConfidenceThresholds(high_min_bookmakers=2, medium_min_bookmakers=3)


def test_thresholds_reject_inconsistent_std_dev_ordering():
    with pytest.raises(ValueError, match="high_max_std_dev"):
        ConfidenceThresholds(high_max_std_dev=0.10, medium_max_std_dev=0.05)
