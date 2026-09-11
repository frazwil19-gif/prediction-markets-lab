"""Multiclass (vector) Brier score for 3-outcome match predictions.

Complements log_loss.py: log loss penalises confident wrong answers
much more harshly, Brier score is bounded ([0, 2] for the 3-outcome
vector form used here) and easier to reason about intuitively. Stage
3B reports both, plus calibration, per
research/cycles/CYCLE_001/STAGE_3B_PLAN.md -- no single metric is
treated as sufficient on its own.
"""

from __future__ import annotations

from prediction_markets_lab.performance.log_loss import OUTCOMES, validate_outcome_probabilities


def brier_score_single(probabilities: dict[str, float], actual_outcome: str) -> float:
    """Multiclass Brier score for a single match.

    Args:
        probabilities: dict with keys "home", "draw", "away" summing to ~1.0.
        actual_outcome: one of "home", "draw", "away".

    Returns:
        sum over all three outcomes of (predicted_probability -
        actual_indicator)^2, where actual_indicator is 1.0 for the
        realised outcome and 0.0 otherwise. Ranges from 0.0 (a
        perfect, fully-confident correct prediction) to 2.0 (fully
        confident in the wrong single outcome).

    Raises:
        ValueError: if actual_outcome is not a valid outcome, the
            probabilities dict has the wrong keys, contains a negative
            value, or does not sum to ~1.0.
    """
    if actual_outcome not in OUTCOMES:
        raise ValueError(f"actual_outcome {actual_outcome!r} must be one of {OUTCOMES}")
    validate_outcome_probabilities(probabilities)
    return sum(
        (probabilities[outcome] - (1.0 if outcome == actual_outcome else 0.0)) ** 2
        for outcome in OUTCOMES
    )


def multiclass_brier_score(
    predicted_probabilities: list[dict[str, float]], actual_outcomes: list[str]
) -> float:
    """Mean multiclass Brier score over a set of predictions.

    Args:
        predicted_probabilities: one {"home":.., "draw":.., "away":..}
            dict per match, in the same order as actual_outcomes.
        actual_outcomes: the realised outcome for each match.

    Returns:
        The mean of brier_score_single() across every match.

    Raises:
        ValueError: if the two lists differ in length, are both empty,
            or any individual prediction fails validation.
    """
    if len(predicted_probabilities) != len(actual_outcomes):
        raise ValueError(
            "predicted_probabilities and actual_outcomes must be the same length "
            f"({len(predicted_probabilities)} != {len(actual_outcomes)})"
        )
    if not predicted_probabilities:
        raise ValueError("cannot compute Brier score over zero predictions")
    total = sum(
        brier_score_single(probs, actual)
        for probs, actual in zip(predicted_probabilities, actual_outcomes)
    )
    return total / len(actual_outcomes)
