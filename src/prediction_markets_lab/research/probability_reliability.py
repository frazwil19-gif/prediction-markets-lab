"""Probability-reliability reporting helpers for Platform V2 (Phase V2-1, 2026-09-23).

Pure functions: fixed probability bands, threshold tables (expected vs realised),
Wilson intervals, top-pick selection for n-way markets, multi-class log loss / Brier.
Used by every V2 probability-engine report so all engines are compared identically.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

V2_BANDS: tuple[tuple[float, float, str], ...] = (
    (0.50, 0.55, "50-54.9%"), (0.55, 0.60, "55-59.9%"), (0.60, 0.65, "60-64.9%"),
    (0.65, 0.70, "65-69.9%"), (0.70, 0.75, "70-74.9%"), (0.75, 0.80, "75-79.9%"),
    (0.80, 0.85, "80-84.9%"), (0.85, 0.90, "85-89.9%"), (0.90, 0.95, "90-94.9%"),
    (0.95, 1.0000001, "95%+"),
)
V2_THRESHOLDS: tuple[float, ...] = (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
Z95 = 1.959963984540054
EPS = 1e-15


def wilson(k: int, n: int, z: float = Z95) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def top_pick(probs: Sequence[float]) -> tuple[int, float]:
    """Index and probability of the most likely outcome (first index wins exact ties)."""
    if not probs:
        raise ValueError("empty probability vector")
    i = int(np.argmax(probs))
    return i, float(probs[i])


def _row(label_key: str, label, ps: np.ndarray, ws: np.ndarray, total: int) -> dict:
    n = len(ps)
    k = int(ws.sum()) if n else 0
    lo, hi = wilson(k, n)
    mean_p = float(ps.mean()) if n else None
    return {label_key: label, "n": n, "share_of_events": n / total if total else None, "mean_predicted": mean_p,
            "expected_wins": float(ps.sum()) if n else 0.0, "actual_wins": k,
            "actual_rate": k / n if n else None, "difference_pp": (k / n - mean_p) * 100 if n else None,
            "wilson95_low": lo, "wilson95_high": hi}


def band_table(pick_probs: Sequence[float], pick_won: Sequence[int]) -> list[dict]:
    p, w = np.asarray(pick_probs, float), np.asarray(pick_won, int)
    out = []
    for lo, hi, lab in V2_BANDS:
        m = (p >= lo) & (p < hi)
        out.append(_row("band", lab, p[m], w[m], len(p)))
    return out


def threshold_table(pick_probs: Sequence[float], pick_won: Sequence[int],
                    thresholds: Sequence[float] = V2_THRESHOLDS) -> list[dict]:
    p, w = np.asarray(pick_probs, float), np.asarray(pick_won, int)
    return [_row("threshold", t, p[p >= t], w[p >= t], len(p)) for t in thresholds]


def multiclass_log_loss(prob_rows: Sequence[Sequence[float]], outcome_idx: Sequence[int]) -> np.ndarray:
    """Per-event log loss of the probability assigned to the realised outcome."""
    return np.array([-math.log(max(float(r[i]), EPS)) for r, i in zip(prob_rows, outcome_idx)])


def multiclass_brier(prob_rows: Sequence[Sequence[float]], outcome_idx: Sequence[int]) -> np.ndarray:
    out = []
    for r, i in zip(prob_rows, outcome_idx):
        out.append(sum((float(p) - (1.0 if j == i else 0.0)) ** 2 for j, p in enumerate(r)))
    return np.array(out)


def paired_bootstrap_ci(a: np.ndarray, b: np.ndarray, seed: int, n_resamples: int = 2000) -> tuple[float, float, float]:
    """Mean(a-b) with a percentile 95% CI, resampling events jointly."""
    if len(a) != len(b) or len(a) == 0:
        raise ValueError("series must be non-empty and equal length")
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), size=(n_resamples, len(d)))].mean(axis=1)
    return float(d.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))
