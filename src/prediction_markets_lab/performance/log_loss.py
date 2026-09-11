"""Multiclass log loss for 3-outcome (home/draw/away) match predictions.

Used throughout Stage 3B to score every baseline and model on an equal
footing (see research/cycles/CYCLE_001/STAGE_3B_PLAN.md). Lower is
better; a uniform 1/3-1/3-1/3 prediction scores ln(3) ≈ 1.0986 on every
match, which is the naive floor any model should beat.
"""

from __future__ import annotations

import math

OUTCOMES: tuple[str, ...] = ("home", "draw", "away")
_EPS = 1e-15
_SUM_TOLERANCE = 1e-3


def validate_outcome_probabilities(probabilities: dict[str, float]) -> None:
    if set(probabilities.keys()) != set(OUTCOMES):
        raise ValueError(
            f"probabilities keys must be exactly {OUTCOMES}, got {sorted(probabilities.keys())}"
        )
    for outcome, p in probabilities.items():
        if p < 0.0:
            raise ValueError(f"probability for {outcome!r} is negative: {p}")
    total = sum(probabilities.values())
    if not math.isclose(total, 1.0, abs_tol=_SUM_TOLERANCE):
        raise ValueError(f"probabilities must sum to ~1.0 (tolerance {_SUM_TOLERANCE}), got {total}")


def log_loss_single(probabilities: dict[str, float], actual_outcome: str) -> float:
    """Log loss for a single match.

    Args:
        probabilities: dict with keys "home", "draw", "away" summing to ~1.0.
        actual_outcome: one of "home", "draw", "away".

    Returns:
        -log(p_actual), with p_actual clipped to [_EPS, 1 - _EPS] so a
        confident-and-wrong prediction is heavily penalised but never
        produces -inf/NaN.

    Raises:
        ValueError: if actual_outcome is not a valid outcome, the
            probabilities dict has the wrong keys, contains a negative
            value, or does not sum to ~1.0.
    """
    if actual_outcome not in OUTCOMES:
        raise ValueError(f"actual_outcome {actual_outcome!r} must be one of {OUTCOMES}")
    validate_outcome_probabilities(probabilities)
    p = min(max(probabilities[actual_outcome], _EPS), 1 - _EPS)
    return -math.log(p)


def multiclass_log_loss(
    predicted_probabilities: list[dict[str, float]], actual_outcomes: list[str]
) -> float:
    """Mean multiclass log loss over a set of predictions.

    Args:
        predicted_probabilities: one {"home":.., "draw":.., "away":..}
            dict per match, in the same order as actual_outcomes.
        actual_outcomes: the realised outcome for each match, one of
            "home"/"draw"/"away".

    Returns:
        The mean of log_loss_single() across every match.

    Raises:
        ValueError: if the two lists differ in length, are both empty,
            or any individual prediction fails validation (see
            log_loss_single).
    """
    if len(predicted_probabilities) != len(actual_outcomes):
        raise ValueError(
            "predicted_probabilities and actual_outcomes must be the same length "
            f"({len(predicted_probabilities)} != {len(actual_outcomes)})"
        )
    if not predicted_probabilities:
        raise ValueError("cannot compute log loss over zero predictions")
    total = sum(
        log_loss_single(probs, actual)
        for probs, actual in zip(predicted_probabilities, actual_outcomes)
    )
    return total / len(actual_outcomes)
