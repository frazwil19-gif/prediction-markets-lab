"""Binary-outcome performance metrics -- log loss, Brier score, raw
calibration, calibration intercept/slope, and AUC.

The existing performance/log_loss.py, brier.py, and calibration.py are
deliberately football-specific (hardcoded to the 3-outcome home/draw/away
convention -- see their own docstrings). Tennis Match Winner is a genuine
binary outcome (no draw), so this module provides the equivalent metrics
for a single probability p = P(player_a wins) against a 0/1 actual
outcome, built fresh rather than forcing tennis through the 3-outcome
interface.

Used by Workstream A4 (Cycle 2 tennis baselines) per the operating
instructions: log loss and Brier score as primary, calibration (raw bins,
plus intercept/slope from a logistic recalibration fit) as a required
diagnostic, AUC as a secondary discrimination metric. None of these
establish a betting edge on their own -- see
research/cycles/CYCLE_002_TENNIS/A4_BASELINE_RESULTS.md for that caveat
stated in context.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_EPS = 1e-15


def _clip_probability(p: float) -> float:
    return min(max(p, _EPS), 1.0 - _EPS)


def binary_log_loss_single(p_predicted: float, actual: int) -> float:
    """Log loss for one prediction. actual must be 0 or 1; p_predicted is P(actual==1)."""
    if actual not in (0, 1):
        raise ValueError(f"actual must be 0 or 1, got {actual!r}")
    p = _clip_probability(p_predicted)
    return -math.log(p) if actual == 1 else -math.log(1.0 - p)


def binary_log_loss(predicted_probabilities: list[float], actuals: list[int]) -> float:
    """Mean binary log loss. Lower is better; a constant p=0.5 prediction
    scores ln(2) ~= 0.6931 on every match, the naive floor any model
    with real information should beat."""
    if len(predicted_probabilities) != len(actuals):
        raise ValueError("predicted_probabilities and actuals must be the same length")
    if not predicted_probabilities:
        raise ValueError("cannot compute log loss over zero predictions")
    return sum(
        binary_log_loss_single(p, a) for p, a in zip(predicted_probabilities, actuals)
    ) / len(actuals)


def binary_brier_score_single(p_predicted: float, actual: int) -> float:
    """Brier score for one prediction: (p_predicted - actual)^2. Ranges [0, 1]."""
    if actual not in (0, 1):
        raise ValueError(f"actual must be 0 or 1, got {actual!r}")
    return (p_predicted - float(actual)) ** 2


def binary_brier_score(predicted_probabilities: list[float], actuals: list[int]) -> float:
    if len(predicted_probabilities) != len(actuals):
        raise ValueError("predicted_probabilities and actuals must be the same length")
    if not predicted_probabilities:
        raise ValueError("cannot compute Brier score over zero predictions")
    return sum(
        binary_brier_score_single(p, a) for p, a in zip(predicted_probabilities, actuals)
    ) / len(actuals)


@dataclass(frozen=True)
class CalibrationBin:
    bin_index: int
    n: int
    mean_predicted_probability: float
    observed_frequency: float
    min_predicted_probability: float
    max_predicted_probability: float

    @property
    def gap(self) -> float:
        return abs(self.mean_predicted_probability - self.observed_frequency)


def binary_calibration_bins(
    predicted_probabilities: list[float], actuals: list[int], n_bins: int = 10
) -> list[CalibrationBin]:
    """Equal-COUNT calibration bins (quantiles of predicted probability,
    not fixed-width [0,1] bins) -- same rationale as the football
    calibration module: guarantees every bin has a comparable, non-zero
    sample size rather than leaving some empty."""
    if len(predicted_probabilities) != len(actuals):
        raise ValueError("predicted_probabilities and actuals must be the same length")
    if len(predicted_probabilities) < n_bins:
        raise ValueError(
            f"need at least n_bins={n_bins} predictions to form that many equal-count bins, "
            f"got {len(predicted_probabilities)}"
        )
    order = np.argsort(predicted_probabilities)
    p_sorted = np.array(predicted_probabilities)[order]
    a_sorted = np.array(actuals)[order]

    bin_edges = np.array_split(np.arange(len(p_sorted)), n_bins)
    bins = []
    for i, idx in enumerate(bin_edges):
        if len(idx) == 0:
            continue
        p_bin = p_sorted[idx]
        a_bin = a_sorted[idx]
        bins.append(CalibrationBin(
            bin_index=i,
            n=len(idx),
            mean_predicted_probability=float(p_bin.mean()),
            observed_frequency=float(a_bin.mean()),
            min_predicted_probability=float(p_bin.min()),
            max_predicted_probability=float(p_bin.max()),
        ))
    return bins


def expected_calibration_error(bins: list[CalibrationBin]) -> float:
    total_n = sum(b.n for b in bins)
    if total_n == 0:
        return float("nan")
    return sum(b.gap * b.n for b in bins) / total_n


def binary_auc(predicted_probabilities: list[float], actuals: list[int]) -> float:
    """AUC via the Mann-Whitney U / rank-sum identity -- no external
    dependency (no sklearn/scipy in this project's environment). Equal to
    the probability that a randomly chosen actual-1 case is scored higher
    than a randomly chosen actual-0 case, with ties counted as 0.5."""
    p = np.asarray(predicted_probabilities, dtype=float)
    a = np.asarray(actuals, dtype=int)
    n_pos = int((a == 1).sum())
    n_neg = int((a == 0).sum())
    if n_pos == 0 or n_neg == 0:
        raise ValueError("AUC is undefined with only one class present in actuals")

    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sorted_p = p[order]
    # Average ranks for ties (standard rank-sum tie handling).
    i = 0
    rank = 1
    while i < len(sorted_p):
        j = i
        while j + 1 < len(sorted_p) and sorted_p[j + 1] == sorted_p[i]:
            j += 1
        avg_rank = (rank + (rank + (j - i))) / 2.0
        ranks[order[i:j + 1]] = avg_rank
        rank += (j - i + 1)
        i = j + 1

    sum_ranks_pos = ranks[a == 1].sum()
    u_statistic = sum_ranks_pos - n_pos * (n_pos + 1) / 2.0
    return float(u_statistic / (n_pos * n_neg))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, _EPS, 1.0 - _EPS)
    return np.log(p / (1.0 - p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35, 35)))


def fit_calibration_intercept_slope(
    predicted_probabilities: list[float], actuals: list[int],
    max_iter: int = 50, tol: float = 1e-8,
) -> tuple[float, float]:
    """Fit actual ~ sigmoid(intercept + slope * logit(p_predicted)) via
    Newton-Raphson (IRLS) -- the standard 2-parameter calibration-slope
    diagnostic (a well-calibrated model has intercept~=0, slope~=1; a
    systematically overconfident model has slope < 1). No sklearn/scipy
    dependency in this project's environment, so implemented directly:
    this is a 2-parameter logistic regression, a small, well-understood,
    closed iterative algorithm, not a general-purpose ML library
    reimplementation.

    Returns:
        (intercept, slope).

    Raises:
        ValueError: if inputs are empty/mismatched, or IRLS fails to
            converge within max_iter (rather than silently returning a
            bad fit).
    """
    if len(predicted_probabilities) != len(actuals):
        raise ValueError("predicted_probabilities and actuals must be the same length")
    if not predicted_probabilities:
        raise ValueError("cannot fit calibration over zero predictions")

    x = _logit(np.asarray(predicted_probabilities, dtype=float))
    y = np.asarray(actuals, dtype=float)
    design = np.column_stack([np.ones_like(x), x])  # [intercept, slope]
    beta = np.array([0.0, 1.0])  # start at "already calibrated"

    for _ in range(max_iter):
        eta = design @ beta
        mu = _sigmoid(eta)
        w = mu * (1.0 - mu)
        w = np.clip(w, 1e-10, None)
        gradient = design.T @ (y - mu)
        hessian = -(design.T * w) @ design
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError as exc:
            raise ValueError("IRLS Hessian is singular -- calibration fit failed") from exc
        beta = beta - step
        if np.max(np.abs(step)) < tol:
            return float(beta[0]), float(beta[1])

    raise ValueError(f"calibration intercept/slope fit did not converge within {max_iter} iterations")
