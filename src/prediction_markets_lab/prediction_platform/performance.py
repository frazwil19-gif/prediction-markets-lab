"""Prospective calibration database: pooled AND per sport/engine/market/version decomposition."""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from prediction_markets_lab.prediction_platform.schema import HIGH_P, THRESHOLDS
from prediction_markets_lab.research.probability_reliability import V2_BANDS, wilson

# Pre-registered (PROSPECTIVE_PROTOCOL.md section 5/6); identical to the tennis protocol.
COLLECTING_MAX, EARLY_MAX, INTERMEDIATE_MIN_HIGH, MATURE_MIN, MATURE_MIN_HIGH = 50, 300, 100, 1000, 300
ALARM_MIN_HIGH, ALARM_SHORTFALL = 100, 0.10
Z995 = 2.807033768343811
TIMING_BUCKETS = ((0, 360, "<6h"), (360, 1440, "6-24h"), (1440, 2880, "24-48h"), (2880, math.inf, ">48h"))


def maturity(n_settled_units: int, n_high_units: int) -> str:
    if n_settled_units >= MATURE_MIN and n_high_units >= MATURE_MIN_HIGH:
        return "MATURE"
    if n_settled_units >= EARLY_MAX and n_high_units >= INTERMEDIATE_MIN_HIGH:
        return "INTERMEDIATE"
    if n_settled_units >= COLLECTING_MAX:
        return "EARLY"
    return "COLLECTING"


def settled_rows(preds: list[dict], settlements: dict[str, dict]) -> list[dict]:
    out = []
    for p in preds:
        s = settlements.get(p["prediction_id"])
        if str(p.get("prediction_valid")) != "True" or s is None or s["settlement_status"] != "SETTLED":
            continue
        out.append({**p, "p": float(p["estimated_probability"]), "y": int(s["correct"])})
    return out


def metrics(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    p = np.clip(np.array([r["p"] for r in rows]), 1e-6, 1 - 1e-6)
    y = np.array([r["y"] for r in rows])
    ece = 0.0
    bands = []
    for lo, hi, lab in V2_BANDS:
        m = (p >= lo) & (p < hi)
        if m.any():
            ece += m.sum() / n * abs(p[m].mean() - y[m].mean())
            lo95, hi95 = wilson(int(y[m].sum()), int(m.sum()))
            bands.append({"band": lab, "n": int(m.sum()), "mean_pred": float(p[m].mean()), "actual": float(y[m].mean()),
                          "wilson95": [lo95, hi95]})
    thr = []
    for t in THRESHOLDS:
        m = p >= t
        if m.any():
            thr.append({"threshold": t, "n": int(m.sum()), "mean_pred": float(p[m].mean()), "actual": float(y[m].mean()),
                        "wilson995": list(wilson(int(y[m].sum()), int(m.sum()), Z995))})
    return {"n": n, "correct": int(y.sum()), "incorrect": int(n - y.sum()), "mean_pred": float(p.mean()),
            "actual": float(y.mean()), "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), "ece_bands": float(ece),
            "bands": bands, "thresholds": thr}


def _units(rows: list[dict]) -> int:
    """Maturity unit = event (1X2/DC have 3 dependent rows per match)."""
    return len({r["event_key"] for r in rows})


def report(preds: list[dict], settlements: dict[str, dict]) -> dict:
    rows = settled_rows(preds, settlements)
    out: dict = {"pooled": metrics(rows), "by": {}}
    for dim in ("sport", "engine_id", "market", "engine_version"):
        g: dict[str, list] = defaultdict(list)
        for r in rows:
            g[r[dim] if dim != "engine_version" else f"{r['engine_id']}@{r['engine_version']}"].append(r)
        out["by"][dim] = {k: metrics(v) for k, v in sorted(g.items())}
    # pooled >=80 band decomposed by engine (detects one engine degrading inside a healthy pool)
    hi = [r for r in rows if r["p"] >= HIGH_P]
    dec: dict[str, list] = defaultdict(list)
    for r in hi:
        dec[r["engine_id"]].append(r)
    out["ge80_decomposition"] = {"pooled": metrics(hi), "by_engine": {k: metrics(v) for k, v in sorted(dec.items())}}
    eng: dict[str, dict] = {}
    for eid in sorted({p["engine_id"] for p in preds}):
        er = [r for r in rows if r["engine_id"] == eid]
        eh = [r for r in er if r["p"] >= HIGH_P]
        pred_n = [p for p in preds if p["engine_id"] == eid and str(p.get("prediction_valid")) == "True"]
        alarm = (len(eh) >= ALARM_MIN_HIGH and
                 np.mean([r["y"] for r in eh]) < np.mean([r["p"] for r in eh]) - ALARM_SHORTFALL)
        eng[eid] = {"predictions": len(pred_n), "prediction_events": _units(pred_n), "settled_rows": len(er),
                    "settled_events": _units(er), "settled_ge80_events": _units(eh),
                    "maturity": maturity(_units(er), _units(eh)), "ge80_maturity": maturity(_units(eh), _units(eh)),
                    "alarm_review_required": bool(alarm)}
    out["engines"] = eng
    tb: dict[str, list] = defaultdict(list)
    for r in rows:
        m = float(r["minutes_to_event"])
        for lo, hi_, lab in TIMING_BUCKETS:
            if lo <= m < hi_:
                tb[lab].append(r)
    out["by_minutes_to_event"] = {k: (metrics(v) if len(v) >= 100 else {"n": len(v), "note": "reported at n>=100"})
                                  for k, v in tb.items()}
    return out
