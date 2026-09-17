"""Tests for development_verdict.py -- boundary cases for the mechanical
DEVELOPMENT-PROMOTE/PARTIAL/REJECT rule, mirroring the discipline used in
test_holdout_verdict.py.
"""

from __future__ import annotations

import pytest

from prediction_markets_lab.research.development_verdict import (
    DevelopmentVerdictInput,
    classify_development_result,
)


def _promote_evidence(**overrides) -> DevelopmentVerdictInput:
    base = dict(
        ci_lower=0.02,
        ci_upper=0.10,
        point_estimate=0.06,
        one_sided_positive_required=False,
        n_seasons_same_sign=4,
        n_seasons_tested=5,
        n_floor_met_in_every_reported_season=True,
        single_competition_independent=True,
    )
    base.update(overrides)
    return DevelopmentVerdictInput(**base)


def test_promote_when_everything_clears():
    result = classify_development_result(_promote_evidence())
    assert result.verdict == "DEVELOPMENT-PROMOTE"


def test_reject_when_two_sided_ci_includes_zero():
    result = classify_development_result(_promote_evidence(ci_lower=-0.02, ci_upper=0.10))
    assert result.verdict == "DEVELOPMENT-REJECT"
    assert "CI does not exclude zero" in result.reason


def test_reject_when_one_sided_ci_is_negative_even_if_excludes_zero():
    # CI excludes zero but lies entirely BELOW zero -- wrong direction
    # for a one-sided-positive hypothesis.
    result = classify_development_result(
        _promote_evidence(one_sided_positive_required=True, ci_lower=-0.10, ci_upper=-0.02, point_estimate=-0.06)
    )
    assert result.verdict == "DEVELOPMENT-REJECT"


def test_promote_when_one_sided_ci_entirely_positive():
    result = classify_development_result(
        _promote_evidence(one_sided_positive_required=True, ci_lower=0.01, ci_upper=0.09)
    )
    assert result.verdict == "DEVELOPMENT-PROMOTE"


def test_reject_when_sign_unstable_below_minimum_seasons():
    result = classify_development_result(_promote_evidence(n_seasons_same_sign=2, n_seasons_tested=5))
    assert result.verdict == "DEVELOPMENT-REJECT"
    assert "sign matches" in result.reason


def test_partial_when_sample_floor_not_met_in_every_season():
    result = classify_development_result(_promote_evidence(n_floor_met_in_every_reported_season=False))
    assert result.verdict == "DEVELOPMENT-PARTIAL"


def test_partial_when_single_competition_drives_the_effect():
    result = classify_development_result(_promote_evidence(single_competition_independent=False))
    assert result.verdict == "DEVELOPMENT-PARTIAL"


def test_partial_when_both_secondary_conditions_fail():
    result = classify_development_result(
        _promote_evidence(n_floor_met_in_every_reported_season=False, single_competition_independent=False)
    )
    assert result.verdict == "DEVELOPMENT-PARTIAL"
    assert "and" in result.reason


def test_exact_minimum_seasons_boundary_counts_as_stable():
    result = classify_development_result(_promote_evidence(n_seasons_same_sign=3, n_seasons_tested=5))
    assert result.verdict == "DEVELOPMENT-PROMOTE"


def test_ci_bound_exactly_zero_is_not_favourable_two_sided():
    result = classify_development_result(_promote_evidence(ci_lower=0.0, ci_upper=0.10))
    assert result.verdict == "DEVELOPMENT-REJECT"


def test_rejects_invalid_ci_bounds():
    with pytest.raises(ValueError):
        DevelopmentVerdictInput(
            ci_lower=0.5,
            ci_upper=0.1,
            point_estimate=0.2,
            one_sided_positive_required=False,
            n_seasons_same_sign=3,
            n_seasons_tested=5,
            n_floor_met_in_every_reported_season=True,
            single_competition_independent=True,
        )


def test_rejects_impossible_season_counts():
    with pytest.raises(ValueError):
        DevelopmentVerdictInput(
            ci_lower=0.01,
            ci_upper=0.10,
            point_estimate=0.05,
            one_sided_positive_required=False,
            n_seasons_same_sign=6,
            n_seasons_tested=5,
            n_floor_met_in_every_reported_season=True,
            single_competition_independent=True,
        )
