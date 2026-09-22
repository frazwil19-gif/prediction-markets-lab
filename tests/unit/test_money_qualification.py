"""Tests for decisions.money_qualification (TARGETED PRODUCTION CHANGE --
DAILY MONEY WINDOW + MONEY/PAPER SEPARATION, 2026-09-22).

Covers the instruction's own named commissioning scenarios (Section 14).
"""

from __future__ import annotations

from prediction_markets_lab.decisions.money_qualification import (
    MoneyQualificationThresholds,
    assess_money_qualification,
)
from prediction_markets_lab.decisions.payout_policy import PayoutPolicyThresholds


def _assess(**overrides):
    kwargs = dict(
        research_grade="A",
        estimated_probability=0.65,
        confidence_label="High",
        data_quality_ok=True,
        decimal_odds=1.80,
        net_ev=0.06,
        kickoff_iso="2026-09-22T18:00:00+00:00",
        scan_timestamp_iso="2026-09-22T09:00:00+00:00",
        payout_policy_thresholds=PayoutPolicyThresholds(),
        thresholds=MoneyQualificationThresholds(),
    )
    kwargs.update(overrides)
    return assess_money_qualification(**kwargs)


# 1. kickoff inside 24h qualifies -----------------------------------------


def test_kickoff_inside_horizon_qualifies_when_everything_else_is_strong():
    result = _assess(kickoff_iso="2026-09-22T18:00:00+00:00", scan_timestamp_iso="2026-09-22T09:00:00+00:00")
    assert result.money_qualified is True
    assert result.money_decision == "BET"
    assert result.money_rejection_reasons == []


# 2. kickoff outside 24h fails ---------------------------------------------


def test_kickoff_outside_horizon_fails():
    result = _assess(
        kickoff_iso="2026-10-18T15:00:00+00:00",
        scan_timestamp_iso="2026-09-22T09:00:00+00:00",
    )
    assert result.money_qualified is False
    assert any("money-event horizon" in r for r in result.money_rejection_reasons)
    # Everything else about this candidate was strong -- only the horizon
    # failed -- so it should resurface as WATCH, not be buried as PAPER_ONLY.
    assert result.money_decision == "WATCH"


def test_kickoff_outside_horizon_with_other_failures_is_paper_only_not_watch():
    result = _assess(
        kickoff_iso="2026-10-18T15:00:00+00:00",
        scan_timestamp_iso="2026-09-22T09:00:00+00:00",
        estimated_probability=0.30,
    )
    assert result.money_qualified is False
    assert result.money_decision == "PAPER_ONLY"


# 3. past kickoff fails ------------------------------------------------------


def test_past_kickoff_fails():
    result = _assess(
        kickoff_iso="2026-09-21T18:00:00+00:00",
        scan_timestamp_iso="2026-09-22T09:00:00+00:00",
    )
    assert result.money_qualified is False
    assert any("not after the scan timestamp" in r for r in result.money_rejection_reasons)


def test_missing_kickoff_fails():
    result = _assess(kickoff_iso=None)
    assert result.money_qualified is False
    assert any("kickoff timestamp is unavailable" in r for r in result.money_rejection_reasons)


# 4. timezone handling --------------------------------------------------------


def test_zulu_suffix_and_offset_timestamps_agree():
    zulu = _assess(kickoff_iso="2026-09-22T18:00:00Z", scan_timestamp_iso="2026-09-22T09:00:00Z")
    offset = _assess(kickoff_iso="2026-09-22T18:00:00+00:00", scan_timestamp_iso="2026-09-22T09:00:00+00:00")
    assert zulu.money_qualified == offset.money_qualified is True


def test_naive_timestamps_are_treated_as_utc():
    naive = _assess(kickoff_iso="2026-09-22T18:00:00", scan_timestamp_iso="2026-09-22T09:00:00")
    assert naive.money_qualified is True


def test_non_utc_offset_is_correctly_converted():
    # 19:00 in UTC+1 is 18:00 UTC -- 9h after a 09:00 UTC scan, same as the
    # baseline strong candidate above, and must qualify identically.
    result = _assess(kickoff_iso="2026-09-22T19:00:00+01:00", scan_timestamp_iso="2026-09-22T09:00:00+00:00")
    assert result.money_qualified is True


# 5. low-probability high-odds candidate stays research/paper, not money ------


