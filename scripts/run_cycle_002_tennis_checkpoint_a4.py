#!/usr/bin/env python3
"""Workstream A4, Cycle 2 tennis: baselines A (ranking-only), B (global
Elo) and C (surface Elo), evaluated strictly walk-forward.

Per the approved A4 sequence (research operator directive, 2026-09):
    A. ranking-only baseline
    B. global Elo, strict chronological/no-look-ahead updating
    C. surface-aware Elo, tested for incremental value over global Elo
    D. pre-registered incremental feature models (NOT in this script --
       see research/cycles/CYCLE_002_TENNIS/EXPLORATORY_ANALYSIS.md for
       the candidate features and TODO below)

Split (fixed by TML-file season label `_season`, not an arbitrary
calendar cut -- see research/cycles/CYCLE_002_TENNIS/DATA_QUALITY_REPORT.md
on why `_season` is the ground-truth partition already used throughout
this pipeline, not tourney_date):
    2021-2023  TRAINING   -- k_factor calibration and ranking-baseline fit
    2024       VALIDATION -- every metric in this report's output
    2025       SEALED HOLDOUT -- never loaded by this script at all (see
               load_matches's season filter and the assertion right after)

Elo ratings are simulated continuously across training+validation
(so 2024 matches see real pre-match ratings built up since 2021), but
k_factor is calibrated using ONLY the training-period log loss, and 2025
is excluded from the very first read of the CSV -- there is no path by
which this script can see 2025 data even by accident.

Every number this script produces is PREDICTIVE PERFORMANCE ONLY -- NO
BETTING EDGE ESTABLISHED. No price data of any kind is used or available
to this script; see reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md
for the separate, still-open search for a usable historical-odds source.

Retirements are included without special handling (a documented
simplification, not an oversight -- consistent with "robust baselines,
not a Kaggle competition"); walkovers were already excluded upstream by
Workstream A2's canonicalisation. Matches with missing ranking points for
either player are excluded from the ranking baseline (never imputed --
see tennis_ranking_baseline.py) but are still scored by both Elo models.

Outputs:
    research/cycles/CYCLE_002_TENNIS/A4_BASELINE_RESULTS.md
    data/interim/cycle_002_tennis_a4_predictions.csv
    data/interim/cycle_002_tennis_a4_metrics.json

Run:
    python scripts/run_cycle_002_tennis_checkpoint_a4.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.models.tennis_elo import (  # noqa: E402
    EloConfig,
    EloMatchInput,
    calibrate_k_factor,
    global_rating_key,
    run_elo_over_matches,
    surface_rating_key,
)
from prediction_markets_lab.models.tennis_ranking_baseline import (  # noqa: E402
    RankingBaselineMatchInput,
    fit_ranking_baseline,
    has_usable_ranking,
    predict_ranking_baseline,
)
from prediction_markets_lab.performance.binary_classification import (  # noqa: E402
    binary_auc,
    binary_brier_score,
    binary_calibration_bins,
    binary_log_loss,
    expected_calibration_error,
    fit_calibration_intercept_slope,
)

CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
REPORT_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "A4_BASELINE_RESULTS.md"
PREDICTIONS_PATH = REPO_ROOT / "data" / "interim" / "cycle_002_tennis_a4_predictions.csv"
METRICS_PATH = REPO_ROOT / "data" / "interim" / "cycle_002_tennis_a4_metrics.json"

TRAINING_SEASONS = [2021, 2022, 2023]
VALIDATION_SEASON = 2024
SEALED_HOLDOUT_SEASON = 2025  # never loaded by this script -- see load_matches

# Same coarse intra-tournament ordering used by Workstream A3's
# explore_cycle_002_tennis_match_data.py -- duplicated rather than
# imported since that file is a script, not a src/ module; see this
# project's convention (tennis_elo._expected_score) of duplicating a
# handful of lines rather than creating a script-to-script import.
ROUND_ORDER = {"RR": 0, "R128": 1, "R64": 2, "R32": 3, "R16": 4, "QF": 5, "SF": 6, "BR": 7, "F": 8}

# Small, predeclared k_factor grid -- "robust baselines, not a Kaggle
# competition" per the operating instructions. Calibrated independently
# for global vs surface Elo since there is no reason to assume the same
# value is optimal for both (surface-specific histories are shorter).
K_FACTOR_CANDIDATES = [16.0, 24.0, 32.0, 40.0, 48.0, 64.0]
BASE_ELO_CONFIG = EloConfig()  # literature-standard defaults; see tennis_elo.py docstring

N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 20260915  # today's date at the time this checkpoint was built, fixed for reproducibility
RANK_GAP_N_BUCKETS = 5


def load_matches(path: Path = CANONICAL_PATH) -> pd.DataFrame:
    """Load canonical matches, excluding the sealed holdout season at the
    very first read -- 2025 data is never in memory in this script."""
    df = pd.read_csv(path, parse_dates=["tourney_date"])
    df = df[~df["walkover"]].copy()  # already excluded upstream; defensive re-check
    seasons_to_load = set(TRAINING_SEASONS) | {VALIDATION_SEASON}
    df = df[df["_season"].isin(seasons_to_load)].copy()
    assert not (df["_season"] == SEALED_HOLDOUT_SEASON).any(), "sealed holdout season leaked into load_matches"

    df["_round_order"] = df["round"].map(ROUND_ORDER).fillna(-1)
    df = df.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    return df


def to_elo_input(row: pd.Series) -> EloMatchInput:
    return EloMatchInput(
        match_id=row["match_id"],
        match_date=row["tourney_date"].date(),
        surface=row["surface"] if pd.notna(row["surface"]) else "Unknown",
        player_a_id=row["player_a_id"],
        player_b_id=row["player_b_id"],
        outcome_a_won=int(row["outcome_a_won"]),
    )


def to_ranking_input(row: pd.Series) -> RankingBaselineMatchInput:
    a_points = row["player_a_rank_points"] if pd.notna(row["player_a_rank_points"]) else None
    b_points = row["player_b_rank_points"] if pd.notna(row["player_b_rank_points"]) else None
    return RankingBaselineMatchInput(
        match_id=row["match_id"],
        match_date=row["tourney_date"].date(),
        player_a_rank_points=a_points,
        player_b_rank_points=b_points,
        outcome_a_won=int(row["outcome_a_won"]),
    )


def run_elo_model(df: pd.DataFrame, rating_key_fn) -> tuple[dict, float]:
    """Calibrate k_factor on TRAINING rows only, then simulate ratings
    continuously across training+validation and return {match_id: p_a_win}
    for every row in df (both training and validation), plus the
    calibrated k_factor."""
    elo_inputs = [to_elo_input(row) for _, row in df.iterrows()]
    train_mask = df["_season"].isin(TRAINING_SEASONS).values
    train_inputs = [ei for ei, is_train in zip(elo_inputs, train_mask) if is_train]

    best_k = calibrate_k_factor(train_inputs, BASE_ELO_CONFIG, K_FACTOR_CANDIDATES, rating_key_fn)
    fold_config = EloConfig(initial_rating=BASE_ELO_CONFIG.initial_rating, k_factor=best_k)
    predictions = run_elo_over_matches(elo_inputs, fold_config, rating_key_fn)
    return {p.match_id: p.p_a_win for p in predictions}, best_k


def run_ranking_model(df: pd.DataFrame) -> dict:
    """Fit on usable-ranking TRAINING rows only, predict for every
    usable-ranking row in df (training and validation). Matches with an
    unranked player are simply absent from the returned dict -- callers
    must treat that as 'no ranking-baseline prediction', not impute one."""
    ranking_inputs = [to_ranking_input(row) for _, row in df.iterrows()]
    usable = [ri for ri in ranking_inputs if has_usable_ranking(ri)]
    train_mask = df["_season"].isin(TRAINING_SEASONS).values
    usable_ids = {ri.match_id for ri in usable}
    train_usable = [
        ri for ri, is_train in zip(ranking_inputs, train_mask)
        if is_train and ri.match_id in usable_ids
    ]
    model = fit_ranking_baseline(train_usable)
    preds = predict_ranking_baseline(model, usable)
    return {p.match_id: p.p_a_win for p in preds}


def _metrics_block(preds: list[float], actuals: list[int]) -> dict:
    bins = binary_calibration_bins(preds, actuals, n_bins=min(10, max(2, len(preds) // 30))) if len(preds) >= 20 else []
    intercept, slope = fit_calibration_intercept_slope(preds, actuals)
    return {
        "n": len(preds),
        "log_loss": binary_log_loss(preds, actuals),
        "brier_score": binary_brier_score(preds, actuals),
        "auc": binary_auc(preds, actuals) if len(set(actuals)) == 2 else None,
        "calibration_intercept": intercept,
        "calibration_slope": slope,
        "expected_calibration_error": expected_calibration_error(bins) if bins else None,
        "calibration_bins": [
            {
                "bin_index": b.bin_index, "n": b.n,
                "mean_predicted_probability": b.mean_predicted_probability,
                "observed_frequency": b.observed_frequency,
            }
            for b in bins
        ],
    }


def _subgroup_table(rows: pd.DataFrame, group_col: str, pred_col: str, actual_col: str = "outcome_a_won") -> list[dict]:
    out = []
    for level, group in rows.groupby(group_col, dropna=True, observed=True):
        preds = group[pred_col].tolist()
        actuals = group[actual_col].tolist()
        if len(preds) < 5 or len(set(actuals)) < 1:
            continue
        out.append({
            "level": str(level),
            "n": len(preds),
            "log_loss": binary_log_loss(preds, actuals),
            "brier_score": binary_brier_score(preds, actuals),
            "mean_predicted_probability": float(np.mean(preds)),
            "observed_frequency": float(np.mean(actuals)),
        })
    # An ordered Categorical (e.g. a qcut bucket, low-gap to high-gap) is
    # a natural reading order -- preserve it. Anything else (surface,
    # tourney level, ...) has no inherent order, so fall back to
    # largest-sample-first, which is at least a stable, readable default.
    col_dtype = rows[group_col].dtype
    if isinstance(col_dtype, pd.CategoricalDtype) and col_dtype.ordered:
        order = {str(c): i for i, c in enumerate(col_dtype.categories)}
        return sorted(out, key=lambda r: order.get(r["level"], len(order)))
    return sorted(out, key=lambda r: -r["n"])


def paired_bootstrap_log_loss_delta(
    preds_a: list[float], preds_b: list[float], actuals: list[int], n_bootstrap: int = N_BOOTSTRAP, seed: int = BOOTSTRAP_SEED
) -> dict:
    """Bootstrap CI for (mean log loss of A) - (mean log loss of B) on the
    SAME matches (paired -- both models scored on identical rows), per the
    operating instructions' request for paired bootstrap uncertainty
    between models. Negative delta means model A has lower (better) log
    loss than model B."""
    from prediction_markets_lab.performance.binary_classification import binary_log_loss_single

    n = len(actuals)
    per_match_a = np.array([binary_log_loss_single(p, a) for p, a in zip(preds_a, actuals)])
    per_match_b = np.array([binary_log_loss_single(p, a) for p, a in zip(preds_b, actuals)])
    point_delta = float(per_match_a.mean() - per_match_b.mean())

    rng = np.random.default_rng(seed)
    deltas = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        deltas[i] = per_match_a[idx].mean() - per_match_b[idx].mean()
    return {
        "n_matches": n,
        "n_bootstrap": n_bootstrap,
        "point_delta_log_loss_a_minus_b": point_delta,
        "ci_2_5_pct": float(np.percentile(deltas, 2.5)),
        "ci_97_5_pct": float(np.percentile(deltas, 97.5)),
        "interpretation": "negative delta = model A (first-listed) has lower/better log loss; "
                           "if the 95% CI excludes zero, the difference is unlikely to be noise "
                           "-- this is a predictive-performance comparison only, not evidence of a betting edge.",
    }


def render_report(summary: dict) -> str:
    lines = []
    lines.append("# Cycle 2 Tennis -- Workstream A4 Baseline Results (A, B, C)")
    lines.append("")
    lines.append(f"*Generated {summary['generated_at']}*")
    lines.append("")
    lines.append("**PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.** "
                  "No price/odds data of any kind is used anywhere in this report; "
                  "see reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md for the "
                  "separate, still-open search for a usable historical-odds source.")
    lines.append("")
    lines.append("**RESULT STATUS: FROZEN.** Per the research operator's explicit decision "
                  "after reviewing these numbers, model C (Surface Elo) is recorded as "
                  "**SURFACE ELO V1 -- NEGATIVE / DOES NOT PROMOTE** and is not modified "
                  "retrospectively to improve it -- doing so after seeing the result would "
                  "introduce researcher degrees of freedom. The likely explanation (too few "
                  "matches per player per surface diluting each surface-specific rating) is "
                  "a plausible HYPOTHESIS, not an established finding. A shrinkage/hierarchical "
                  "surface-rating model may be pursued later as a SEPARATE, newly "
                  "pre-registered specification, never as a repair of this one. Models A and B "
                  "are accepted as-is; Workstream A4 proceeds to step D using Global Elo (B) as "
                  "the primary odds-independent benchmark.")
    lines.append("")
    lines.append("## 1. Scope and split")
    lines.append("")
    lines.append(f"- Training/calibration seasons: {summary['training_seasons']} (n={summary['n_training']})")
    lines.append(f"- Validation season: {summary['validation_season']} (n={summary['n_validation']})")
    lines.append(f"- Sealed holdout season: {summary['sealed_holdout_season']} -- **never loaded by this script** "
                  "(excluded at the CSV read itself, plus an assertion immediately after)")
    lines.append("- Models: (A) ranking-only baseline, (B) global Elo, (C) surface Elo -- "
                  "independent standalone predictors, not blended")
    lines.append("- Retirements included without special handling (documented simplification). "
                  "Walkovers already excluded upstream by Workstream A2.")
    lines.append("- Ranking baseline excludes matches with an unranked player (never imputed); "
                  "both Elo models score every match.")
    lines.append("")
    lines.append("## 2. Headline validation-season metrics")
    lines.append("")
    lines.append("| Model | Coverage n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for name, m in summary["model_metrics"].items():
        auc = f"{m['auc']:.4f}" if m["auc"] is not None else "n/a"
        ece = f"{m['expected_calibration_error']:.4f}" if m["expected_calibration_error"] is not None else "n/a"
        lines.append(
            f"| {name} | {m['n']} | {m['log_loss']:.4f} | {m['brier_score']:.4f} | {auc} | "
            f"{m['calibration_intercept']:.4f} | {m['calibration_slope']:.4f} | {ece} |"
        )
    lines.append("")
    lines.append("A well-calibrated model has calibration intercept ~= 0 and slope ~= 1. "
                  "The naive floor for log loss is ln(2) ~= 0.6931 (always predicting 0.5).")
    lines.append("")
    lines.append("### Calibrated k_factor")
    lines.append("")
    lines.append(f"- Global Elo: k_factor = {summary['global_elo_k_factor']}")
    lines.append(f"- Surface Elo: k_factor = {summary['surface_elo_k_factor']}")
    lines.append(f"- Candidates searched: {K_FACTOR_CANDIDATES}")
    lines.append("")
    lines.append("## 3. Common-sample comparison (matches all three models can score)")
    lines.append("")
    lines.append("The ranking baseline only covers matches where both players are ranked, so "
                  "comparing models on their own full-coverage samples is not apples-to-apples. "
                  "This section restricts ALL THREE models to that common, ranking-usable subset.")
    lines.append("")
    lines.append("| Model | Common-sample n | Log loss | Brier |")
    lines.append("|---|---|---|---|")
    for name, m in summary["common_sample_metrics"].items():
        lines.append(f"| {name} | {m['n']} | {m['log_loss']:.4f} | {m['brier_score']:.4f} |")
    lines.append("")
    lines.append("## 4. Paired bootstrap uncertainty (common sample, log loss delta)")
    lines.append("")
    for comparison, res in summary["bootstrap_comparisons"].items():
        lines.append(f"**{comparison}** (n={res['n_matches']}, {res['n_bootstrap']} resamples): "
                      f"delta = {res['point_delta_log_loss_a_minus_b']:.4f}, "
                      f"95% CI [{res['ci_2_5_pct']:.4f}, {res['ci_97_5_pct']:.4f}]")
        lines.append("")
    lines.append("Negative delta means the first-named model has the lower (better) log loss. "
                  "A CI excluding zero means the gap is unlikely to be sampling noise -- this is "
                  "still a predictive-performance statement only, not a betting-edge claim.")
    lines.append("")
    lines.append("## 5. Subgroup diagnostics (global Elo, full validation coverage)")
    lines.append("")
    for group_name, table in summary["subgroups"].items():
        lines.append(f"### By {group_name}")
        lines.append("")
        lines.append("| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |")
        lines.append("|---|---|---|---|---|---|")
        for row in table:
            lines.append(
                f"| {row['level']} | {row['n']} | {row['log_loss']:.4f} | {row['brier_score']:.4f} | "
                f"{row['mean_predicted_probability']:.4f} | {row['observed_frequency']:.4f} |"
            )
        lines.append("")
    lines.append("## 6. What this does and does not show")
    lines.append("")
    lines.append("- This compares three PREDICTIVE models against each other on match outcomes. "
                  "None of it is compared to a market price, because no verified historical-odds "
                  "source is connected yet (see the odds-source audit doc). A model beating the "
                  "ranking baseline here says nothing about whether it would beat a bookmaker's line.")
    lines.append("- Not yet built (Workstream A4 step D, next): incremental feature models testing "
                  "recent form, surface-specific form, and congestion/rest as information ADDED "
                  "BEYOND these rating-based baselines, per the pre-registered candidates in "
                  "research/cycles/CYCLE_002_TENNIS/EXPLORATORY_ANALYSIS.md section 9.")
    lines.append("- No hyperparameter search beyond the small predeclared k_factor grid above -- "
                  "per the explicit instruction to build robust baselines, not optimise for their own sake.")
    lines.append("- 2025 is completely unexamined by this script. It remains a sealed holdout for "
                  "whatever model is eventually selected as the cycle's primary candidate.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    df = load_matches()
    print(f"Loaded {len(df)} matches across seasons {sorted(df['_season'].unique().tolist())} "
          f"(2025 excluded at load time).")

    train_df = df[df["_season"].isin(TRAINING_SEASONS)]
    val_df = df[df["_season"] == VALIDATION_SEASON]
    print(f"Training: {len(train_df)}  Validation: {len(val_df)}")

    global_preds, global_k = run_elo_model(df, global_rating_key)
    surface_preds, surface_k = run_elo_model(df, surface_rating_key)
    ranking_preds = run_ranking_model(df)
    print(f"Calibrated k_factor -- global: {global_k}, surface: {surface_k}")
    print(f"Ranking baseline covers {len(ranking_preds)} / {len(df)} total matches (usable ranking only).")

    val_ids = set(val_df["match_id"])
    val_lookup = val_df.set_index("match_id")

    def _validation_rows(pred_dict: dict) -> pd.DataFrame:
        ids = [mid for mid in pred_dict if mid in val_ids]
        rows = val_lookup.loc[ids].copy()
        rows["p_a_win"] = [pred_dict[mid] for mid in ids]
        return rows.reset_index()  # restore match_id as an ordinary column

    global_val = _validation_rows(global_preds)
    surface_val = _validation_rows(surface_preds)
    ranking_val = _validation_rows(ranking_preds)

    model_metrics = {
        "A. Ranking baseline": _metrics_block(ranking_val["p_a_win"].tolist(), ranking_val["outcome_a_won"].tolist()),
        "B. Global Elo": _metrics_block(global_val["p_a_win"].tolist(), global_val["outcome_a_won"].tolist()),
        "C. Surface Elo": _metrics_block(surface_val["p_a_win"].tolist(), surface_val["outcome_a_won"].tolist()),
    }

    common_ids = set(ranking_val["match_id"]) & set(global_val["match_id"]) & set(surface_val["match_id"])
    common_ranking = ranking_val[ranking_val["match_id"].isin(common_ids)].set_index("match_id")
    common_global = global_val[global_val["match_id"].isin(common_ids)].set_index("match_id")
    common_surface = surface_val[surface_val["match_id"].isin(common_ids)].set_index("match_id")
    ordered_ids = sorted(common_ids)
    common_actuals = [int(common_ranking.loc[mid, "outcome_a_won"]) for mid in ordered_ids]
    common_ranking_preds = [float(common_ranking.loc[mid, "p_a_win"]) for mid in ordered_ids]
    common_global_preds = [float(common_global.loc[mid, "p_a_win"]) for mid in ordered_ids]
    common_surface_preds = [float(common_surface.loc[mid, "p_a_win"]) for mid in ordered_ids]

    common_sample_metrics = {
        "A. Ranking baseline": {"n": len(ordered_ids), "log_loss": binary_log_loss(common_ranking_preds, common_actuals),
                                 "brier_score": binary_brier_score(common_ranking_preds, common_actuals)},
        "B. Global Elo": {"n": len(ordered_ids), "log_loss": binary_log_loss(common_global_preds, common_actuals),
                           "brier_score": binary_brier_score(common_global_preds, common_actuals)},
        "C. Surface Elo": {"n": len(ordered_ids), "log_loss": binary_log_loss(common_surface_preds, common_actuals),
                            "brier_score": binary_brier_score(common_surface_preds, common_actuals)},
    }

    bootstrap_comparisons = {
        "B. Global Elo vs A. Ranking baseline": paired_bootstrap_log_loss_delta(
            common_global_preds, common_ranking_preds, common_actuals),
        "C. Surface Elo vs B. Global Elo": paired_bootstrap_log_loss_delta(
            common_surface_preds, common_global_preds, common_actuals),
    }

    # Subgroup diagnostics on global Elo's full validation coverage.
    global_val = global_val.copy()
    usable_rank_mask = global_val["match_id"].isin(set(ranking_preds.keys()))
    rank_gap = pd.Series(np.nan, index=global_val.index)
    rank_gap[usable_rank_mask] = np.abs(
        np.log(global_val.loc[usable_rank_mask, "player_a_rank_points"])
        - np.log(global_val.loc[usable_rank_mask, "player_b_rank_points"])
    )
    global_val["_rank_gap_abs"] = rank_gap
    if usable_rank_mask.sum() >= RANK_GAP_N_BUCKETS * 5:
        # pd.qcut returns an ORDERED Categorical (low gap -> high gap);
        # reindex (not .loc-assign into a preallocated column) so that
        # ordering survives onto the full-length column with NaN for the
        # unranked rows -- _subgroup_table reads this ordering to present
        # the rank-gap subgroup smallest-to-largest instead of by count.
        bucket_values = pd.qcut(
            global_val.loc[usable_rank_mask, "_rank_gap_abs"], RANK_GAP_N_BUCKETS, duplicates="drop"
        )
        global_val["_rank_gap_bucket"] = bucket_values.reindex(global_val.index)

    subgroups = {
        "surface": _subgroup_table(global_val, "surface", "p_a_win"),
        "tourney_level": _subgroup_table(global_val, "tourney_level", "p_a_win"),
        "best_of": _subgroup_table(global_val, "best_of", "p_a_win"),
    }
    if "_rank_gap_bucket" in global_val.columns:
        subgroups["rank_gap (usable-ranking matches only)"] = _subgroup_table(
            global_val[usable_rank_mask], "_rank_gap_bucket", "p_a_win"
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_seasons": TRAINING_SEASONS,
        "validation_season": VALIDATION_SEASON,
        "sealed_holdout_season": SEALED_HOLDOUT_SEASON,
        "n_training": int(len(train_df)),
        "n_validation": int(len(val_df)),
        "global_elo_k_factor": global_k,
        "surface_elo_k_factor": surface_k,
        "model_metrics": model_metrics,
        "common_sample_metrics": common_sample_metrics,
        "bootstrap_comparisons": bootstrap_comparisons,
        "subgroups": subgroups,
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    pred_rows = []
    for mid in val_df["match_id"]:
        pred_rows.append({
            "match_id": mid,
            "season": VALIDATION_SEASON,
            "outcome_a_won": int(val_lookup.loc[mid, "outcome_a_won"]),
            "surface": val_lookup.loc[mid, "surface"],
            "ranking_baseline_p_a_win": ranking_preds.get(mid, ""),
            "global_elo_p_a_win": global_preds.get(mid, ""),
            "surface_elo_p_a_win": surface_preds.get(mid, ""),
        })
    pd.DataFrame(pred_rows).to_csv(PREDICTIONS_PATH, index=False)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(summary))

    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {PREDICTIONS_PATH}")
    print(f"Wrote {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
