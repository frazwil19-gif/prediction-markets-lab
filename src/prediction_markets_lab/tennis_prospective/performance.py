"""Prospective tennis prediction performance + pre-registered evidence-maturity labels.
Only validated-source, settled, non-void predictions count toward an engine."""
from __future__ import annotations

import math

import numpy as np

from prediction_markets_lab.research import probability_reliability as rel

COLLECTING_MAX = 50
EARLY_MAX = 300
INTERMEDIATE_MIN_HIGH = 100
MATURE_MIN = 1000
MATURE_MIN_HIGH = 300
HIGH_P = 0.80


def maturity(n_settled: int, n_high: int) -> str:
    if n_settled >= MATURE_MIN and n_high >= MATURE_MIN_HIGH:
        return "MATURE"
    if n_settled >= EARLY_MAX and n_high >= INTERMEDIATE_MIN_HIGH:
        return "INTERMEDIATE"
    if n_settled >= COLLECTING_MAX:
        return "EARLY"
    return "COLLECTING"


def engine_performance(preds: list[dict], settlements: dict[str, dict]) -> dict:
    rows = []
    for p in preds:
        s = settlements.get(p["prediction_id"])
        if str(p.get("source_validated")) not in ("True", "true", "1") or s is None:
            continue
        if s["status"] not in ("SETTLED_CORRECT", "SETTLED_INCORRECT"):
            continue
        rows.append((float(p["predicted_probability"]), 1 if s["status"] == "SETTLED_CORRECT" else 0))
    n = len(rows)
    pk = np.array([r[0] for r in rows]) if rows else np.array([])
    w = np.array([r[1] for r in rows]) if rows else np.array([])
    n_high = int((pk >= HIGH_P).sum()) if n else 0
    out = {"settled": n, "settled_ge_80": n_high, "maturity": maturity(n, n_high)}
    if n:
        out.update({"correct": int(w.sum()), "accuracy": float(w.mean()), "expected_correct": float(pk.sum()),
                    "brier_top_pick": float(((pk - w) ** 2).mean()),
                    "log_loss_top_pick": float(np.mean([-math.log(max(p if y else 1 - p, 1e-15)) for p, y in zip(pk, w)])),
                    "bands": rel.band_table(pk, w), "thresholds": rel.threshold_table(pk, w, (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95))})
    return out
