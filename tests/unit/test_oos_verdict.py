"""Tests for oos_verdict.py -- boundary cases for the mechanical
PASS/PARTIAL/FAIL rule governing H-FB2-002's sealed 2025/26 OOS test,
mirroring the discipline used in test_holdout_verdict.py and
test_development_verdict.py.
"""

from __future__ import annotations

import pytest

from prediction_markets_lab.research.oos_verdict import (
    FROZEN_COMPETITIONS,
    SealedOOSVerdictInput,
    classify_sealed_oos_result,
)


def _pass_evidence(**overrides) -> SealedOOSVerdictInput:
    base = dict(
        ci_lower=0.03,
        ci_upper=0.15,
        point_estimate=0.09,
        n_top_quintile=150,
        competitions_present=frozenset({"E0", "E1", "SC0"}),
        min_n=100,
    )
    base.update(overrides)
    return SealedOOSVerdictInput(**base)


def test_pass_when_everything_clears():
    result = classify_sealed_oos_result(_pass_evidence())
    assert result.verdict == "PASS"


def test_ci_lower_bound_greater_than_zero_is_favourable():
    result = classify_sealed_oos_result(_pass_evidence(ci_lower=0.0001, ci_upper=0.2))
    assert result.verdict == "PASS"


def test_ci_lower_bound_exactly_zero_is_fail_not_partial():
    # A CI that merely touches zero is FAIL for this one-shot test --
    # there is no inconclusive category.
    result = classify_sealed_oos_result(_pass_evidence(ci_lower=0.0, ci_upper=0.15))
    assert result.verdict == "FAIL"
    assert "does not lie entirely above zero" in result.reason


def test_ci_lower_bound_less_than_zero_is_fail():
    result = classify_sealed_oos_result(_pass_evidence(ci_lower=-0.02, ci_upper=0.10))
    assert result.verdict == "FAIL"


def test_ci_entirely_negative_is_fail():
    result = classify_sealed_oos_result(
        _pass_evidence(ci_lower=-0.15, ci_upper=-0.03, point_estimate=-0.09)
    )
    assert result.verdict == "FAIL"


def test_positive_point_estimate_but_ci_includes_zero_is_fail():
    result = classify_sealed_oos_result(
        _pass_evidence(ci_lower=-0.01, ci_upper=0.05, point_estimate=0.02)
    )
    assert result.verdict == "FAIL"


def test_zero_point_estimate_is_fail():
    result = classify_sealed_oos_result(
        _pass_evidence(ci_lower=-0.03, ci_upper=0.03, point_estimate=0.0)
    )
    assert result.verdict == "FAIL"


def test_negative_point_estimate_is_fail():
    result = classify_sealed_oos_result(
        _pass_evidence(ci_lower=-0.20, ci_upper=-0.05, point_estimate=-0.12)
    )
    assert result.verdict == "FAIL"


def test_minimum_n_exactly_met_is_pass():
    result = classify_sealed_oos_result(_pass_evidence(n_top_quintile=100, min_n=100))
    assert result.verdict == "PASS"


def test_minimum_n_one_below_requirement_is_partial():
    result = classify_sealed_oos_result(_pass_evidence(n_top_quintile=99, min_n=100))
    assert result.verdict == "PARTIAL"
    assert "below the pre-registered floor" in result.reason


def test_missing_competition_is_partial_population_deviation():
    result = classify_sealed_oos_result(
        _pass_evidence(competitions_present=frozenset({"E0", "E1"}))
    )
    assert result.verdict == "PARTIAL"
    assert "population deviation" in result.reason
    assert "SC0" in result.reason


def test_missing_competition_dominates_even_a_favourable_result():
    # Population deviation is checked first: even an otherwise-clean
    # PASS-shaped result must not be reported as PASS if a whole
    # competition's 2025/26 data never arrived.
    result = classify_sealed_oos_result(
        _pass_evidence(
            competitions_present=frozenset({"E0", "SC0"}),
            ci_lower=0.05,
            ci_upper=0.20,
            n_top_quintile=500,
        )
    )
    assert result.verdict == "PARTIAL"
    assert "E1" in result.reason


def test_missing_competition_dominates_even_a_fail_shaped_result():
    # Population deviation also takes precedence over what would
    # otherwise be a FAIL -- the verdict is PARTIAL either way, not FAIL.
    result = classify_sealed_oos_result(
        _pass_evidence(competitions_present=frozenset({"E1", "SC0"}), ci_lower=-0.10, ci_upper=-0.01)
    )
    assert result.verdict == "PARTIAL"
    assert "E0" in result.reason


def test_all_frozen_competitions_present_but_none_extra_required():
    # Extra/unexpected competition codes present alongside the three
    # frozen ones do not themselves cause a population deviation.
    result = classify_sealed_oos_result(
        _pass_evidence(competitions_present=frozenset({"E0", "E1", "SC0", "D1"}))
    )
    assert result.verdict == "PASS"


def test_competition_level_sample_skew_does_not_gate_the_verdict():
    # The classifier's gate is aggregate-only: it takes no per-
    # competition sample-size input at all, so an extremely skewed
    # competition contribution to the top quintile (e.g. one league
    # supplying only a handful of matches) cannot, by construction,
    # change a PASS to anything else as long as all three competitions'
    # raw season data was acquired (population-completeness satisfied).
    # Competition-by-competition breakdowns are diagnostics reported
    # alongside this verdict, never inputs to it (protocol section 17.3).
    result = classify_sealed_oos_result(_pass_evidence())
    assert result.verdict == "PASS"


def test_frozen_competitions_constant_is_exactly_three_leagues():
    assert FROZEN_COMPETITIONS == frozenset({"E0", "E1", "SC0"})


def test_zero_width_ci_strictly_positive_is_pass():
    result = classify_sealed_oos_result(_pass_evidence(ci_lower=0.02, ci_upper=0.02, point_estimate=0.02))
    assert result.verdict == "PASS"


def test_zero_width_ci_at_zero_is_fail():
    result = classify_sealed_oos_result(_pass_evidence(ci_lower=0.0, ci_upper=0.0, point_estimate=0.0))
    assert result.verdict == "FAIL"


def test_rejects_invalid_ci_bounds():
    with pytest.raises(ValueError):
        SealedOOSVerdictInput(
            ci_lower=0.5,
            ci_upper=0.1,
            point_estimate=0.2,
            n_top_quintile=150,
            competitions_present=frozenset({"E0", "E1", "SC0"}),
        )


def test_rejects_negative_sample_size():
    with pytest.raises(ValueError):
        SealedOOSVerdictInput(
            ci_lower=0.01,
            ci_upper=0.10,
            point_estimate=0.05,
            n_top_quintile=-1,
            competitions_present=frozenset({"E0", "E1", "SC0"}),
        )


def test_rejects_non_positive_min_n():
    with pytest.raises(ValueError):
        SealedOOSVerdictInput(
            ci_lower=0.01,
            ci_upper=0.10,
            point_estimate=0.05,
            n_top_quintile=150,
            competitions_present=frozenset({"E0", "E1", "SC0"}),
            min_n=0,
        )
