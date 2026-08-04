"""Evidence grading: A / B / C / INSUFFICIENT.

Implements the grading rules from project instructions section 8,
reading configurable thresholds from config/research_thresholds.yaml
rather than hard-coding them (project coding standards, section 20).

This is deliberately separate from decisions.grading (which grades a
single day's trading opportunity, A+/A/B/C/Reject). Evidence grading
answers a different question — how much do we trust a *behaviour's*
accumulated research evidence — on a much slower cadence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceGradingThresholds:
    """Configurable thresholds mirroring config/research_thresholds.yaml."""

    grade_a_min_out_of_sample_observations: int = 100
    grade_a_min_paper_observations: int = 30
    grade_a_require_positive_out_of_sample_result: bool = True
    grade_a_require_non_negative_paper_result: bool = True
    grade_a_require_positive_clv: bool = True
    grade_a_max_calibration_error: float = 0.05
    grade_a_confidence_interval_excludes_zero: bool = True
    grade_a_require_stability_across_periods: bool = True
    grade_a_max_multiple_testing_family_size: int = 5

    grade_b_min_out_of_sample_observations: int = 40
    grade_b_min_paper_observations: int = 10

    grade_c_min_out_of_sample_observations: int = 1


@dataclass(frozen=True)
class EvidenceInputs:
    """All evidence available for one behaviour/hypothesis, at grading time."""

    out_of_sample_observations: int = 0
    paper_observations: int = 0
    out_of_sample_result_positive: bool | None = None  # None = no result yet
    paper_result_non_negative: bool | None = None
    clv_positive: bool | None = None
    calibration_error: float | None = None  # e.g. |observed Brier - baseline Brier|
    confidence_interval_lower: float | None = None
    confidence_interval_upper: float | None = None
    stable_across_periods: bool | None = None
    multiple_testing_family_size: int = 1
    known_leakage_or_data_quality_issue: bool = False


@dataclass(frozen=True)
class EvidenceGradeResult:
    """The outcome of grading a behaviour's accumulated evidence."""

    grade: str  # "A" | "B" | "C" | "INSUFFICIENT"
    reason: str
    extra_scrutiny_flag: bool = False


def grade_evidence(
    evidence: EvidenceInputs, thresholds: EvidenceGradingThresholds
) -> EvidenceGradeResult:
    """Grade a behaviour/hypothesis's accumulated research evidence.

    Args:
        evidence: All evidence gathered so far.
        thresholds: The configured grading thresholds to apply.

    Returns:
        An EvidenceGradeResult with grade "A", "B", "C", or
        "INSUFFICIENT", a reason, and an extra_scrutiny_flag set when
        the hypothesis belongs to a large multiple-testing family
        (see docs/RESEARCH_ENGINE.md, "Multiple testing risk").
    """
    extra_scrutiny = (
        evidence.multiple_testing_family_size > thresholds.grade_a_max_multiple_testing_family_size
    )

    if evidence.known_leakage_or_data_quality_issue:
        return EvidenceGradeResult(
            "INSUFFICIENT",
            "known data-quality or leakage issue — evidence cannot be trusted until resolved",
            extra_scrutiny,
        )

    if evidence.out_of_sample_observations < thresholds.grade_c_min_out_of_sample_observations:
        return EvidenceGradeResult(
            "INSUFFICIENT", "no meaningful out-of-sample test completed yet", extra_scrutiny
        )

    ci_excludes_zero = (
        evidence.confidence_interval_lower is not None
        and evidence.confidence_interval_upper is not None
        and (evidence.confidence_interval_lower > 0 or evidence.confidence_interval_upper < 0)
    )

    grade_a_checks = {
        "out_of_sample_observations": (
            evidence.out_of_sample_observations >= thresholds.grade_a_min_out_of_sample_observations
        ),
        "paper_observations": (
            evidence.paper_observations >= thresholds.grade_a_min_paper_observations
        ),
        "out_of_sample_result_positive": (
            not thresholds.grade_a_require_positive_out_of_sample_result
            or evidence.out_of_sample_result_positive is True
        ),
        "paper_result_non_negative": (
            not thresholds.grade_a_require_non_negative_paper_result
            or evidence.paper_result_non_negative is True
        ),
        "clv_positive": (
            not thresholds.grade_a_require_positive_clv or evidence.clv_positive is True
        ),
        "calibration": (
            evidence.calibration_error is not None
            and evidence.calibration_error <= thresholds.grade_a_max_calibration_error
        ),
        "confidence_interval": (
            not thresholds.grade_a_confidence_interval_excludes_zero or ci_excludes_zero
        ),
        "stability": (
            not thresholds.grade_a_require_stability_across_periods
            or evidence.stable_across_periods is True
        ),
        "no_extra_scrutiny_block": not extra_scrutiny,
    }
    failed_a_checks = [name for name, passed in grade_a_checks.items() if not passed]

    if not failed_a_checks:
        return EvidenceGradeResult("A", "meets all Grade A evidence criteria", extra_scrutiny)

    grade_b_checks = {
        "out_of_sample_observations": (
            evidence.out_of_sample_observations >= thresholds.grade_b_min_out_of_sample_observations
        ),
        "paper_observations": (
            evidence.paper_observations >= thresholds.grade_b_min_paper_observations
        ),
        "out_of_sample_result_promising": evidence.out_of_sample_result_positive is True,
    }
    failed_b_checks = [name for name, passed in grade_b_checks.items() if not passed]

    if not failed_b_checks:
        reason = "meets Grade B criteria: promising out-of-sample result, limited sample"
        if extra_scrutiny:
            reason += " (large multiple-testing family — treat with extra scepticism)"
        return EvidenceGradeResult("B", reason, extra_scrutiny)

    return EvidenceGradeResult(
        "C",
        f"has at least one out-of-sample observation but fails Grade B on: {failed_b_checks}",
        extra_scrutiny,
    )
