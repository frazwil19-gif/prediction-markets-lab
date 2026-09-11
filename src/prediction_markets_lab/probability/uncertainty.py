"""Paired bootstrap confidence intervals for model-vs-market metric deltas.

Point-estimate deltas alone are insufficient (Stage 3B directive
section 9: "do not claim superiority merely because 1.004 < 1.009").
This module quantifies whether a log-loss/Brier gap between a
candidate model and the market benchmark is stable, via two distinct
resampling schemes, always reported separately (never mixed):

- "match_level": i.i.d. resampling of individual matches. Simple, but
  assumes matches are independent, which football matches on the same
  matchday plausibly are not (shared refereeing pool, weather,
  systematic market conditions on a given date).
- "block_by_date": resamples whole match DATES with replacement (every
  match on a resampled date moves together), a defensible cluster unit
  directly available in this dataset. Preferred when the two disagree
  meaningfully, since it does not assume independence across same-day
  matches.

Both use a fixed, documented seed for reproducibility -- this is
research reporting, not a randomised procedure that should give a
different answer each run.

Performance note: log_loss/brier are both simple per-match means, so
a resampled metric equals the mean of the *per-match* metric values at
the resampled indices -- it is mathematically identical to rebuilding
the resampled prediction lists and calling multiclass_log_loss /
multiclass_brier_score on them, but does not require re-validating
every probability dict on every one of n_resamples iterations. This
module computes each match's single-observation loss once (which
validates its probabilities exactly once), then resamples over the
resulting float arrays. This is not an approximation -- it is the same
computation, algebraically -- and it is what makes n_resamples=2000
tractable over a real multi-thousand-match pooled sample.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from prediction_markets_lab.performance.brier import brier_score_single
from prediction_markets_lab.performance.log_loss import log_loss_single

DEFAULT_N_RESAMPLES = 2000
DEFAULT_SEED = 42
DEFAULT_CI_LEVEL = 0.95


@dataclass(frozen=True)
class BootstrapResult:
    """A bootstrap confidence interval for one metric delta.

    point_estimate is the delta computed on the FULL (non-resampled)
    sample -- the CI describes uncertainty around this single number,
    it is not itself the mean of the resampled deltas (which can differ
    slightly due to resampling noise/bias; reporting the full-sample
    point estimate alongside a resampled CI is standard practice).
    """

    metric: str  # "log_loss" or "brier"
    method: str  # "match_level" or "block_by_date"
    point_estimate: float
    ci_lower: float
    ci_upper: float
    ci_level: float
    n_resamples: int
    n_matches: int


def _percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolation percentile, p in [0, 1], on an already-sorted list."""
    if not sorted_values:
        raise ValueError("cannot compute a percentile of an empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = p * (len(sorted_values) - 1)
    lower_idx = int(rank)
    upper_idx = min(lower_idx + 1, len(sorted_values) - 1)
    frac = rank - lower_idx
    return sorted_values[lower_idx] * (1 - frac) + sorted_values[upper_idx] * frac


def paired_bootstrap_delta(
    model_preds: list[dict],
    market_preds: list[dict],
    actuals: list[str],
    metric: str,
    dates: list | None = None,
    method: str = "match_level",
    n_resamples: int = DEFAULT_N_RESAMPLES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> BootstrapResult:
    """Paired bootstrap CI for (model_metric - market_metric).

    Args:
        model_preds, market_preds, actuals: same length, index-aligned
            -- entry i in each list describes the same match.
        metric: "log_loss" or "brier".
        dates: required when method="block_by_date" -- one date (or any
            hashable cluster key, e.g. a matchweek id) per match, same
            order/length as the prediction lists.
        method: "match_level" (i.i.d. resample of match indices) or
            "block_by_date" (resample whole dates with replacement).
        n_resamples: number of bootstrap resamples.
        seed: fixed RNG seed for reproducibility.
        ci_level: e.g. 0.95 for a 95% CI (2.5th/97.5th percentile).

    Returns:
        A BootstrapResult with the full-sample point estimate and the
        percentile CI from the resampled delta distribution.

    Raises:
        ValueError: on length mismatch, empty input, an unknown metric
            or method, or method="block_by_date" without dates.
    """
    n = len(actuals)
    if not (len(model_preds) == len(market_preds) == n):
        raise ValueError("model_preds, market_preds, and actuals must be the same length")
    if n == 0:
        raise ValueError("cannot bootstrap over zero matches")
    if metric not in ("log_loss", "brier"):
        raise ValueError(f"metric must be 'log_loss' or 'brier', got {metric!r}")
    if method not in ("match_level", "block_by_date"):
        raise ValueError(f"method must be 'match_level' or 'block_by_date', got {method!r}")
    if method == "block_by_date" and (dates is None or len(dates) != n):
        raise ValueError("method='block_by_date' requires dates of the same length as the predictions")

    single_fn = log_loss_single if metric == "log_loss" else brier_score_single

    # Each match's per-observation loss is computed exactly once here
    # (this is also where probability-dict validation happens, exactly
    # once per match rather than once per resample -- see module docstring).
    model_losses = [single_fn(probs, actual) for probs, actual in zip(model_preds, actuals)]
    market_losses = [single_fn(probs, actual) for probs, actual in zip(market_preds, actuals)]

    point_estimate = (sum(model_losses) / n) - (sum(market_losses) / n)

    rng = random.Random(seed)
    deltas: list[float] = []

    if method == "match_level":
        indices = list(range(n))
        for _ in range(n_resamples):
            model_total = 0.0
            market_total = 0.0
            for _ in range(n):
                i = rng.choice(indices)
                model_total += model_losses[i]
                market_total += market_losses[i]
            deltas.append((model_total / n) - (market_total / n))
    else:
        by_date: dict = {}
        for i, d in enumerate(dates):
            by_date.setdefault(d, []).append(i)
        unique_dates = list(by_date.keys())
        # Precompute each date's aggregate loss totals and match count
        # once, so a resample only needs to sum per-date aggregates
        # rather than re-walking every match on every resampled date.
        date_model_total = {d: sum(model_losses[i] for i in idxs) for d, idxs in by_date.items()}
        date_market_total = {d: sum(market_losses[i] for i in idxs) for d, idxs in by_date.items()}
        date_count = {d: len(idxs) for d, idxs in by_date.items()}
        for _ in range(n_resamples):
            sampled_dates = [rng.choice(unique_dates) for _ in range(len(unique_dates))]
            model_total = sum(date_model_total[d] for d in sampled_dates)
            market_total = sum(date_market_total[d] for d in sampled_dates)
            resample_n = sum(date_count[d] for d in sampled_dates)
            deltas.append((model_total / resample_n) - (market_total / resample_n))

    deltas.sort()
    lower_p = (1 - ci_level) / 2
    upper_p = 1 - lower_p

    return BootstrapResult(
        metric=metric,
        method=method,
        point_estimate=point_estimate,
        ci_lower=_percentile(deltas, lower_p),
        ci_upper=_percentile(deltas, upper_p),
        ci_level=ci_level,
        n_resamples=n_resamples,
        n_matches=n,
    )
