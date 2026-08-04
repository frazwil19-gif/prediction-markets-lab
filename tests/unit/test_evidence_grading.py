from prediction_markets_lab.research.evidence_grading import (
    EvidenceGradingThresholds,
    EvidenceInputs,
    grade_evidence,
)


def default_thresholds() -> EvidenceGradingThresholds:
    return EvidenceGradingThresholds()


def test_grade_a_when_all_criteria_met():
    evidence = EvidenceInputs(
        out_of_sample_observations=150,
        paper_observations=40,
        out_of_sample_result_positive=True,
        paper_result_non_negative=True,
        clv_positive=True,
        calibration_error=0.02,
        confidence_interval_lower=0.01,
        confidence_interval_upper=0.05,
        stable_across_periods=True,
        multiple_testing_family_size=2,
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade == "A"
    assert not result.extra_scrutiny_flag


def test_grade_a_blocked_by_large_multiple_testing_family():
    evidence = EvidenceInputs(
        out_of_sample_observations=150,
        paper_observations=40,
        out_of_sample_result_positive=True,
        paper_result_non_negative=True,
        clv_positive=True,
        calibration_error=0.02,
        confidence_interval_lower=0.01,
        confidence_interval_upper=0.05,
        stable_across_periods=True,
        multiple_testing_family_size=20,  # large family
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade != "A"
    assert result.extra_scrutiny_flag


def test_grade_b_with_promising_but_limited_sample():
    evidence = EvidenceInputs(
        out_of_sample_observations=50,
        paper_observations=15,
        out_of_sample_result_positive=True,
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade == "B"


def test_grade_c_with_weak_result():
    evidence = EvidenceInputs(
        out_of_sample_observations=5,
        paper_observations=0,
        out_of_sample_result_positive=False,
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade == "C"


def test_insufficient_with_no_out_of_sample_observations():
    evidence = EvidenceInputs()
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade == "INSUFFICIENT"


def test_insufficient_when_known_data_quality_issue():
    evidence = EvidenceInputs(
        out_of_sample_observations=200,
        paper_observations=50,
        out_of_sample_result_positive=True,
        known_leakage_or_data_quality_issue=True,
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade == "INSUFFICIENT"
    assert "leakage" in result.reason or "data-quality" in result.reason


def test_grade_a_requires_positive_clv_by_default():
    evidence = EvidenceInputs(
        out_of_sample_observations=150,
        paper_observations=40,
        out_of_sample_result_positive=True,
        paper_result_non_negative=True,
        clv_positive=False,  # fails
        calibration_error=0.02,
        confidence_interval_lower=0.01,
        confidence_interval_upper=0.05,
        stable_across_periods=True,
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade != "A"


def test_grade_a_requires_confidence_interval_excluding_zero():
    evidence = EvidenceInputs(
        out_of_sample_observations=150,
        paper_observations=40,
        out_of_sample_result_positive=True,
        paper_result_non_negative=True,
        clv_positive=True,
        calibration_error=0.02,
        confidence_interval_lower=-0.01,  # CI includes zero
        confidence_interval_upper=0.05,
        stable_across_periods=True,
    )
    result = grade_evidence(evidence, default_thresholds())
    assert result.grade != "A"