def test_low_probability_high_odds_longshot_is_paper_only():
    # The operator's own cited examples: Ipswich (a) v Man City-style,
    # ~7.8% at 14.00 -- legitimate research/paper, never a money bet.
    result = _assess(
        research_grade="B",
        estimated_probability=0.078,
        decimal_odds=14.00,
        net_ev=0.09,
        confidence_label="Medium",
    )
    assert result.money_qualified is False
    assert result.money_decision == "PAPER_ONLY"
    assert any("probability" in r for r in result.money_rejection_reasons)


# 6. high-probability tiny-payout candidate fails the payout gate -------------


def test_high_probability_tiny_payout_fails_payout_gate():
    result = _assess(estimated_probability=0.95, decimal_odds=1.10, net_ev=0.03)
    assert result.money_qualified is False
    assert any("payout floor" in r for r in result.money_rejection_reasons)


# 7. high-probability acceptable-payout candidate can qualify -----------------


def test_high_probability_acceptable_payout_can_qualify():
    result = _assess(estimated_probability=0.60, decimal_odds=1.80, net_ev=0.05, confidence_label="High")
    assert result.money_qualified is True
    assert result.money_decision == "BET"


# 8. low-confidence candidate cannot normally qualify --------------------------


def test_low_confidence_cannot_qualify():
    result = _assess(confidence_label="Low", estimated_probability=0.80, net_ev=0.10, decimal_odds=2.00)
    assert result.money_qualified is False
    assert any("not eligible for real-money qualification" in r for r in result.money_rejection_reasons)
    assert result.money_decision == "PAPER_ONLY"


def test_medium_confidence_qualifies_only_when_every_other_requirement_is_strong():
    weak_medium = _assess(confidence_label="Medium", estimated_probability=0.55, net_ev=0.03, decimal_odds=1.80)
    assert weak_medium.money_qualified is False

    strong_medium = _assess(confidence_label="Medium", estimated_probability=0.65, net_ev=0.06, decimal_odds=1.80)
    assert strong_medium.money_qualified is True
    assert strong_medium.money_decision == "BET"


def test_medium_confidence_outside_preferred_odds_band_fails():
    result = _assess(
        confidence_label="Medium", estimated_probability=0.70, net_ev=0.08, decimal_odds=1.35,
    )
    assert result.money_qualified is False
    assert any("preferred range" in r for r in result.money_rejection_reasons)


# 9. negative-value high-probability candidate cannot qualify -----------------


def test_negative_value_high_probability_cannot_qualify():
    result = _assess(estimated_probability=0.90, net_ev=-0.02, decimal_odds=1.50)
    assert result.money_qualified is False
    assert any("value floor" in r for r in result.money_rejection_reasons)


# 10. research grade preserved after money rejection ---------------------------


def test_research_grade_is_never_recomputed_or_overwritten(monkeypatch=None):
    result = _assess(estimated_probability=0.20)
    # This module never returns or mutates a grade -- it only ever reads
    # research_grade as an input. Confirm rejection is driven purely by
    # money-specific reasons, with no grade field anywhere in the result.
    assert not hasattr(result, "research_grade")
    assert not hasattr(result, "grade")
    assert result.money_qualified is False


def test_grade_c_and_reject_are_never_actionable_for_money():
    c_grade = _assess(research_grade="C")
    reject_grade = _assess(research_grade="Reject")
    assert c_grade.money_qualified is False
    assert c_grade.money_decision == "REJECT"
    assert reject_grade.money_qualified is False
    assert reject_grade.money_decision == "REJECT"


# Multiple simultaneous failures are all recorded, never just the first -------


def test_every_failing_gate_is_recorded_not_just_the_first():
    result = _assess(
        kickoff_iso="2026-10-18T15:00:00+00:00",
        estimated_probability=0.10,
        decimal_odds=1.05,
        net_ev=-0.05,
    )
    assert len(result.money_rejection_reasons) >= 3


def test_thresholds_reject_looser_medium_than_high_configuration():
    import pytest

    with pytest.raises(ValueError):
        MoneyQualificationThresholds(min_probability=0.50, min_probability_medium_confidence=0.40)
    with pytest.raises(ValueError):
        MoneyQualificationThresholds(min_net_ev=0.05, min_net_ev_medium_confidence=0.02)
