"""Paired percentile bootstrap for comparing two models' per-match losses.

Distinct from research/football_cycle2_development.py's
`bootstrap_ci_mean_diff`, which resamples two INDEPENDENT groups
separately (used for a two-sample subgroup comparison, e.g. "high SOT
differential" vs "low SOT differential" matches). Here the two series
being compared are the SAME matches scored by two different models
(e.g. Model A's log loss vs Model B's log loss on an identical evaluation
set) -- a paired comparison, so each bootstrap resample must draw the
SAME match indices for both series, not resample them independently
(independent resampling would overstate the uncertainty of the
difference by ignoring the two series' per-match correlation).

This is the same paired-bootstrap logic already used informally inline
in Tennis Cycle 1's holdout evaluation and Stage 3B's model-vs-market
comparisons; promoted here to one tested, reusable function so the Gate 1
probability-architecture comparison (and any future model-vs-model
comparison) does not each re-derive it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PairedBootstrapResult:
    point_estimate: float  # mean(series_a) - mean(series_b), on the ORIGINAL (non-resampled) data
    ci_lower: float
    ci_upper: float
    n: int
    n_resamples: int
    seed: int

    @property
    def excludes_zero(self) -> bool:
        return self.ci_lower > 0.0 or self.ci_upper < 0.0


def paired_bootstrap_mean_diff(
    series_a: list[float],
    series_b: list[float],
    seed: int,
    n_resamples: int = 2000,
    confidence_level: float = 0.95,
) -> PairedBootstrapResult:
    """Percentile bootstrap CI for mean(series_a) - mean(series_b), resampling
    MATCH INDICES (not each series independently) so per-match pairing is preserved.

    Args:
        series_a, series_b: per-match values (e.g. per-match log loss)
            for two models, same length, same match order (index i in
            series_a and series_b must refer to the same match).
        seed: RNG seed -- required explicitly (no default) so every
            caller states its own seed choice rather than silently
            inheriting one, per this project's provenance discipline.
        n_resamples: number of bootstrap resamples.
        confidence_level: e.g. 0.95 for a 95% CI.

    Returns:
        A PairedBootstrapResult with the point estimate (on the original
        data, not a resample) and the percentile CI bounds.

    Raises:
        ValueError: if series_a/series_b differ in length, are empty,
            n_resamples < 1, or confidence_level is not in (0, 1).
    """
    if len(series_a) != len(series_b):
        raise ValueError(
            f"series_a and series_b must be the same length ({len(series_a)} != {len(series_b)})"
        )
    n = len(series_a)
    if n == 0:
        raise ValueError("cannot bootstrap over zero matched pairs")
    if n_resamples < 1:
        raise ValueError(f"n_resamples must be >= 1, got {n_resamples}")
    if not (0.0 < confidence_level < 1.0):
        raise ValueError(f"confidence_level must be in (0, 1), got {confidence_level}")

    a = np.asarray(series_a, dtype=float)
    b = np.asarray(series_b, dtype=float)
    point = float(a.mean() - b.mean())

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    resampled_diffs = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    resampled_diffs.sort()

    alpha = 1.0 - confidence_level
    lo_idx = int((alpha / 2.0) * n_resamples)
    hi_idx = min(int((1.0 - alpha / 2.0) * n_resamples), n_resamples - 1)

    return PairedBootstrapResult(
        point_estimate=point,
        ci_lower=float(resampled_diffs[lo_idx]),
        ci_upper=float(resampled_diffs[hi_idx]),
        n=n,
        n_resamples=n_resamples,
        seed=seed,
    )
