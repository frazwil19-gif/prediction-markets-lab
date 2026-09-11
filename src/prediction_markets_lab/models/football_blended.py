"""Simple, interpretable probability blending (Stage 3B Model 3).

A blend is a weighted linear combination of two or more already-computed
probability vectors (market, Elo, Poisson) -- a convex combination, so it
remains a valid probability vector with no separate renormalisation step.
Weights are chosen by an exhaustive, predeclared grid search (not an
open-ended optimiser) over TRAINING-period predictions only, minimising log
loss -- the same calibrate-on-training-only pattern used for Elo's
draw_margin and Poisson's shrinkage. This project deliberately does NOT
automatically build every combination in the predeclared comparison matrix;
see research/cycles/CYCLE_001/STAGE_3B_PLAN.md and BLEND_REPORT.md for which
combinations were actually run and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement

from prediction_markets_lab.performance.log_loss import OUTCOMES, multiclass_log_loss


@dataclass(frozen=True)
class BlendWeights:
    """Component name -> weight. Weights must be >= 0 and sum to ~1.0."""

    weights: dict[str, float]

    def __post_init__(self) -> None:
        if any(w < 0 for w in self.weights.values()):
            raise ValueError(f"all blend weights must be >= 0, got {self.weights}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"blend weights must sum to 1.0 (tolerance 1e-6), got {total}")


def blend_probabilities(
    component_predictions: dict[str, dict[str, float]], weights: BlendWeights
) -> dict[str, float]:
    """Weighted linear combination of named component probability vectors.

    Args:
        component_predictions: {component_name: {"home":.., "draw":.., "away":..}},
            one entry per component named in weights.weights.
        weights: the blend weights, one per component, summing to 1.0.

    Returns:
        A single {"home":.., "draw":.., "away":..} dict, guaranteed to
        sum to ~1.0 since it is a convex combination of vectors that
        each already sum to ~1.0.

    Raises:
        ValueError: if the component names in component_predictions and
            weights.weights do not match exactly.
    """
    if set(component_predictions.keys()) != set(weights.weights.keys()):
        raise ValueError(
            "component_predictions and weights must name exactly the same components: "
            f"{sorted(component_predictions.keys())} vs {sorted(weights.weights.keys())}"
        )
    return {
        outcome: sum(
            weights.weights[name] * component_predictions[name][outcome]
            for name in weights.weights
        )
        for outcome in OUTCOMES
    }


def generate_predeclared_weight_grid(component_names: tuple[str, ...], step: float = 0.1) -> list[BlendWeights]:
    """Enumerate every weight combination over component_names summing to 1.0 in units of `step`.

    A finite, exhaustive, predeclared grid -- not an open-ended
    optimiser and not manually/arbitrarily chosen weights. For k
    components and step=0.1 (N=10 units), this is C(N+k-1, k-1)
    combinations (11 for k=2, 66 for k=3).

    Args:
        component_names: e.g. ("market", "elo").
        step: grid resolution, must evenly divide 1.0.

    Returns:
        A list of BlendWeights, each summing to exactly 1.0.

    Raises:
        ValueError: if component_names has fewer than 2 entries, or
            step does not evenly divide 1.0.
    """
    if len(component_names) < 2:
        raise ValueError("need at least 2 components to form a blend")
    n_units = round(1.0 / step)
    if abs(n_units * step - 1.0) > 1e-9:
        raise ValueError(f"step={step} must evenly divide 1.0")

    def _partitions(total_units: int, n_parts: int):
        if n_parts == 1:
            yield (total_units,)
            return
        for first in range(total_units + 1):
            for rest in _partitions(total_units - first, n_parts - 1):
                yield (first,) + rest

    grids = []
    for parts in _partitions(n_units, len(component_names)):
        weights = {name: units * step for name, units in zip(component_names, parts)}
        grids.append(BlendWeights(weights))
    return grids


def calibrate_blend_weights(
    component_predictions_by_name: dict[str, list[dict[str, float]]],
    actuals: list[str],
    step: float = 0.1,
) -> BlendWeights:
    """Grid-search blend weights minimising log loss on the given (training) predictions.

    Args:
        component_predictions_by_name: {component_name: [predictions...]},
            every list the same length and index-aligned to actuals.
            Intended to be TRAINING-period predictions only -- the
            caller is responsible for this (see
            research/cycles/CYCLE_001/STAGE_3B_PLAN.md).
        actuals: realised outcomes, same order/length as each prediction list.
        step: grid resolution passed to generate_predeclared_weight_grid.

    Returns:
        The BlendWeights from the predeclared grid with the lowest
        in-sample log loss on (component_predictions_by_name, actuals).

    Raises:
        ValueError: if component_predictions_by_name has fewer than 2
            components, or any list length does not match len(actuals).
    """
    component_names = tuple(component_predictions_by_name.keys())
    if len(component_names) < 2:
        raise ValueError("need at least 2 components to calibrate a blend")
    for name, preds in component_predictions_by_name.items():
        if len(preds) != len(actuals):
            raise ValueError(f"component {name!r} has {len(preds)} predictions, expected {len(actuals)}")

    n = len(actuals)
    best_weights = None
    best_log_loss = float("inf")
    for candidate in generate_predeclared_weight_grid(component_names, step=step):
        blended = [
            blend_probabilities(
                {name: component_predictions_by_name[name][i] for name in component_names}, candidate
            )
            for i in range(n)
        ]
        loss = multiclass_log_loss(blended, actuals)
        if loss < best_log_loss:
            best_log_loss = loss
            best_weights = candidate

    return best_weights
