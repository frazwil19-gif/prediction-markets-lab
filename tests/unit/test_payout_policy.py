"""Tests for decisions.payout_policy (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

import pytest

from prediction_markets_lab.decisions.payout_policy import PayoutPolicyThresholds, apply_payout_floor


def test_default_thresholds_valid():
    t = PayoutPolicyThresholds()
    assert t.normal_min_decimal_odds == 1.33
    assert t.preferred_min_decimal_odds == 1.40
    assert t.preferred_max_decimal_odds == 2.50


def test_normal_floor_must_exceed_one():
    with pytest.raises(ValueError):
        PayoutPolicyThresholds(normal_min_decimal_odds=0.9)


def test_preferred_min_cannot_be_below_normal_min():
    with pytest.raises(ValueError):
        PayoutPolicyThresholds(preferred_min_decimal_odds=1.0, normal_min_decimal_odds=1.33)


def test_preferred_max_cannot_be_below_preferred_min():
    with pytest.raises(ValueError):
        PayoutPolicyThresholds(preferred_max_decimal_odds=1.0, preferred_min_decimal_odds=1.40)


def test_grade_a_below_floor_demoted_to_c():
    grade, reason = apply_payout_floor("A", "strong edge", 1.10, PayoutPolicyThresholds())
    assert grade == "C"
    assert "payout floor" in reason


def test_grade_above_floor_unchanged():
    grade, reason = apply_payout_floor("A", "strong edge", 2.20, PayoutPolicyThresholds())
    assert grade == "A"
    assert reason == "strong edge"


def test_grade_c_never_touched():
    grade, reason = apply_payout_floor("C", "watch", 1.05, PayoutPolicyThresholds())
    assert grade == "C"
    assert reason == "watch"


def test_reject_never_touched():
    grade, reason = apply_payout_floor("Reject", "bad ev", 1.05, PayoutPolicyThresholds())
    assert grade == "Reject"
    assert reason == "bad ev"


def test_grade_b_at_exact_floor_not_demoted():
    grade, _ = apply_payout_floor("B", "ok edge", 1.33, PayoutPolicyThresholds())
    assert grade == "B"
