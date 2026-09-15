import pytest

from prediction_markets_lab.research.holdout_verdict import (
    HoldoutVerdictInput,
    HoldoutVerdictThresholds,
    classify_holdout_result,
)


def _ev(ci_lower, ci_upper, auc=0.70, slope=1.0):
    return HoldoutVerdictInput(ci_lower=ci_lower, ci_upper=ci_upper, auc=auc, calibration_slope=slope)


# --- Input validation ---

def test_rejects_ci_lower_greater_than_ci_upper():
    with pytest.raises(ValueError):
        HoldoutVerdictInput(ci_lower=0.05, ci_upper=-0.05, auc=0.7, calibration_slope=1.0)


def test_thresholds_reject_inconsistent_bands():
    with pytest.raises(ValueError):
        HoldoutVerdictThresholds(catastrophic_slope_low=0.8, pass_slope_low=0.7)
    with pytest.raises(ValueError):
        HoldoutVerdictThresholds(catastrophic_slope_high=1.2, pass_slope_high=1.3)
    with pytest.raises(ValueError):
        HoldoutVerdictThresholds(pass_slope_low=1.3, pass_slope_high=0.7)
    with pytest.raises(ValueError):
        HoldoutVerdictThresholds(min_auc=0.5)
    with pytest.raises(ValueError):
        HoldoutVerdictThresholds(min_auc=1.0)


# --- Clear-cut cases ---

def test_clear_pass():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=1.0))
    assert result.verdict == "PASS"


def test_clear_fail_ci_unfavourable():
    result = classify_holdout_result(_ev(0.01, 0.05, auc=0.70, slope=1.0))
    assert result.verdict == "FAIL"
    assert "worse than the baseline" in result.reason


def test_clear_fail_low_auc():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.60, slope=1.0))
    assert result.verdict == "FAIL"
    assert "discrimination floor" in result.reason


def test_clear_fail_slope_too_low():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=0.3))
    assert result.verdict == "FAIL"
    assert "catastrophic" in result.reason


def test_clear_fail_slope_too_high():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=1.8))
    assert result.verdict == "FAIL"


def test_catastrophic_slope_fails_even_with_favourable_ci_and_good_auc():
    # A catastrophic slope alone is disqualifying, independent of the CI result --
    # this is the exact overlap ChatGPT flagged, now resolved as an independent OR-branch.
    result = classify_holdout_result(_ev(-0.10, -0.05, auc=0.90, slope=2.0))
    assert result.verdict == "FAIL"


def test_partial_inconclusive_ci_straddles_zero():
    result = classify_holdout_result(_ev(-0.01, 0.01, auc=0.70, slope=1.0))
    assert result.verdict == "PARTIAL"
    assert "includes zero" in result.reason


def test_partial_favourable_ci_but_marginal_slope_low():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=0.5))
    assert result.verdict == "PARTIAL"
    assert "pass band" in result.reason


def test_partial_favourable_ci_but_marginal_slope_high():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=1.5))
    assert result.verdict == "PARTIAL"


# --- Exact boundary cases (each must map to exactly one verdict) ---

def test_boundary_ci_upper_exactly_zero_is_partial_not_pass():
    result = classify_holdout_result(_ev(-0.02, 0.0, auc=0.70, slope=1.0))
    assert result.verdict == "PARTIAL"


def test_boundary_ci_lower_exactly_zero_is_not_fail():
    result = classify_holdout_result(_ev(0.0, 0.02, auc=0.70, slope=1.0))
    assert result.verdict == "PARTIAL"


def test_boundary_auc_exactly_at_floor_can_still_pass():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.65, slope=1.0))
    assert result.verdict == "PASS"


def test_boundary_auc_just_below_floor_fails():
    result = classify_holdout_result(_ev(-0.05, -0.01, auc=0.6499, slope=1.0))
    assert result.verdict == "FAIL"


def test_boundary_slope_exactly_at_pass_band_edges_passes():
    assert classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=0.7)).verdict == "PASS"
    assert classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=1.3)).verdict == "PASS"


def test_boundary_slope_exactly_at_catastrophic_edges_is_partial_not_fail():
    # Exactly on the catastrophic boundary is defined as NOT catastrophic (inclusive),
    # but it is still outside the pass band, so it lands in PARTIAL.
    assert classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=0.4)).verdict == "PARTIAL"
    assert classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=1.6)).verdict == "PARTIAL"


def test_boundary_slope_just_outside_catastrophic_edges_fails():
    assert classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=0.3999)).verdict == "FAIL"
    assert classify_holdout_result(_ev(-0.05, -0.01, auc=0.70, slope=1.6001)).verdict == "FAIL"


# --- Exhaustiveness / uniqueness sweep ---

def test_every_combination_in_a_representative_grid_maps_to_exactly_one_verdict():
    ci_bounds = [(-0.05, -0.02), (-0.02, 0.0), (-0.01, 0.01), (0.0, 0.02), (0.02, 0.05)]
    aucs = [0.55, 0.6499, 0.65, 0.70, 0.90]
    slopes = [0.2, 0.4, 0.5, 0.7, 1.0, 1.3, 1.5, 1.6, 2.0]
    seen_all_three = set()
    for lower, upper in ci_bounds:
        for auc in aucs:
            for slope in slopes:
                result = classify_holdout_result(_ev(lower, upper, auc=auc, slope=slope))
                assert result.verdict in ("PASS", "PARTIAL", "FAIL")
                seen_all_three.add(result.verdict)
    assert seen_all_three == {"PASS", "PARTIAL", "FAIL"}
