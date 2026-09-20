"""Binary Brier score and log loss for single-selection paper/real bets.

Distinct from performance/brier.py and performance/log_loss.py, which
score a full 3-outcome (home/draw/away) probability vector for research
model validation -- see docs/PROBABILITY_METHODOLOGY.md. A Daily Card
recommendation is graded on ONE selection's estimated probability (e.g.
"home wins" at 55%), not a full three-way distribution, so scoring it
needs the standard binary formulation, not a reuse (or a distortion) of
the 3-outcome functions. This keeps "different markets/contexts may use
different probability architectures" (the master research directive)
honest at the metrics layer too, rather than forcing one shape to fit
both jobs.
"""

from __future__ import annotations

import math

_EPS = 1e-15


def binary_brier_score(predicted_probability: float, outcome_occurred: bool) -> float:
    """Brier score for one binary prediction. 0.0 (best) to 1.0 (worst)."""
    actual = 1.0 if outcome_occurred else 0.0
    return (predicted_probability - actual) ** 2


def binary_log_loss(predicted_probability: float, outcome_occurred: bool) -> float:
    """Log loss for one binary prediction, clipped to avoid -inf/NaN."""
    p = min(max(predicted_probability, _EPS), 1 - _EPS)
    return -math.log(p) if outcome_occurred else -math.log(1 - p)


def mean_binary_brier_score(predicted_probabilities: list[float], outcomes_occurred: list[bool]) -> float | None:
    """Mean binary Brier score, or None if the inputs are empty/mismatched."""
    if not predicted_probabilities or len(predicted_probabilities) != len(outcomes_occurred):
        return None
    return sum(
        binary_brier_score(p, o) for p, o in zip(predicted_probabilities, outcomes_occurred)
    ) / len(predicted_probabilities)


def mean_binary_log_loss(predicted_probabilities: list[float], outcomes_occurred: list[bool]) -> float | None:
    """Mean binary log loss, or None if the inputs are empty/mismatched."""
    if not predicted_probabilities or len(predicted_probabilities) != len(outcomes_occurred):
        return None
    return sum(
        binary_log_loss(p, o) for p, o in zip(predicted_probabilities, outcomes_occurred)
    ) / len(predicted_probabilities)
