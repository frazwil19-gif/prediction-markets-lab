#!/usr/bin/env python3
"""Workstream A4 step D, Cycle 2 tennis: pre-registered incremental
feature models.

Per the research operator's explicit A4 step D directive (approved after
reviewing A4 A-C, which is FROZEN -- see A4_BASELINE_RESULTS.md's "RESULT
STATUS: FROZEN" note; Surface Elo V1 is not touched or rescued here):

    Does any of three pre-registered candidate information families add
    INCREMENTAL predictive information beyond Global Elo (the accepted
    primary odds-independent benchmark)?

        1. recent form beyond Global Elo
        2. surface-specific form beyond Global Elo
        3. congestion/rest/fatigue beyond Global Elo

Method: for each family, fit a NESTED pair of logistic regression models on
the SAME rows (an "Elo-only" model with one feature -- the pre-match global
Elo rating difference -- and an "Elo+feature" model adding the candidate
feature(s)), trained on 2021-2023 only, and compare their 2024-validation
log loss with a PAIRED bootstrap confidence interval. Promotion requires the
CI on (augmented - baseline) log loss to lie entirely below zero -- not a
correctly-signed coefficient, not a favourable raw win rate. An explicit
multiple-testing policy (Bonferroni, m=3 families) widens each CI to the
group's family-wise 95% level, per the explicit instruction that testing
three candidate families at once needs a stated correction, not three
independent 95% claims.

2025 is never loaded: this script reuses run_cycle_002_tennis_checkpoint_a4
.load_matches(), which excludes the sealed holdout season at the very first
CSV read and asserts it absent -- re-asserted again here for defence in
depth. Calibration (raw vs. a simple forward-safe recalibration) is
deliberately NOT investigated in this script -- the operator's instruction
is to do that only AFTER step D's model selection is settled, to avoid
tuning calibration to chase a better headline log loss.

Feature engineering (recent form, surface form, rest days, congestion) is
NOT reimplemented here -- it is reused directly from Workstream A3's
scripts/explore_cycle_002_tennis_match_data.py (already hand-verified
no-look-ahead by tests/unit/test_cycle_002_tennis_exploratory_analysis.py),
loaded dynamically the same way run_stage_3b_checkpoint2_elo.py loads
verify_frozen_data_hashes.py. Duplicating already-tested leakage-sensitive
logic would be a real correctness risk for no benefit.

Every number here is PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE
ESTABLISHED. No price/odds data is used.

Outputs:
    research/cycles/CYCLE_002_TENNIS/A4_STEP_D_INCREMENTAL_FEATURES.md
    data/interim/cycle_002_tennis_a4_step_d_metrics.json

Run:
    python scripts/run_cycle_002_tennis_checkpoint_a4_step_d.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.models.logistic_regression import fit_logistic_regression  # noqa: E402
from prediction_markets_lab.models.tennis_elo import (  # noqa: E402
    EloConfig,
    calibrate_k_factor,
    global_rating_key,
    run_elo_over_matches,
)
from prediction_markets_lab.performance.binary_classification import (  # noqa: E402
    binary_log_loss_single,
)

REPORT_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "A4_STEP_D_INCREMENTAL_FEATURES.md"
METRICS_PATH = REPO_ROOT / "data" / "interim" / "cycle_002_tennis_a4_step_d_metrics.json"

N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 20260915
FAMILYWISE_ALPHA = 0.05

# The three pre-registered candidate families (research operator directive).
# congestion/rest is treated as ONE family (both features describe the same
# underlying "fatigue/scheduling" hypothesis), matching how it was posed --
# not split into two families to inflate the count tested.
FEATURE_FAMILIES = {
    "1. Recent form beyond Global Elo": ["rolling_win_pct_diff_a_minus_b"],
    "2. Surface-specific form beyond Global Elo": ["rolling_win_pct_surface_diff_a_minus_b"],
    "3. Congestion/rest beyond Global Elo": ["rest_diff_a_minus_b", "congestion_diff_a_minus_b"],
}
N_FAMILIES = len(FEATURE_FAMILIES)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bonferroni_ci_percentiles(n_comparisons: int, familywise_alpha: float = FAMILYWISE_ALPHA) -> tuple[float, float]:
    """Two-sided percentile bounds for a Bonferroni-corrected CI: spends
    familywise_alpha evenly across n_comparisons independent tests so the
    FAMILY of CIs (not each one individually) holds at the stated
    confidence level. E.g. n_comparisons=3, familywise_alpha=0.05 ->
    per-comparison alpha=0.016667 -> (0.8333, 99.1667) percentiles.

    Raises:
        ValueError: if n_comparisons < 1 or familywise_alpha not in (0, 1).
    """
    if n_comparisons < 1:
        raise ValueError(f"n_comparisons must be >= 1, got {n_comparisons}")
    if not (0.0 < familywise_alpha < 1.0):
        raise ValueError(f"familywise_alpha must be in (0, 1), got {familywise_alpha}")
    per_comparison_alpha = familywise_alpha / n_comparisons
    lower = 100.0 * (per_comparison_alpha / 2.0)
    upper = 100.0 * (1.0 - per_comparison_alpha / 2.0)
    return lower, upper


def paired_bootstrap_log_loss_delta_corrected(
    preds_augmented: list[float], preds_baseline: list[float], actuals: list[int],
    n_comparisons: int, n_bootstrap: int = N_BOOTSTRAP, seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Paired bootstrap CI for (augmented model log loss) - (baseline model
    log loss) on identical rows, at a Bonferroni-corrected confidence level
    for n_comparisons simultaneous tests. Negative delta means the
    augmented model has lower (better) log loss."""
    n = len(actuals)
    per_match_aug = np.array([binary_log_loss_single(p, a) for p, a in zip(preds_augmented, actuals)])
    per_match_base = np.array([binary_log_loss_single(p, a) for p, a in zip(preds_baseline, actuals)])
    point_delta = float(per_match_aug.mean() - per_match_base.mean())

    rng = np.random.default_rng(seed)
    deltas = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        deltas[i] = per_match_aug[idx].mean() - per_match_base[idx].mean()

    lower_pct, upper_pct = bonferroni_ci_percentiles(n_comparisons)
    ci_lower = float(np.percentile(deltas, lower_pct))
    ci_upper = float(np.percentile(deltas, upper_pct))
    return {
        "n_matches": n,
        "n_bootstrap": n_bootstrap,
        "n_comparisons_corrected_for": n_comparisons,
        "ci_percentile_bounds": [lower_pct, upper_pct],
        "point_delta_log_loss_augmented_minus_baseline": point_delta,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "promoted": bool(ci_upper < 0.0),
    }


