"""Phase V2-1 Workstream B -- tennis ATP Match Winner sealed holdout (2024-2025),
opened ONCE. Refuses to run unless research/platform_v2/tennis/HOLDOUT_SPEC.json matches
its committed SHA-256, and refuses a second run if HOLDOUT_RESULTS.json exists.
Also writes the (already-exposed) 2021-2023 development tables for comparison.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.models.logistic_regression import fit_logistic_regression
from prediction_markets_lab.performance.binary_classification import (
    binary_auc, binary_brier_score, binary_log_loss, fit_calibration_intercept_slope)
from prediction_markets_lab.research import margin_removal_methods as mrm
from prediction_markets_lab.research import probability_reliability as rel

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/tennis"
SPEC, SPEC_HASH, RESULTS = OUT / "HOLDOUT_SPEC.json", OUT / "HOLDOUT_SPEC.sha256", OUT / "HOLDOUT_RESULTS.json"
SEED = 20260923
EPS = 1e-6


def logit(p):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def estimators(df: pd.DataFrame, stack) -> dict[str, np.ndarray]:
    e = {f"market_{m}": df[f"p_a_market_{m}"].to_numpy() for m in mrm.METHODS}
    e["elo_global"] = df.p_a_elo_global.to_numpy()
    e["ranking_baseline"] = df.p_a_ranking.to_numpy()
    X = np.column_stack([logit(df.p_a_market_multiplicative), logit(df.p_a_elo_global)])
    e["stack_market_elo"] = stack.predict_proba(X)
    return e


def metrics(p: np.ndarray, y: np.ndarray) -> dict:
    pk = np.maximum(p, 1 - p)
    w = np.where(p >= 0.5, y, 1 - y)
    i, s = fit_calibration_intercept_slope(list(p), list(y))
    return {"n": int(len(y)), "log_loss": binary_log_loss(list(p), list(y)), "brier": binary_brier_score(list(p), list(y)),
            "auc": binary_auc(list(p), list(y)), "cal_intercept": i, "cal_slope": s,
            "top_pick_accuracy": float(w.mean()), "mean_top_pick_p": float(pk.mean()),
            "expected_correct": float(pk.sum()), "actual_correct": int(w.sum())}


def tables(tag: str, est: dict, df: pd.DataFrame, y: np.ndarray):
    rows_m, rows_b, rows_t, rows_g = [], [], [], []
    for k, p in est.items():
        ok = ~np.isnan(p)
        rows_m.append({"period": tag, "estimator": k, **metrics(p[ok], y[ok])})
        pk = np.maximum(p[ok], 1 - p[ok]); w = np.where(p[ok] >= 0.5, y[ok], 1 - y[ok])
        rows_b += [{"period": tag, "estimator": k, **r} for r in rel.band_table(pk, w)]
        rows_t += [{"period": tag, "estimator": k, **r} for r in rel.threshold_table(pk, w)]
        if k in ("market_multiplicative", "elo_global"):
            for col in ("year", "surface", "tourney_level", "best_of"):
                for g, idx in df[ok].groupby(col).groups.items():
                    pos = df[ok].index.get_indexer(idx)
                    pg, yg = p[ok][pos], y[ok][pos]
                    pkg = np.maximum(pg, 1 - pg); wg = np.where(pg >= 0.5, yg, 1 - yg)
                    hi = pkg >= 0.8
                    lo_, hi_ = rel.wilson(int(wg[hi].sum()), int(hi.sum()))
                    rows_g.append({"period": tag, "estimator": k, "group": f"{col}={g}", "n": int(len(pg)),
                                   "log_loss": binary_log_loss(list(pg), list(yg)), "top_pick_accuracy": float(wg.mean()),
                                   "n_ge_80": int(hi.sum()), "share_ge_80": float(hi.mean()),
                                   "mean_p_ge_80": float(pkg[hi].mean()) if hi.any() else None,
                                   "win_rate_ge_80": float(wg[hi].mean()) if hi.any() else None,
                                   "wilson_low": lo_, "wilson_high": hi_})
    return rows_m, rows_b, rows_t, rows_g


def main() -> None:
    if RESULTS.exists():
        sys.exit("REFUSED: tennis holdout already opened once.")
    if not SPEC.exists() or hashlib.sha256(SPEC.read_bytes()).hexdigest() != SPEC_HASH.read_text().split()[0]:
        sys.exit("REFUSED: HOLDOUT_SPEC.json missing or does not match its frozen hash.")
    spec = json.loads(SPEC.read_text())
    df = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv")
    dev = df[df.year.isin(spec["development_years"])].reset_index(drop=True)
    hold = df[df.year.isin(spec["holdout_years"])].reset_index(drop=True)
    Xd = np.column_stack([logit(dev.p_a_market_multiplicative), logit(dev.p_a_elo_global)])
    stack = fit_logistic_regression(Xd, dev.outcome_a_won.tolist(), ["logit_market", "logit_elo"], l2_penalty=spec["stack_l2"])
    M, Bd, T, G = [], [], [], []
    for tag, d in (("development_2021_2023_exposed", dev), ("SEALED_HOLDOUT_2024_2025", hold)):
        y = d.outcome_a_won.to_numpy()
        m, b, t, g = tables(tag, estimators(d, stack), d, y)
        M += m; Bd += b; T += t; G += g
    est = estimators(hold, stack)
    y = hold.outcome_a_won.to_numpy()
    ll = {k: np.array([-math.log(max(pp if yy else 1 - pp, 1e-15)) for pp, yy in zip(v, y)]) for k, v in est.items()}
    boot = []
    for k in est:
        if k == spec["default_estimator"]:
            continue
        dmean, lo, hi = rel.paired_bootstrap_ci(ll[k], ll[spec["default_estimator"]], seed=SEED)
        boot.append({"estimator": k, "vs": spec["default_estimator"], "log_loss_diff": dmean, "ci95_low": lo,
                     "ci95_high": hi, "better_and_excludes_zero": hi < 0})
    winners = [r for r in boot if r["better_and_excludes_zero"]]
    selected = min(winners, key=lambda r: r["log_loss_diff"])["estimator"] if winners else spec["default_estimator"]
    pd.DataFrame(M).to_csv(OUT / "TENNIS_MODEL_COMPARISON.csv", index=False)
    pd.DataFrame(Bd).to_csv(OUT / "TENNIS_PROBABILITY_BANDS.csv", index=False)
    pd.DataFrame(T).to_csv(OUT / "TENNIS_HIGH_PROBABILITY_ANALYSIS.csv", index=False)
    pd.DataFrame(G).to_csv(OUT / "TENNIS_SUBGROUPS.csv", index=False)
    res = {"opened_at": datetime.now(timezone.utc).isoformat(), "spec_sha256": SPEC_HASH.read_text().split()[0],
           "n_holdout": int(len(hold)), "n_development": int(len(dev)), "selected_estimator": selected,
           "stack_coefficients": {"intercept": stack.intercept, "logit_market": stack.coefficients[0], "logit_elo": stack.coefficients[1]},
           "bootstrap_vs_default": boot, "holdout_metrics": [r for r in M if r["period"].startswith("SEALED")]}
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(M).round(4).to_string())
    print(json.dumps({k: res[k] for k in ("selected_estimator", "stack_coefficients", "bootstrap_vs_default")}, indent=1, default=float))


if __name__ == "__main__":
    main()
