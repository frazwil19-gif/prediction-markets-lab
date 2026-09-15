"""Mechanical PASS/PARTIAL/FAIL verdict for a sealed-holdout evaluation.

Implements a single, pre-registered decision function so a sealed
holdout's outcome is read off mechanically rather than judged after
the fact. See
research/cycles/CYCLE_002_TENNIS/TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md
section 9 for the exact rule this function encodes. Tennis Cycle 1's
first drafted rule had an overlap -- a FAIL clause ("the CI doesn't
exclude zero favourably") and a PARTIAL clause ("a favourable point
estimate but an inconclusive CI") could describe the same result. That
was corrected here, before 2025 was ever opened, by making the three
checks strictly ordered and mutually exclusive.

The three checks (a paired-bootstrap CI on the primary log-loss
comparison, discrimination via AUC, and calibration slope) are
evaluated in this fixed order so every possible input maps to exactly
one of PASS / PARTIAL / FAIL:

1. FAIL first -- each of these is independently disqualifying, never
   combined with another condition to produce a different verdict:
   - the CI for (candidate - baseline) log loss lies ENTIRELY ABOVE
     zero (the candidate is statistically significantly worse than the
     baseline -- not merely inconclusive);
   - AUC is below the discrimination floor;
   - the calibration slope is outside the catastrophic band (this
     alone fails the cycle, regardless of how the log-loss CI reads).
2. Otherwise PASS, only if ALL of: the CI lies entirely below zero
   (the candidate is statistically significantly better), AUC clears
   the floor, and the calibration slope is inside the pass band.
3. Otherwise PARTIAL -- the only remaining case, covering both an
   inconclusive CI (straddles zero) and a favourable CI paired with a
   merely-marginal (non-catastrophic) calibration slope.

Every boundary (a CI bound of exactly zero, a metric sitting exactly
on a threshold) is resolved by the strict/non-strict inequalities
below, never by judgement at report time -- see
tests/unit/test_holdout_verdict.py for the exact mapping of each one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["PASS", "PARTIAL", "FAIL"]


@dataclass(frozen=True)
class HoldoutVerdictThresholds:
    """Pre-registered thresholds for the sealed-holdout verdict.

    Defaults are Tennis Cycle 1's frozen values (see
    TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md section 9). A future cycle
    with its own frozen document should pass its own thresholds
    explicitly rather than silently relying on these defaults.
    """

    min_auc: float = 0.65
    pass_slope_low: float = 0.7
    pass_slope_high: float = 1.3
    catastrophic_slope_low: float = 0.4
    catastrophic_slope_high: float = 1.6

    def __post_init__(self) -> None:
        if self.catastrophic_slope_low > self.pass_slope_low:
            raise ValueError("catastrophic_slope_low must be <= pass_slope_low")
        if self.catastrophic_slope_high < self.pass_slope_high:
            raise ValueError("catastrophic_slope_high must be >= pass_slope_high")
        if self.pass_slope_low >= self.pass_slope_high:
            raise ValueError("pass_slope_low must be < pass_slope_high")
        if self.min_auc <= 0.5 or self.min_auc >= 1.0:
            raise ValueError("min_auc must be strictly between 0.5 and 1.0")


@dataclass(frozen=True)
class HoldoutVerdictInput:
    """Primary-comparison and diagnostic evidence for the verdict.

    ci_lower/ci_upper are the paired-bootstrap 95% CI bounds for
    (candidate_log_loss - baseline_log_loss) on the sealed holdout:
    negative means the candidate has lower (better) log loss.
    """

    ci_lower: float
    ci_upper: float
    auc: float
    calibration_slope: float

    def __post_init__(self) -> None:
        if self.ci_lower > self.ci_upper:
            raise ValueError("ci_lower must be <= ci_upper")


@dataclass(frozen=True)
class HoldoutVerdictResult:
    """The mechanical verdict plus the specific clause that produced it."""

    verdict: Verdict
    reason: str


def classify_holdout_result(
    evidence: HoldoutVerdictInput,
    thresholds: HoldoutVerdictThresholds = HoldoutVerdictThresholds(),
) -> HoldoutVerdictResult:
    """Apply the frozen, mutually exclusive PASS/PARTIAL/FAIL rule.

    Args:
        evidence: The primary-comparison CI plus AUC/calibration-slope
            diagnostics computed on the sealed holdout.
        thresholds: The pre-registered thresholds to apply (defaults to
            Tennis Cycle 1's frozen values).

    Returns:
        A HoldoutVerdictResult naming the verdict and the specific
        clause that produced it, for an auditable, non-discretionary
        report.
    """
    ci_favourable = evidence.ci_upper < 0.0
    ci_unfavourable = evidence.ci_lower > 0.0
    slope_catastrophic = (
        evidence.calibration_slope < thresholds.catastrophic_slope_low
        or evidence.calibration_slope > thresholds.catastrophic_slope_high
    )
    slope_in_pass_band = (
        thresholds.pass_slope_low <= evidence.calibration_slope <= thresholds.pass_slope_high
    )

    if ci_unfavourable:
        return HoldoutVerdictResult(
            "FAIL",
            "primary-comparison CI lies entirely above zero: the candidate is "
            "statistically significantly worse than the baseline, not merely inconclusive",
        )
    if evidence.auc < thresholds.min_auc:
        return HoldoutVerdictResult(
            "FAIL",
            f"AUC {evidence.auc:.4f} is below the discrimination floor {thresholds.min_auc:.4f}",
        )
    if slope_catastrophic:
        return HoldoutVerdictResult(
            "FAIL",
            f"calibration slope {evidence.calibration_slope:.4f} is outside the catastrophic "
            f"band [{thresholds.catastrophic_slope_low}, {thresholds.catastrophic_slope_high}]",
        )

    if ci_favourable and slope_in_pass_band:
        # AUC has already cleared the floor above (not < thresholds.min_auc).
        return HoldoutVerdictResult(
            "PASS",
            "primary-comparison CI lies entirely below zero, AUC clears the floor, and "
            "calibration slope is within the pass band",
        )

    if not ci_favourable:
        return HoldoutVerdictResult(
            "PARTIAL",
            "primary-comparison CI includes zero: any favourable point estimate is not "
            "statistically conclusive at this sample size",
        )
    return HoldoutVerdictResult(
        "PARTIAL",
        f"primary comparison favours the candidate, but calibration slope "
        f"{evidence.calibration_slope:.4f} falls outside the pass band "
        f"[{thresholds.pass_slope_low}, {thresholds.pass_slope_high}] without being catastrophic",
    )
