"""Phase V2-2 Workstream B -- WTA Match Winner: development tables + sealed 2024-25 holdout (opened ONCE).
Guarded exactly like the ATP V2-1 holdout. Spec: research/platform_v2/wta/HOLDOUT_SPEC.json."""
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
OUT = REPO / "research/platform_v2/wta"
SPEC, SPEC_HASH, RESULTS = OUT / "HOLDOUT_SPEC.json", OUT / "HOLDOUT_SPEC.sha256", OUT / "HOLDOUT_RESULTS.json"
SEED = 20260923
Z_BONF = 2.807033768343811  # two-sided 99.5%


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def estimators(df, stack):
    e = {f"market_{m}": df[f"p_a_market_{m}"].to_numpy() for m in mrm.METHODS}
    e["elo_global"] = df.p_a_elo_global.to_numpy()
    e["stack_market_elo"] = stack.predict_proba(np.column_stack([logit(df.p_a_market_multiplicative), logit(df.p_a_elo_global)]))
    return e


def metrics(p, y):
    pk, w = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
    i, s = fit_calibration_intercept_slope(list(p), list(y))
    return {"n": int(len(y)), "log_loss": binary_log_loss(list(p), list(y)), "brier": binary_brier_score(list(p), list(y)),
            "auc": binary_auc(list(p), list(y)), "cal_intercept": i, "cal_slope": s, "top_pick_accuracy": float(w.mean()),
            "mean_top_pick_p": float(pk.mean()), "expected_correct": float(pk.sum()), "actual_correct": int(w.sum())}


def slope_ci(p, y, n=1000):
    rng = np.random.default_rng(SEED)
    s = [fit_calibration_intercept_slope(list(p[i]), list(y[i]))[1] for i in (rng.integers(0, len(p), len(p)) for _ in range(n))]
    return [float(np.quantile(s, 0.025)), float(np.quantile(s, 0.975))]


def main() -> None:
    if RESULTS.exists():
        sys.exit("REFUSED: WTA holdout already opened once.")
    if not SPEC.exists() or hashlib.sha256(SPEC.read_bytes()).hexdigest() != SPEC_HASH.read_text().split()[0]:
        sys.exit("REFUSED: HOLDOUT_SPEC.json missing or does not match its frozen hash.")
    spec = json.loads(SPEC.read_text())
    df = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    dev = df[df.year.isin(spec["development_years"])].reset_index(drop=True)
    hold = df[df.year.isin(spec["holdout_years"])].reset_index(drop=True)
    stack = fit_logistic_regression(np.column_stack([logit(dev.p_a_market_multiplicative), logit(dev.p_a_elo_global)]),
                                    dev.outcome_a_won.tolist(), ["logit_market", "logit_elo"], l2_penalty=spec["stack_l2"])
    M, Bd, T, G = [], [], [], []
    for tag, d in (("development_2021_2023", dev), ("SEALED_HOLDOUT_2024_2025", hold)):
        y = d.outcome_a_won.to_numpy()
        for k, p in estimators(d, stack).items():
            M.append({"period": tag, "estimator": k, **metrics(p, y)})
            pk, w = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
            Bd += [{"period": tag, "estimator": k, **r} for r in rel.band_table(pk, w)]
            T += [{"period": tag, "estimator": k, **r} for r in rel.threshold_table(pk, w)]
            if k in ("market_multiplicative", "elo_global"):
                for col in ("year", "surface", "level"):
                    for g, idx in d.groupby(col).groups.items():
                        pos = d.index.get_indexer(idx)
                        pg, yg = p[pos], y[pos]
                        pkg, wg = np.maximum(pg, 1 - pg), np.where(pg >= 0.5, yg, 1 - yg)
                        hi = pkg >= 0.8
                        lo_, hi_ = rel.wilson(int(wg[hi].sum()), int(hi.sum()))
                        G.append({"period": tag, "estimator": k, "group": f"{col}={g}", "n": int(len(pg)),
                                  "top_pick_accuracy": float(wg.mean()), "n_ge_80": int(hi.sum()), "share_ge_80": float(hi.mean()),
                                  "mean_p_ge_80": float(pkg[hi].mean()) if hi.any() else None,
                                  "win_rate_ge_80": float(wg[hi].mean()) if hi.any() else None, "wilson_low": lo_, "wilson_high": hi_})
    est = estimators(hold, stack)
    y = hold.outcome_a_won.to_numpy()
    ll = {k: np.array([-math.log(max(pp if yy else 1 - pp, 1e-15)) for pp, yy in zip(v, y)]) for k, v in est.items()}
    boot = []
    for k in est:
        if k != spec["default_estimator"]:
            dm, lo, hi = rel.paired_bootstrap_ci(ll[k], ll[spec["default_estimator"]], seed=SEED)
            boot.append({"estimator": k, "log_loss_diff": dm, "ci95_low": lo, "ci95_high": hi, "better_and_excludes_zero": hi < 0})
    winners = [r for r in boot if r["better_and_excludes_zero"]]
    selected = min(winners, key=lambda r: r["log_loss_diff"])["estimator"] if winners else spec["default_estimator"]
    p = est[selected]
    pk, w = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
    band_checks = []
    for r in rel.band_table(pk, w):
        if r["n"] >= 200:
            lo, hi = rel.wilson(r["actual_wins"], r["n"], z=Z_BONF)
            band_checks.append({"band": r["band"], "n": r["n"], "mean_predicted": r["mean_predicted"], "actual_rate": r["actual_rate"],
                                "wilson995_low": lo, "wilson995_high": hi, "inside": lo <= r["mean_predicted"] <= hi})
    sci = slope_ci(p, y)
    verdict_calibrated = (sci[0] <= 1 <= sci[1]) and all(b["inside"] for b in band_checks)
    for name, frame in (("WTA_MODEL_COMPARISON.csv", M), ("WTA_PROBABILITY_BANDS.csv", Bd),
                        ("WTA_HIGH_PROBABILITY_ANALYSIS.csv", T), ("WTA_SUBGROUPS.csv", G)):
        pd.DataFrame(frame).to_csv(OUT / name, index=False)
    res = {"opened_at": datetime.now(timezone.utc).isoformat(), "spec_sha256": SPEC_HASH.read_text().split()[0],
           "n_holdout": int(len(hold)), "n_development": int(len(dev)), "selected_estimator": selected,
           "stack_coefficients": {"intercept": stack.intercept, "logit_market": stack.coefficients[0], "logit_elo": stack.coefficients[1]},
           "bootstrap_vs_default": boot, "selected_slope_ci95": sci, "band_checks_995": band_checks,
           "calibration_rule_passed": verdict_calibrated,
           "elo_slope_ci95": slope_ci(est["elo_global"], y)}
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(M).round(4).to_string())
    print(json.dumps({k: res[k] for k in ("selected_estimator", "stack_coefficients", "bootstrap_vs_default", "selected_slope_ci95",
                                          "band_checks_995", "calibration_rule_passed", "elo_slope_ci95")}, indent=1, default=float))


if __name__ == "__main__":
    main()