def build_dataset() -> tuple[pd.DataFrame, dict]:
    """Load canonical matches (2025 sealed, never loaded -- inherited from
    run_cycle_002_tennis_checkpoint_a4.load_matches, re-asserted below),
    compute the Global Elo rating-difference feature, and merge in A3's
    already-tested no-look-ahead rolling/congestion features plus this
    script's own rest/congestion DIFF columns (A3's merge_features_into_
    matches doesn't compute those diffs itself -- it only needed the raw
    per-player values for its own EDA)."""
    a4 = _load_module(REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py", "run_cycle_002_tennis_checkpoint_a4")
    a3 = _load_module(REPO_ROOT / "scripts" / "explore_cycle_002_tennis_match_data.py", "explore_cycle_002_tennis_match_data")

    df = a4.load_matches()
    assert not (df["_season"] == a4.SEALED_HOLDOUT_SEASON).any(), "sealed holdout season leaked into build_dataset"
    df = df.reset_index(drop=True)
    df["_match_seq"] = np.arange(len(df))

    elo_inputs = [a4.to_elo_input(row) for _, row in df.iterrows()]
    train_mask = df["_season"].isin(a4.TRAINING_SEASONS).values
    train_elo_inputs = [ei for ei, is_train in zip(elo_inputs, train_mask) if is_train]
    best_k = calibrate_k_factor(train_elo_inputs, EloConfig(), a4.K_FACTOR_CANDIDATES, global_rating_key)
    elo_predictions = run_elo_over_matches(elo_inputs, EloConfig(k_factor=best_k), global_rating_key)
    elo_by_match = {p.match_id: p for p in elo_predictions}
    df["_elo_rating_diff"] = [
        elo_by_match[mid].pre_match_a_rating - elo_by_match[mid].pre_match_b_rating for mid in df["match_id"]
    ]

    long_df = a3.build_long_format(df)
    long_df = a3.add_no_lookahead_rolling_features(long_df)
    merged = a3.merge_features_into_matches(df, long_df)

    merged["rest_diff_a_minus_b"] = merged["player_a_days_since_last_match"] - merged["player_b_days_since_last_match"]
    merged["congestion_diff_a_minus_b"] = merged["player_a_matches_last_14_days"] - merged["player_b_matches_last_14_days"]

    return merged, {"global_elo_k_factor": best_k, "training_seasons": a4.TRAINING_SEASONS,
                     "validation_season": a4.VALIDATION_SEASON, "sealed_holdout_season": a4.SEALED_HOLDOUT_SEASON}


def _fit_and_predict(train_rows: pd.DataFrame, val_rows: pd.DataFrame, feature_cols: list[str]):
    X_train = train_rows[feature_cols].to_numpy(dtype=float)
    y_train = train_rows["outcome_a_won"].tolist()
    model = fit_logistic_regression(X_train, y_train, feature_cols)
    X_val = val_rows[feature_cols].to_numpy(dtype=float)
    preds = model.predict_proba(X_val).tolist()
    return model, preds


def _stability_table(val_rows: pd.DataFrame, group_col: str, baseline_preds: list, augmented_preds: list) -> list[dict]:
    tmp = val_rows.copy()
    tmp["_baseline_pred"] = baseline_preds
    tmp["_augmented_pred"] = augmented_preds
    out = []
    for level, group in tmp.groupby(group_col, dropna=True, observed=True):
        if len(group) < 30:
            continue
        actuals = group["outcome_a_won"].tolist()
        base_ll = np.mean([binary_log_loss_single(p, a) for p, a in zip(group["_baseline_pred"], actuals)])
        aug_ll = np.mean([binary_log_loss_single(p, a) for p, a in zip(group["_augmented_pred"], actuals)])
        out.append({"level": str(level), "n": len(group), "baseline_log_loss": float(base_ll),
                    "augmented_log_loss": float(aug_ll), "delta": float(aug_ll - base_ll)})
    return sorted(out, key=lambda r: -r["n"])


def evaluate_family(merged: pd.DataFrame, feature_cols: list[str], training_seasons: list[int], validation_season: int) -> dict:
    usable = merged[feature_cols].notna().all(axis=1) & merged["_elo_rating_diff"].notna()
    usable_df = merged[usable]
    train_rows = usable_df[usable_df["_season"].isin(training_seasons)]
    val_rows = usable_df[usable_df["_season"] == validation_season]

    baseline_cols = ["_elo_rating_diff"]
    augmented_cols = ["_elo_rating_diff"] + feature_cols

    _, baseline_preds = _fit_and_predict(train_rows, val_rows, baseline_cols)
    augmented_model, augmented_preds = _fit_and_predict(train_rows, val_rows, augmented_cols)

    actuals = val_rows["outcome_a_won"].tolist()
    bootstrap = paired_bootstrap_log_loss_delta_corrected(augmented_preds, baseline_preds, actuals, N_FAMILIES)

    # Stability: split the single validation season in half chronologically
    # (season/tourney-level splits aren't meaningful with only one
    # validation season -- see module docstring), plus by surface and
    # best_of, wherever a group has enough rows to be informative.
    val_rows_sorted = val_rows.sort_values("tourney_date")
    midpoint = len(val_rows_sorted) // 2
    half_labels = pd.Series(["first_half_2024"] * midpoint + ["second_half_2024"] * (len(val_rows_sorted) - midpoint),
                             index=val_rows_sorted.index)
    val_rows_for_stability = val_rows.copy()
    val_rows_for_stability["_half"] = half_labels.reindex(val_rows_for_stability.index)

    return {
        "feature_columns": feature_cols,
        "n_training": int(len(train_rows)),
        "n_validation": int(len(val_rows)),
        "coefficient_on_new_feature(s)": dict(zip(feature_cols, augmented_model.coefficients[1:])),
        "baseline_log_loss": float(np.mean([binary_log_loss_single(p, a) for p, a in zip(baseline_preds, actuals)])),
        "augmented_log_loss": float(np.mean([binary_log_loss_single(p, a) for p, a in zip(augmented_preds, actuals)])),
        "bootstrap": bootstrap,
        "stability_by_half_of_2024": _stability_table(val_rows_for_stability, "_half", baseline_preds, augmented_preds),
        "stability_by_surface": _stability_table(val_rows, "surface", baseline_preds, augmented_preds),
        "stability_by_best_of": _stability_table(val_rows, "best_of", baseline_preds, augmented_preds),
    }


def render_report(summary: dict) -> str:
    lines = []
    lines.append("# Cycle 2 Tennis -- Workstream A4 Step D: Incremental Feature Models")
    lines.append("")
    lines.append(f"*Generated {summary['generated_at']}*")
    lines.append("")
    lines.append("**PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.** No price/odds data of any kind is used. "
                  "A4 baselines A-C are FROZEN (see A4_BASELINE_RESULTS.md) and not modified here; "
                  "Global Elo is the accepted primary odds-independent benchmark every feature below is tested against.")
    lines.append("")
    lines.append(f"- Training/calibration seasons: {summary['training_seasons']}")
    lines.append(f"- Validation season: {summary['validation_season']}")
    lines.append(f"- Sealed holdout season: {summary['sealed_holdout_season']} -- **never loaded by this script**")
    lines.append(f"- Global Elo k_factor (recalibrated identically to A4): {summary['global_elo_k_factor']}")
    lines.append(f"- Multiple-testing policy: Bonferroni correction across {N_FAMILIES} pre-registered families -- "
                  f"each CI below is reported at the {100 - FAMILYWISE_ALPHA/N_FAMILIES*100:.4f}% level "
                  f"(per-comparison alpha = {FAMILYWISE_ALPHA}/{N_FAMILIES}), not a naive 95%, "
                  "so that the FAMILY of three tests holds at 95% overall.")
    lines.append("- Promotion rule: a feature is promoted only if its bootstrap CI for "
                  "(Elo+feature log loss - Elo-only log loss) lies ENTIRELY below zero at the corrected level above. "
                  "A correctly-signed coefficient or a favourable raw win-rate difference is not sufficient.")
    lines.append("")
    lines.append("## Results by family")
    lines.append("")
    for name, res in summary["families"].items():
        b = res["bootstrap"]
        verdict = "**PROMOTED**" if b["promoted"] else "NOT PROMOTED (null or negative result)"
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"Feature column(s): `{', '.join(res['feature_columns'])}` -- coverage n_train={res['n_training']}, n_validation={res['n_validation']}")
        lines.append("")
        lines.append(f"- Elo-only log loss: {res['baseline_log_loss']:.4f}")
        lines.append(f"- Elo+feature log loss: {res['augmented_log_loss']:.4f}")
        lines.append(f"- Delta (augmented - baseline): {b['point_delta_log_loss_augmented_minus_baseline']:.4f}, "
                      f"Bonferroni-corrected {b['ci_percentile_bounds'][1]-b['ci_percentile_bounds'][0]:.2f}% CI "
                      f"[{b['ci_lower']:.4f}, {b['ci_upper']:.4f}]")
        lines.append(f"- Fitted coefficient(s) on new feature(s): "
                      f"{ {k: round(v, 6) for k, v in res['coefficient_on_new_feature(s)'].items()} }")
        lines.append(f"- **Verdict: {verdict}**")
        lines.append("")
        lines.append("Stability (2024 first vs second half):")
        lines.append("")
        lines.append("| Half | n | Baseline log loss | Augmented log loss | Delta |")
        lines.append("|---|---|---|---|---|")
        for row in res["stability_by_half_of_2024"]:
            lines.append(f"| {row['level']} | {row['n']} | {row['baseline_log_loss']:.4f} | {row['augmented_log_loss']:.4f} | {row['delta']:.4f} |")
        lines.append("")
        if res["stability_by_surface"]:
            lines.append("Stability by surface:")
            lines.append("")
            lines.append("| Surface | n | Baseline log loss | Augmented log loss | Delta |")
            lines.append("|---|---|---|---|---|")
            for row in res["stability_by_surface"]:
                lines.append(f"| {row['level']} | {row['n']} | {row['baseline_log_loss']:.4f} | {row['augmented_log_loss']:.4f} | {row['delta']:.4f} |")
            lines.append("")
        if res["stability_by_best_of"]:
            lines.append("Stability by best-of format:")
            lines.append("")
            lines.append("| Best of | n | Baseline log loss | Augmented log loss | Delta |")
            lines.append("|---|---|---|---|---|")
            for row in res["stability_by_best_of"]:
                lines.append(f"| {row['level']} | {row['n']} | {row['baseline_log_loss']:.4f} | {row['augmented_log_loss']:.4f} | {row['delta']:.4f} |")
            lines.append("")

    promoted = [name for name, res in summary["families"].items() if res["bootstrap"]["promoted"]]
    lines.append("## Summary and next candidate model")
    lines.append("")
    if promoted:
        lines.append(f"Promoted feature families: {promoted}. A combined odds-independent candidate model "
                      "(Global Elo + all promoted features together) is the natural next step, evaluated the "
                      "same way (paired bootstrap vs. Global Elo alone) before it is treated as final.")
    else:
        lines.append("No feature family was promoted at the Bonferroni-corrected level. This is reported as a "
                      "clean null result, per the standing 'a clean null result is acceptable' directive -- it is "
                      "not reframed as a near-miss or retried with a looser threshold. Global Elo alone remains "
                      "the cycle's odds-independent candidate model pending any newly pre-registered feature.")
    lines.append("")
    lines.append("Calibration (raw vs. a simple forward-safe recalibration) has deliberately not been investigated "
                  "yet -- per the operator's instruction, that follows model selection, not before it, to avoid "
                  "tuning calibration to chase a better headline log loss.")
    lines.append("")
    lines.append("2025 remains completely sealed and unexamined by this script.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    merged, meta = build_dataset()
    print(f"Dataset built: {len(merged)} matches, global Elo k_factor={meta['global_elo_k_factor']}")

    families = {}
    for name, feature_cols in FEATURE_FAMILIES.items():
        print(f"Evaluating: {name} ({feature_cols})")
        families[name] = evaluate_family(merged, feature_cols, meta["training_seasons"], meta["validation_season"])
        b = families[name]["bootstrap"]
        print(f"  delta={b['point_delta_log_loss_augmented_minus_baseline']:.4f} "
              f"CI=[{b['ci_lower']:.4f}, {b['ci_upper']:.4f}] promoted={b['promoted']}")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_seasons": meta["training_seasons"],
        "validation_season": meta["validation_season"],
        "sealed_holdout_season": meta["sealed_holdout_season"],
        "global_elo_k_factor": meta["global_elo_k_factor"],
        "families": families,
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
