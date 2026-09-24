"""Double Chance events derived from a 1X2 probability vector (Phase V2-4, 2026-09-24).

Pure functions. Order of DC events everywhere: 0 = 1X (home or draw), 1 = X2 (draw or away), 2 = 12 (no draw).
Outcome index: 0 = H, 1 = D, 2 = A.
"""
from __future__ import annotations

import numpy as np

DC_LABELS: tuple[str, str, str] = ("1X", "X2", "12")


def dc_probabilities(p1x2: np.ndarray) -> np.ndarray:
    """(n,3) array of [pH, pD, pA] -> (n,3) array of [P(1X), P(X2), P(12)]. Rows must sum to ~1."""
    p = np.asarray(p1x2, float)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("expected an (n, 3) probability array")
    if np.any(p < 0) or np.any(np.abs(p.sum(1) - 1.0) > 1e-6):
        raise ValueError("1X2 rows must be non-negative and sum to 1")
    return np.stack([p[:, 0] + p[:, 1], p[:, 1] + p[:, 2], p[:, 0] + p[:, 2]], axis=1)


def dc_outcomes(outcome_idx: np.ndarray) -> np.ndarray:
    """(n,) outcome indices -> (n,3) int array: did 1X / X2 / 12 win."""
    o = np.asarray(outcome_idx, int)
    if np.any((o < 0) | (o > 2)):
        raise ValueError("outcome index must be 0, 1 or 2")
    return np.stack([o != 2, o != 0, o != 1], axis=1).astype(int)


def best_selection(dc_p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Index (first wins ties) and probability of the most likely DC event per match. Always >= 2/3."""
    i = np.argmax(dc_p, axis=1)
    return i, dc_p[np.arange(len(i)), i]
