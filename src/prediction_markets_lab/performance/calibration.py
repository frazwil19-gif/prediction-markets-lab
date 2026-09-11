"""Raw calibration / reliability diagnostics for 3-outcome match predictions.

Per research/cycles/CYCLE_001/STAGE_3B_PLAN.md section 8: "Calibration/
reliability reporting is deferred to the model checkpoints (Elo/Poisson/
blend), where there is something non-trivial to calibrate beyond the
already-well-calibrated consensus." This module implements RAW
calibration only -- it measures whether a model's stated probabilities
match observed frequencies, it does NOT fit or apply any recalibration
(no Platt scaling, no isotonic regression). Any such recalibration
remains a distinct, later, optional step per the plan.

Method: for one outcome (e.g. "home"), take every match's predicted
probability of that outcome and a 0/1 indicator of whether that outcome
actually occurred. Group into equal-COUNT bins (quantiles of the
predicted probability), not equal-width bins -- football win/draw/away
probabilities cluster in a fairly narrow band (draw probabilities in
particular rarely go below ~0.10 or above ~0.40), so fixed-width bins
over [0, 1] would leave several bins empty while overloading one or two
others. Equal-count bins guarantee every bin has a comparable, non-zero
sample size to compute a meaningful observed frequency from.

Within each bin: mean predicted probability vs. observed frequency
(fraction of matches in that bin where the outcome actually occurred).
A well-calibrated model has these two numbers close together in every
bin. Expected Calibration Error (ECE) summarises this into one number:
the sample-size-weighted mean absolute gap across bins.
"""

from __future__ import annotations

from dataclasses import dataclass

from prediction_markets_lab.performance.log_loss import OUTCOMES


@dataclass(frozen=True)
class CalibrationBin:
    """One bin of a reliability diagram for a single outcome."""

    bin_index: int
    n: int
    mean_predicted_probability: float
    observed_frequency: float
    min_predicted_probability: float
    max_predicted_probability: float

    @property
    def gap(self) -> float:
        """Absolute difference between mean predicted probability and observed frequency."""
        return abs(self.mean_predicted_probability - self.observed_frequency)


@dataclass(frozen=True)
class CalibrationReport:
    """Calibration diagnostics for one model, for one outcome."""

    outcome: str
    n_bins: int
    n_matches: int
    bins: list[CalibrationBin]
    expected_calibration_error: float


def compute_calibration_bins(
    predicted_probabilities: list[float], actual_indicators: list[bool], n_bins: int = 10
) -> list[CalibrationBin]:
    """Group (predicted probability, actual indicator) pairs into equal-count bins.

    Args:
        predicted_probabilities: this outcome's predicted probability for
            each match.
        actual_indicators: True/False, whether this outcome actually
            occurred, same order/length as predicted_probabilities.
        n_bins: number of equal-count bins. The final bin absorbs any
            remainder when n_matches does not divide evenly by n_bins.

    Returns:
        A list of CalibrationBin, ordered by increasing predicted
        probability (bin 0 = lowest predicted probabilities).

    Raises:
        ValueError: on length mismatch, empty input, or n_bins < 1 or
            greater than the number of matches.
    """
    n = len(predicted_probabilities)
    if len(actual_indicators) != n:
        raise ValueError("predicted_probabilities and actual_indicators must be the same length")
    if n == 0:
        raise ValueError("cannot compute calibration bins over zero matches")
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")
    if n_bins > n:
        raise ValueError(f"n_bins ({n_bins}) must not exceed the number of matches ({n})")

    paired = sorted(zip(predicted_probabilities, actual_indicators), key=lambda pair: pair[0])

    base_size = n // n_bins
    remainder = n % n_bins

    bins: list[CalibrationBin] = []
    start = 0
    for bin_index in range(n_bins):
        # Distribute the remainder across the LAST bins so every bin
        # size differs by at most one match, rather than dumping the
        # whole remainder into a single oversized final bin.
        size = base_size + (1 if bin_index >= n_bins - remainder else 0)
        chunk = paired[start:start + size]
        start += size

        preds_in_bin = [p for p, _ in chunk]
        actuals_in_bin = [a for _, a in chunk]
        bins.append(
            CalibrationBin(
                bin_index=bin_index,
                n=len(chunk),
                mean_predicted_probability=sum(preds_in_bin) / len(chunk),
                observed_frequency=sum(1 for a in actuals_in_bin if a) / len(chunk),
                min_predicted_probability=min(preds_in_bin),
                max_predicted_probability=max(preds_in_bin),
            )
        )
    return bins


def compute_outcome_calibration(
    predictions: list[dict[str, float]], actual_outcomes: list[str], outcome: str, n_bins: int = 10
) -> CalibrationReport:
    """Raw calibration report for one outcome (e.g. "home") of a model.

    Args:
        predictions: one {"home":.., "draw":.., "away":..} dict per match.
        actual_outcomes: the realised outcome per match ("home"/"draw"/"away").
        outcome: which outcome to assess calibration for.
        n_bins: number of equal-count bins (see compute_calibration_bins).

    Returns:
        A CalibrationReport with per-bin diagnostics and the overall
        expected calibration error for this outcome.

    Raises:
        ValueError: if outcome is not a valid outcome, lengths mismatch,
            or n_bins is invalid.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome {outcome!r} must be one of {OUTCOMES}")
    if len(predictions) != len(actual_outcomes):
        raise ValueError("predictions and actual_outcomes must be the same length")

    predicted_probabilities = [p[outcome] for p in predictions]
    actual_indicators = [a == outcome for a in actual_outcomes]
    bins = compute_calibration_bins(predicted_probabilities, actual_indicators, n_bins=n_bins)

    n = len(actual_outcomes)
    ece = sum(b.n * b.gap for b in bins) / n

    return CalibrationReport(
        outcome=outcome,
        n_bins=n_bins,
        n_matches=n,
        bins=bins,
        expected_calibration_error=ece,
    )
