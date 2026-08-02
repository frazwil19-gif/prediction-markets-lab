"""Cross-bookmaker consensus probability calculations.

For a given outcome, each bookmaker contributes one margin-free fair
probability (see margin_removal.py). This module aggregates those
per-bookmaker probabilities into a single consensus estimate.

The V1 default consensus estimator is the median, chosen for robustness
to stale or unusual individual bookmaker prices (project instructions,
section 8). Mean, weighted mean, standard deviation, min, max, IQR and
bookmaker count are also provided as supporting diagnostics.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ConsensusResult:
    """Aggregated consensus statistics for a single outcome."""

    median: float
    mean: float
    weighted_mean: float | None
    std_dev: float
    minimum: float
    maximum: float
    interquartile_range: float
    bookmaker_count: int

    @property
    def consensus_probability(self) -> float:
        """The V1 default consensus estimate (median)."""
        return self.median


def _interquartile_range(values: Sequence[float]) -> float:
    """Compute the interquartile range (Q3 - Q1) using inclusive quartiles."""
    if len(values) < 2:
        return 0.0
    quantiles = statistics.quantiles(values, n=4, method="inclusive")
    q1, _, q3 = quantiles
    return q3 - q1


def calculate_consensus(
    fair_probabilities: Sequence[float],
    weights: Sequence[float] | None = None,
) -> ConsensusResult:
    """Calculate consensus statistics from per-bookmaker fair probabilities.

    Args:
        fair_probabilities: Margin-free fair probability for one outcome,
            one value per bookmaker.
        weights: Optional per-bookmaker weights (same length and order as
            fair_probabilities) used to compute a weighted mean. If omitted,
            weighted_mean is None.

    Returns:
        A ConsensusResult with median (the V1 default consensus estimator),
        mean, optional weighted mean, standard deviation, min, max, IQR and
        bookmaker count.

    Raises:
        ValueError: If fair_probabilities is empty, any value is outside
            (0, 1), or weights is provided with mismatched length or a
            non-positive sum.
    """
    if not fair_probabilities:
        raise ValueError("fair_probabilities must contain at least one value")
    if any(not (0.0 < p < 1.0) for p in fair_probabilities):
        raise ValueError("all fair_probabilities must be strictly between 0 and 1")

    values = list(fair_probabilities)
    n = len(values)

    median = statistics.median(values)
    mean = statistics.fmean(values)
    std_dev = statistics.pstdev(values) if n > 1 else 0.0
    minimum = min(values)
    maximum = max(values)
    iqr = _interquartile_range(values)

    weighted_mean: float | None = None
    if weights is not None:
        if len(weights) != n:
            raise ValueError("weights must be the same length as fair_probabilities")
        weight_sum = sum(weights)
        if weight_sum <= 0:
            raise ValueError("sum of weights must be positive")
        weighted_mean = sum(v * w for v, w in zip(values, weights)) / weight_sum

    return ConsensusResult(
        median=median,
        mean=mean,
        weighted_mean=weighted_mean,
        std_dev=std_dev,
        minimum=minimum,
        maximum=maximum,
        interquartile_range=iqr,
        bookmaker_count=n,
    )


def calculate_consensus_per_outcome(
    fair_probabilities_by_outcome: Mapping[str, Sequence[float]],
) -> dict[str, ConsensusResult]:
    """Calculate consensus statistics for every outcome in a market.

    Args:
        fair_probabilities_by_outcome: Mapping of outcome name (e.g. "home",
            "draw", "away") to a sequence of per-bookmaker fair probabilities
            for that outcome.

    Returns:
        A dict mapping each outcome name to its ConsensusResult.
    """
    return {
        outcome: calculate_consensus(probs)
        for outcome, probs in fair_probabilities_by_outcome.items()
    }
