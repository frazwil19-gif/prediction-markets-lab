"""Tests for decisions.data_quality (Daily Engine V1 build, 2026-09-18)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.decisions.data_quality import (
    DataQualityThresholds,
    assess_data_quality,
)


def test_ok_when_enough_bookmakers_and_fresh_quote():
    thresholds = DataQualityThresholds(min_bookmakers=3, max_quote_age_minutes=60.0)
    result = assess_data_quality(bookmaker_count=5, quote_age_minutes=10.0, thresholds=thresholds)
    assert result.ok
    assert result.reasons == []


def test_fails_when_too_few_bookmakers():
    thresholds = DataQualityThresholds(min_bookmakers=3, max_quote_age_minutes=60.0)
    result = assess_data_quality(bookmaker_count=2, quote_age_minutes=10.0, thresholds=thresholds)
    assert not result.ok
    assert any("bookmaker" in r for r in result.reasons)


def test_fails_when_quote_is_stale():
    thresholds = DataQualityThresholds(min_bookmakers=3, max_quote_age_minutes=60.0)
    result = assess_data_quality(bookmaker_count=5, quote_age_minutes=120.0, thresholds=thresholds)
    assert not result.ok
    assert any("old" in r for r in result.reasons)


def test_reports_both_reasons_when_both_fail():
    thresholds = DataQualityThresholds(min_bookmakers=3, max_quote_age_minutes=60.0)
    result = assess_data_quality(bookmaker_count=1, quote_age_minutes=999.0, thresholds=thresholds)
    assert not result.ok
    assert len(result.reasons) == 2


def test_boundary_values_pass():
    thresholds = DataQualityThresholds(min_bookmakers=3, max_quote_age_minutes=60.0)
    result = assess_data_quality(bookmaker_count=3, quote_age_minutes=60.0, thresholds=thresholds)
    assert result.ok


def test_raises_on_negative_quote_age():
    with pytest.raises(ValueError, match="quote_age_minutes"):
        assess_data_quality(3, -1.0, DataQualityThresholds())


def test_thresholds_reject_invalid_values():
    with pytest.raises(ValueError, match="min_bookmakers"):
        DataQualityThresholds(min_bookmakers=0)
    with pytest.raises(ValueError, match="max_quote_age_minutes"):
        DataQualityThresholds(max_quote_age_minutes=0)
