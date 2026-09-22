"""Bootstrap confidence intervals for single-series backtest summary
statistics (win rate, ROI, mean net EV, mean Brier/log loss).

Distinct from probability.uncertainty.paired_bootstrap_delta and
performance.bootstrap.paired_bootstrap_mean_diff, both of which compare
TWO paired series (model vs. market). A backtest performance report also
needs an uncertainty band on ONE series' own summary statistic (e.g. "is
this ROI distinguishable from zero"), which those two modules do not
provide -- this module adds that single-series case as new, non-
duplicative functionality, without touching either existing tested file.

Uses the same percentile-bootstrap methodology (fixed seed, documented
resample count) as the existing bootstrap modules, for consistency across
the project's reporting.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

DEFAULT_N_RESAMPLES = 2000
DEFAULT_SEED = 20260922  # fixed, documented -- the date Phase 1 backtesting began
DEFAULT_CI_LEVEL = 0.95


@dataclass(frozen=True)
class BootstrapCI:
    """A single-series bootstrap confidence interval for a summary statistic."""

    statistic_name: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    ci_level: float
    n_resamples: int
    n: int

    @property
    def excludes_zero(self) -> bool:
        return self.ci_lower > 0.0 or self.ci_upper < 0.0


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute a percentile of an empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = p * (len(sorted_values) - 1)
    lower_idx = int(rank)
    upper_idx = min(lower_idx + 1, len(sorted_values) - 1)
    frac = rank - lower_idx
    return sorted_values[lower_idx] * (1 - frac) + sorted_values[upper_idx] * frac


def bootstrap_mean_ci(
    values: list[float],
    statistic_name: str,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> BootstrapCI:
    """Percentile bootstrap CI for the mean of one series (i.i.d. resample).

    Args:
        values: per-bet (or per-match) values whose MEAN is the statistic
            of interest (e.g. per-bet net profit -> mean is ROI-per-unit-
            stake once divided by stake; per-bet win indicator -> mean is
            win rate).
        statistic_name: label only, carried through to the result for
            reporting (e.g. "net_profit_per_bet_gbp").
        n_resamples: number of bootstrap resamples.
        seed: fixed RNG seed for reproducibility.
        ci_level: e.g. 0.95 for a 95% CI.

    Returns:
        A BootstrapCI with the point estimate computed on the ORIGINAL
        (non-resampled) data.

    Raises:
        ValueError: if values is empty.
    """
    n = len(values)
    if n == 0:
        raise ValueError("cannot bootstrap over zero values")

    point_estimate = sum(values) / n
    rng = random.Random(seed)
    indices = list(range(n))
    resampled_means: list[float] = []
    for _ in range(n_resamples):
        total = 0.0
        for _ in range(n):
            total += values[rng.choice(indices)]
        resampled_means.append(total / n)
    resampled_means.sort()

    lower_p = (1 - ci_level) / 2
    upper_p = 1 - lower_p
    return BootstrapCI(
        statistic_name=statistic_name,
        point_estimate=point_estimate,
        ci_lower=_percentile(resampled_means, lower_p),
        ci_upper=_percentile(resampled_means, upper_p),
        ci_level=ci_level,
        n_resamples=n_resamples,
        n=n,
    )


def bootstrap_ratio_ci(
    numerators: list[float],
    denominators: list[float],
    statistic_name: str,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> BootstrapCI:
    """Percentile bootstrap CI for sum(numerators)/sum(denominators)
    (e.g. ROI = total net profit / total staked), resampling bet INDICES
    so numerator/denominator pairs stay matched per resample.

    Args:
        numerators: per-bet numerator values (e.g. net profit per bet).
        denominators: per-bet denominator values (e.g. stake per bet),
            same length/order as numerators.
        statistic_name: label only.
        n_resamples, seed, ci_level: see bootstrap_mean_ci.

    Returns:
        A BootstrapCI for the ratio statistic.

    Raises:
        ValueError: if the lists differ in length, are empty, or the
            original (non-resampled) sum of denominators is zero.
    """
    if len(numerators) != len(denominators):
        raise ValueError("numerators and denominators must be the same length")
    n = len(numerators)
    if n == 0:
        raise ValueError("cannot bootstrap over zero values")
    total_denominator = sum(denominators)
    if total_denominator == 0:
        raise ValueError("sum of denominators is zero -- ratio is undefined")

    point_estimate = sum(numerators) / total_denominator
    rng = random.Random(seed)
    indices = list(range(n))
    resampled_ratios: list[float] = []
    for _ in range(n_resamples):
        num_total = 0.0
        den_total = 0.0
        for _ in range(n):
            i = rng.choice(indices)
            num_total += numerators[i]
            den_total += denominators[i]
        if den_total != 0:
            resampled_ratios.append(num_total / den_total)
    resampled_ratios.sort()

    lower_p = (1 - ci_level) / 2
    upper_p = 1 - lower_p
    return BootstrapCI(
        statistic_name=statistic_name,
        point_estimate=point_estimate,
        ci_lower=_percentile(resampled_ratios, lower_p),
        ci_upper=_percentile(resampled_ratios, upper_p),
        ci_level=ci_level,
        n_resamples=n_resamples,
        n=n,
    )
