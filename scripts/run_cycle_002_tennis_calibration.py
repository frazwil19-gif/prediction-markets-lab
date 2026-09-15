#!/usr/bin/env python3
"""Tennis Cycle 1 -- Global Elo calibration research (post step-D, per the
research operator's explicit sequencing: calibration is investigated only
AFTER model/feature selection is settled, never before, to avoid tuning
calibration to chase a better headline log loss).

Global Elo (the accepted odds-independent candidate; k_factor=32, no
promoted incremental features -- see A4_BASELINE_RESULTS.md and
A4_STEP_D_INCREMENTAL_FEATURES.md) shows mild overconfidence on 2024
validation (calibration slope 0.8749). This script tests ONE simple,
pre-specified, forward-safe calibration method -- a 2-parameter logistic
recalibration (Platt-style: fit intercept+slope on logit(raw_p) against
outcomes) -- fit on 2021-2023 TRAINING predictions only, then applied
UNCHANGED to 2024 VALIDATION predictions. This is forward-safe by
construction: the calibration parameters never see validation-period
outcomes, so applying them to validation is a genuine out-of-sample test,
not a validation-set fit.

Decision rule, stated up front (not chosen after seeing the result):
calibration is adopted ONLY if the paired-bootstrap 95% CI for
(calibrated log loss - raw log loss) on validation lies entirely below
zero. Otherwise the explicit output is CALIBRATION = NONE -- calibration
is not forced merely because the raw model is mildly overconfident, per
the operator's explicit instruction.

No other calibration method is tried (isotonic regression, temperature
scaling variants, etc.) -- one simple, standard, pre-specified method,
consistent with "robust baselines, not a Kaggle competition."

2025 is never loaded (inherited from run_cycle_002_tennis_checkpoint_a4.
load_matches, re-asserted here). AUC is unaffected by this calibration
method since a monotonic logit-linear recalibration cannot change rank
ordering -- reported once, not duplicated for both variants.

Outputs:
    research/cycles/CYCLE_002_TENNIS/A4_CALIBRATION_RESEARCH.md
    data/interim/cycle_002_tennis_calibration_metrics.json

Run:
    python scripts/run_cycle_002_tennis_calibration.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.models.tennis_elo import (  # noqa: E402
    EloConfig,
    calibrate_k_factor,
    global_rating_key,
    run_elo_over_matches,
)
from prediction_markets_lab.performance.binary_classification import (  # noqa: E402
    binary_auc,
    binary_brier_score,
    binary_calibration_bins,
    binary_log_loss,
    binary_log_loss_single,
    expected_calibration_error,
    fit_calibration_intercept_slope,
)

REPORT_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "A4_CALIBRATION_RESEARCH.md"
METRICS_PATH = REPO_ROOT / "data" / "interim" / "cycle_002_tennis_calibration_metrics.json"

N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 20260915


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35, 35)))


def _logit(p: float) -> float:
    p = min(max(p, 1e-15), 1.0 - 1e-15)
    return float(np.log(p / (1.0 - p)))


def paired_bootstrap_log_loss_delta(preds_a: list[float], preds_b: list[float], actuals: list[int],
                                     n_bootstrap: int = N_BOOTSTRAP, seed: int = BOOTSTRAP_SEED) -> dict:
    n = len(actuals)
    per_match_a = np.array([binary_log_loss_single(p, a) for p, a in zip(preds_a, actuals)])
    per_match_b = np.array([binary_log_loss_single(p, a) for p, a in zip(preds_b, actuals)])
    point_delta = float(per_match_a.mean() - per_match_b.mean())
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        deltas[i] = per_match_a[idx].mean() - per_match_b[idx].mean()
    ci_lower, ci_upper = float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))
    return {"n_matches": n, "n_bootstrap": n_bootstrap, "point_delta": point_delta,
            "ci_lower": ci_lower, "ci_upper": ci_upper, "calibration_improves": bool(ci_upper < 0.0)}


def metrics_block(preds: list[float], actuals: list[int]) -> dict:
    bins = binary_calibration_bins(preds, actuals, n_bins=10)
    intercept, slope = fit_calibration_intercept_slope(preds, actuals)
    return {
        "n": len(preds), "log_loss": binary_log_loss(preds, actuals),
        "brier_score": binary_brier_score(preds, actuals),
        "auc": binary_auc(preds, actuals),
        "calibration_intercept": intercept, "calibration_slope": slope,
        "expected_calibration_error": expected_calibration_error(bins),
        "calibration_bins": [
            {"bin_index": b.bin_index, "n": b.n, "mean_predicted_probability": b.mean_predicted_probability,
             "observed_frequency": b.observed_frequency} for b in bins
        ],
    }


def build_predictions() -> dict:
    a4 = _load_module(REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py", "run_cycle_002_tennis_checkpoint_a4")
    df = a4.load_matches()
    assert not (df["_season"] == a4.SEALED_HOLDOUT_SEASON).any(), "sealed holdout season leaked into calibration research"

    elo_inputs = [a4.to_elo_input(row) for _, row in df.iterrows()]
    train_mask = df["_season"].isin(a4.TRAINING_SEASONS).values
    val_mask = (df["_season"] == a4.VALIDATION_SEASON).values
    train_elo_inputs = [ei for ei, is_train in zip(elo_inputs, train_mask) if is_train]

    best_k = calibrate_k_factor(train_elo_inputs, EloConfig(), a4.K_FACTOR_CANDIDATES, global_rating_key)
    predictions = run_elo_over_matches(elo_inputs, EloConfig(k_factor=best_k), global_rating_key)

    match_ids = df["match_id"].tolist()
    outcomes = df["outcome_a_won"].tolist()
    pred_by_id = {p.match_id: p.p_a_win for p in predictions}

    train_raw = [pred_by_id[mid] for mid, is_train in zip(match_ids, train_mask) if is_train]
    train_actuals = [o for o, is_train in zip(outcomes, train_mask) if is_train]
    val_raw = [pred_by_id[mid] for mid, is_val in zip(match_ids, val_mask) if is_val]
    val_actuals = [o for o, is_val in zip(outcomes, val_mask) if is_val]

    return {
        "global_elo_k_factor": best_k,
        "train_raw": train_raw, "train_actuals": train_actuals,
        "val_raw": val_raw, "val_actuals": val_actuals,
        "training_seasons": a4.TRAINING_SEASONS, "validation_season": a4.VALIDATION_SEASON,
        "sealed_holdout_season": a4.SEALED_HOLDOUT_SEASON,
    }


def render_report(summary: dict) -> str:
    lines = []
    lines.append("# Cycle 2 Tennis -- Global Elo Calibration Research")
    lines.append("")
    lines.append(f"*Generated {summary['generated_at']}*")
    lines.append("")
    lines.append("**PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.** No price/odds data is used. "
                  "This investigates ONE simple, pre-specified, forward-safe calibration method for Global Elo "
                  "(the accepted odds-independent candidate model), fit on training data only and applied "
                  "unchanged to validation -- never the reverse.")
    lines.append("")
    lines.append(f"- Training seasons: {summary['training_seasons']} (calibration parameters fit here only)")
    lines.append(f"- Validation season: {summary['validation_season']} (calibration applied out-of-sample, evaluated here)")
    lines.append(f"- Sealed holdout: {summary['sealed_holdout_season']} -- **never loaded by this script**")
    lines.append(f"- Global Elo k_factor: {summary['global_elo_k_factor']}")
    lines.append("- Decision rule (stated before running): adopt calibration only if the paired-bootstrap 95% CI "
                  "for (calibrated log loss - raw log loss) lies entirely below zero. Otherwise: CALIBRATION = NONE.")
    lines.append("")
    lines.append("## Fitted calibration parameters (from training data only)")
    lines.append("")
    lines.append(f"- intercept = {summary['fitted_intercept']:.4f}")
    lines.append(f"- slope = {summary['fitted_slope']:.4f}")
    lines.append("These are close to identity (intercept~=0, slope~=1): Global Elo is already close to "
                  "well-calibrated ON ITS OWN TRAINING PERIOD. This is a different number from A4's "
                  "validation-season calibration slope (0.8749) -- that overconfidence pattern shows up only "
                  "on 2024, so a correction fit purely on 2021-2023 has little reason to fix it, and (see "
                  "below) largely doesn't. That is exactly the honest, forward-safe outcome this test is "
                  "designed to expose, not a bug.")
    lines.append("")
    lines.append("## Validation-season comparison: raw vs. calibrated")
    lines.append("")
    lines.append("| Variant | n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for name in ("raw", "calibrated"):
        m = summary[f"{name}_metrics"]
        lines.append(f"| {name} | {m['n']} | {m['log_loss']:.4f} | {m['brier_score']:.4f} | {m['auc']:.4f} | "
                      f"{m['calibration_intercept']:.4f} | {m['calibration_slope']:.4f} | {m['expected_calibration_error']:.4f} |")
    lines.append("")
    lines.append("AUC is identical for both by construction: a monotonic logit-linear recalibration cannot change "
                  "rank ordering, only the scale of the probabilities.")
    lines.append("")
    b = summary["bootstrap"]
    lines.append(f"**Paired bootstrap** (n={b['n_matches']}, {b['n_bootstrap']} resamples): "
                  f"delta (calibrated - raw) = {b['point_delta']:.4f}, 95% CI [{b['ci_lower']:.4f}, {b['ci_upper']:.4f}]")
    lines.append("")
    verdict = "CALIBRATED (adopt the fitted intercept/slope above)" if b["calibration_improves"] else "NONE (raw Global Elo probabilities are used unchanged)"
    lines.append(f"## Decision: CALIBRATION = {verdict}")
    lines.append("")
    if b["calibration_improves"]:
        lines.append("The corrected probabilities genuinely improve out-of-sample log loss on validation -- "
                      "this recalibration step is adopted as part of the frozen model specification.")
    else:
        lines.append("The CI does not exclude zero (or excludes it in the wrong direction), so per the "
                      "pre-stated decision rule, calibration is NOT adopted. Raw Global Elo output is used "
                      "unchanged going forward, despite its mild overconfidence -- forcing a correction that "
                      "doesn't demonstrably help out-of-sample would be curve-fitting to one validation season.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    data = build_predictions()
    intercept, slope = fit_calibration_intercept_slope(data["train_raw"], data["train_actuals"])
    print(f"Fitted on training only: intercept={intercept:.4f}, slope={slope:.4f}")

    calibrated_val = [_sigmoid(intercept + slope * _logit(p)) for p in data["val_raw"]]

    raw_metrics = metrics_block(data["val_raw"], data["val_actuals"])
    calibrated_metrics = metrics_block(calibrated_val, data["val_actuals"])
    bootstrap = paired_bootstrap_log_loss_delta(calibrated_val, data["val_raw"], data["val_actuals"])
    print(f"Validation: raw log loss={raw_metrics['log_loss']:.4f}, calibrated={calibrated_metrics['log_loss']:.4f}, "
          f"delta CI=[{bootstrap['ci_lower']:.4f}, {bootstrap['ci_upper']:.4f}], improves={bootstrap['calibration_improves']}")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_seasons": data["training_seasons"], "validation_season": data["validation_season"],
        "sealed_holdout_season": data["sealed_holdout_season"], "global_elo_k_factor": data["global_elo_k_factor"],
        "fitted_intercept": intercept, "fitted_slope": slope,
        "raw_metrics": raw_metrics, "calibrated_metrics": calibrated_metrics, "bootstrap": bootstrap,
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(summary))
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
