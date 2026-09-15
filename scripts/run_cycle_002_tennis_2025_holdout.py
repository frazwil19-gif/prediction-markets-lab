#!/usr/bin/env python3
"""TENNIS CYCLE 1 -- the one-time 2025 sealed-holdout evaluation.

This is the ONLY script in this repository permitted to load season 2025
of the canonical tennis dataset. It re-runs EXACTLY the frozen
specification in
research/cycles/CYCLE_002_TENNIS/TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md
(Global Elo, k_factor=32.0, no additional features, no calibration)
against 2025, and applies the frozen, mechanical PASS/PARTIAL/FAIL rule
(`classify_holdout_result` in
src/prediction_markets_lab/research/holdout_verdict.py) to the result.
Nobody reads the numbers and picks a verdict by eye.

Before running this script, run
scripts/run_cycle_002_tennis_2025_holdout_seal_check.py and confirm it
reports "All checks OK." This script does not call the seal check itself
(the seal check runs the full test suite, which would make every run of
this script slow and would make "run the tests" and "open the holdout"
the same irreversible action) -- it is a separate, deliberate step per
the freeze's process.

Per the freeze's Process section, running this script IS "opening 2025."
It is designed to be run exactly once: if
TENNIS_CYCLE_1_2025_HOLDOUT_REPORT.md already exists, this script refuses
to overwrite it unless --allow-rerun is passed explicitly, so a second run
cannot silently happen by accident (for example, by re-running this
command out of habit after a small unrelated code change elsewhere).

Model spec, hyperparameters, feature set, and calibration are NOT
re-decided here -- they are read from the frozen constants below, which
mirror the freeze document exactly. K_FACTOR is recalibrated on the
SAME training-only (2021-2023) rows as before (unaffected by whether 2025
is also loaded, since calibration only ever sees rows whose _season is in
TRAINING_SEASONS) purely as a consistency check that it still equals the
frozen value of 32.0 -- it is not being re-tuned against 2025.

Outputs:
    research/cycles/CYCLE_002_TENNIS/TENNIS_CYCLE_1_2025_HOLDOUT_REPORT.md
    data/interim/cycle_002_tennis_2025_holdout_predictions.csv
    data/interim/cycle_002_tennis_2025_holdout_metrics.json

Run:
    python scripts/run_cycle_002_tennis_2025_holdout_seal_check.py   # first, must pass
    python scripts/run_cycle_002_tennis_2025_holdout.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.research.holdout_verdict import (  # noqa: E402
    HoldoutVerdictInput,
    classify_holdout_result,
)

REPORT_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "TENNIS_CYCLE_1_2025_HOLDOUT_REPORT.md"
PREDICTIONS_PATH = REPO_ROOT / "data" / "interim" / "cycle_002_tennis_2025_holdout_predictions.csv"
METRICS_PATH = REPO_ROOT / "data" / "interim" / "cycle_002_tennis_2025_holdout_metrics.json"

FROZEN_K_FACTOR = 32.0  # from TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md section 3


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_matches_including_holdout(a4, path: Path | None = None) -> pd.DataFrame:
    """The ONE loader in this repo that includes season 2025.

    Deliberately does NOT reuse a4.load_matches() -- that function's
    entire job is to make 2025 unreachable, and it is left completely
    untouched so every other script's guarantee still holds. This
    function mirrors its logic exactly, minus the 2025 exclusion.
    """
    csv_path = path if path is not None else a4.CANONICAL_PATH
    seasons_to_load = set(a4.TRAINING_SEASONS) | {a4.VALIDATION_SEASON, a4.SEALED_HOLDOUT_SEASON}
    df = pd.read_csv(csv_path, parse_dates=["tourney_date"])
    df = df[~df["walkover"]].copy()
    df = df[df["_season"].isin(seasons_to_load)].copy()
    df["_round_order"] = df["round"].map(a4.ROUND_ORDER).fillna(-1)
    df = df.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    return df


def build_rank_gap_bucket(rows: pd.DataFrame, ranking_pred_ids: set, n_buckets: int) -> pd.DataFrame:
    """Attach an ordered rank-gap-decile bucket column, mirroring A4's
    construction (see run_cycle_002_tennis_checkpoint_a4.main) exactly,
    factored out here so it can be unit-tested against synthetic data."""
    rows = rows.copy()
    usable_mask = rows["match_id"].isin(ranking_pred_ids)
    rank_gap = pd.Series(np.nan, index=rows.index)
    rank_gap[usable_mask] = np.abs(
        np.log(rows.loc[usable_mask, "player_a_rank_points"])
        - np.log(rows.loc[usable_mask, "player_b_rank_points"])
    )
    rows["_rank_gap_abs"] = rank_gap
    rows["_usable_rank_mask"] = usable_mask
    if usable_mask.sum() >= n_buckets * 5:
        bucket_values = pd.qcut(rows.loc[usable_mask, "_rank_gap_abs"], n_buckets, duplicates="drop")
        rows["_rank_gap_bucket"] = bucket_values.reindex(rows.index)
    return rows


def build_common_sample(global_preds: dict, ranking_preds: dict, holdout_lookup: pd.DataFrame) -> pd.DataFrame:
    """Matches in the holdout season BOTH models can score, sorted by
    match_id for a deterministic pairing order in the bootstrap."""
    common_ids = sorted(set(global_preds) & set(ranking_preds) & set(holdout_lookup.index))
    rows = holdout_lookup.loc[common_ids].copy()
    rows["global_elo_p_a_win"] = [global_preds[mid] for mid in common_ids]
    rows["ranking_baseline_p_a_win"] = [ranking_preds[mid] for mid in common_ids]
    return rows.reset_index()


def render_report(summary: dict) -> str:
    lines = []
    lines.append("# Tennis Cycle 1 -- 2025 Sealed Holdout Report")
    lines.append("")
    lines.append(f"*Generated {summary['generated_at']}*")
    lines.append("")
    lines.append("**This is the ONE-TIME evaluation described in "
                  "TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md.** Run exactly once, against the "
                  "frozen specification, with the verdict below produced mechanically by "
                  "`classify_holdout_result` -- not read off by eye. No retrying, "
                  "threshold-loosening, or silent model change followed seeing these numbers.")
    lines.append("")
    lines.append(f"## 0. Seal and scope")
    lines.append("")
    lines.append(f"- Frozen model: Global Elo, k_factor={summary['k_factor']} "
                  f"(re-derived from training-only data as a consistency check -- matches the "
                  f"frozen value of {FROZEN_K_FACTOR}: {summary['k_factor'] == FROZEN_K_FACTOR})")
    lines.append(f"- Training/calibration seasons: {summary['training_seasons']}")
    lines.append(f"- Validation season (already reported elsewhere): {summary['validation_season']}")
    lines.append(f"- Sealed holdout season (evaluated here, for the first time): {summary['holdout_season']}")
    lines.append(f"- Holdout coverage: N={summary['n_holdout_total']} total matches in 2025; "
                  f"Global Elo scores {summary['global_elo']['n']} (full coverage -- Elo scores "
                  f"every match); ranking baseline scores {summary['ranking_baseline']['n']} "
                  f"(usable-ranking matches only); common sample for the primary comparison: "
                  f"N={summary['bootstrap']['n_matches']}.")
    lines.append("")
    lines.append("## 1. Global Elo -- 2025 metrics (full coverage)")
    lines.append("")
    m = summary["global_elo"]
    lines.append("| n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |")
    lines.append("|---|---|---|---|---|---|---|")
    ece = f"{m['expected_calibration_error']:.4f}" if m["expected_calibration_error"] is not None else "n/a"
    lines.append(
        f"| {m['n']} | {m['log_loss']:.4f} | {m['brier_score']:.4f} | {m['auc']:.4f} | "
        f"{m['calibration_intercept']:.4f} | {m['calibration_slope']:.4f} | {ece} |"
    )
    lines.append("")
    lines.append("## 2. Ranking baseline -- 2025 metrics (usable-ranking matches only)")
    lines.append("")
    m = summary["ranking_baseline"]
    lines.append("| n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |")
    lines.append("|---|---|---|---|---|---|---|")
    auc = f"{m['auc']:.4f}" if m["auc"] is not None else "n/a"
    ece = f"{m['expected_calibration_error']:.4f}" if m["expected_calibration_error"] is not None else "n/a"
    lines.append(
        f"| {m['n']} | {m['log_loss']:.4f} | {m['brier_score']:.4f} | {auc} | "
        f"{m['calibration_intercept']:.4f} | {m['calibration_slope']:.4f} | {ece} |"
    )
    lines.append("")
    lines.append("## 3. Primary comparison (common sample, paired bootstrap)")
    lines.append("")
    b = summary["bootstrap"]
    lines.append(f"delta (Global Elo log loss - ranking baseline log loss) = "
                  f"{b['point_delta_log_loss_a_minus_b']:.4f}, 95% CI "
                  f"[{b['ci_2_5_pct']:.4f}, {b['ci_97_5_pct']:.4f}] "
                  f"(n={b['n_matches']}, {b['n_bootstrap']} resamples, seed={summary['bootstrap_seed']})")
    lines.append("")
    lines.append("Negative delta means Global Elo has the lower (better) log loss. A CI "
                  "excluding zero means the gap is unlikely to be sampling noise -- this is "
                  "still a predictive-performance statement only, not a betting-edge claim "
                  "(see section 6).")
    lines.append("")
    lines.append("## 4. Mechanical verdict")
    lines.append("")
    v = summary["verdict"]
    lines.append(f"# VERDICT: {v['verdict']}")
    lines.append("")
    lines.append(f"Reason: {v['reason']}")
    lines.append("")
    lines.append("This verdict was produced by `classify_holdout_result` applied to the "
                  "numbers in sections 1-3 above, per the frozen, mutually exclusive rule in "
                  "TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md section 9. It was not chosen by "
                  "reading the numbers and picking the closest-sounding label.")
    lines.append("")
    lines.append("## 5. Subgroup diagnostics (Global Elo, full 2025 coverage) -- DIAGNOSTIC ONLY")
    lines.append("")
    lines.append("These were pre-registered as reporting-only in the freeze (section 6). Per "
                  "the freeze's process (section 11), an interesting pattern here is recorded "
                  "as a FUTURE HYPOTHESIS -- NOT VALIDATED and does NOT change the verdict above.")
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
    lines.append("## 6. What this result does and does not establish")
    lines.append("")
    lines.append("This holdout tests only whether Global Elo's PREDICTIVE performance "
                  "generalises out of sample to a period never touched during model "
                  "selection. It does NOT establish a betting edge, positive EV, market "
                  "outperformance, CLV, or tradeability, whatever the verdict above is -- "
                  "that requires historical market prices (Workstream B) and a full "
                  "EV/CLV/liquidity/cost analysis on top of predictive skill.")
    lines.append("")
    lines.append("## 7. Next step, per the freeze's process")
    lines.append("")
    next_step = {
        "PASS": "Proceed to market-aware research: Global Elo probabilities vs. historical "
                "Betfair Match Odds prices, once Workstream B's data access exists. Do not "
                "paper trade or live bet on this result alone.",
        "PARTIAL": "Do not modify the model. Report why the evidence is inconclusive and "
                   "identify the cleanest genuinely untouched additional validation route "
                   "without using 2025 for development.",
        "FAIL": "Close Tennis Cycle 1 honestly as a failed predictive experiment. Do not "
                "rescue it using 2025. Any new Elo specification, surface shrinkage, "
                "additional features, hyperparameters or calibration is Tennis Cycle 2, "
                "separately pre-registered.",
    }[v["verdict"]]
    lines.append(next_step)
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-rerun", action="store_true",
                         help="Explicitly permit overwriting an existing holdout report. "
                              "This cycle's evaluation is meant to happen exactly once -- "
                              "use this only to fix a genuine bug in THIS script's reporting "
                              "code, never to try a different model spec.")
    args = parser.parse_args(argv)

    if REPORT_PATH.exists() and not args.allow_rerun:
        print(f"STOP: {REPORT_PATH} already exists. Tennis Cycle 1's 2025 holdout is a "
              "one-time evaluation; re-running it is exactly what the freeze forbids. "
              "Pass --allow-rerun only if you are fixing a bug in this script's own "
              "reporting code, never to change the model spec or try again for a better result.")
        return 1

    a4 = _load_module(REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py",
                       "run_cycle_002_tennis_checkpoint_a4")

    df = load_matches_including_holdout(a4)
    holdout_df = df[df["_season"] == a4.SEALED_HOLDOUT_SEASON].copy()
    print(f"Loaded {len(df)} matches across seasons {sorted(df['_season'].unique().tolist())} "
          f"-- 2025 holdout n={len(holdout_df)}.")

    global_preds, global_k = a4.run_elo_model(df, a4.global_rating_key)
    ranking_preds = a4.run_ranking_model(df)
    print(f"Re-derived global Elo k_factor = {global_k} (frozen value: {FROZEN_K_FACTOR})")
    if global_k != FROZEN_K_FACTOR:
        print(f"STOP: re-derived k_factor {global_k} does not match the frozen value "
              f"{FROZEN_K_FACTOR} -- training data may have changed since the freeze. "
              "Do not proceed.")
        return 1

    holdout_ids = set(holdout_df["match_id"])
    holdout_lookup = holdout_df.set_index("match_id")

    global_holdout_ids = sorted(set(global_preds) & holdout_ids)
    global_holdout_preds = [global_preds[mid] for mid in global_holdout_ids]
    global_holdout_actuals = [int(holdout_lookup.loc[mid, "outcome_a_won"]) for mid in global_holdout_ids]
    global_metrics = a4._metrics_block(global_holdout_preds, global_holdout_actuals)

    ranking_holdout_ids = sorted(set(ranking_preds) & holdout_ids)
    ranking_holdout_preds = [ranking_preds[mid] for mid in ranking_holdout_ids]
    ranking_holdout_actuals = [int(holdout_lookup.loc[mid, "outcome_a_won"]) for mid in ranking_holdout_ids]
    ranking_metrics = a4._metrics_block(ranking_holdout_preds, ranking_holdout_actuals)

    common = build_common_sample(global_preds, ranking_preds, holdout_lookup)
    bootstrap = a4.paired_bootstrap_log_loss_delta(
        common["global_elo_p_a_win"].tolist(),
        common["ranking_baseline_p_a_win"].tolist(),
        common["outcome_a_won"].tolist(),
    )

    evidence = HoldoutVerdictInput(
        ci_lower=bootstrap["ci_2_5_pct"],
        ci_upper=bootstrap["ci_97_5_pct"],
        auc=global_metrics["auc"],
        calibration_slope=global_metrics["calibration_slope"],
    )
    verdict = classify_holdout_result(evidence)
    print(f"VERDICT: {verdict.verdict} -- {verdict.reason}")

    global_holdout_rows = holdout_lookup.loc[global_holdout_ids].reset_index()
    global_holdout_rows["p_a_win"] = global_holdout_preds
    global_holdout_rows = build_rank_gap_bucket(global_holdout_rows, set(ranking_holdout_ids), a4.RANK_GAP_N_BUCKETS)

    subgroups = {
        "surface": a4._subgroup_table(global_holdout_rows, "surface", "p_a_win"),
        "tourney_level": a4._subgroup_table(global_holdout_rows, "tourney_level", "p_a_win"),
        "best_of": a4._subgroup_table(global_holdout_rows, "best_of", "p_a_win"),
    }
    if "_rank_gap_bucket" in global_holdout_rows.columns:
        subgroups["rank_gap (usable-ranking matches only)"] = a4._subgroup_table(
            global_holdout_rows[global_holdout_rows["_usable_rank_mask"]], "_rank_gap_bucket", "p_a_win"
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_seasons": a4.TRAINING_SEASONS,
        "validation_season": a4.VALIDATION_SEASON,
        "holdout_season": a4.SEALED_HOLDOUT_SEASON,
        "k_factor": global_k,
        "n_holdout_total": int(len(holdout_df)),
        "global_elo": global_metrics,
        "ranking_baseline": ranking_metrics,
        "bootstrap": bootstrap,
        "bootstrap_seed": a4.BOOTSTRAP_SEED,
        "verdict": {"verdict": verdict.verdict, "reason": verdict.reason},
        "subgroups": subgroups,
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    pred_rows = []
    for mid in holdout_df["match_id"]:
        pred_rows.append({
            "match_id": mid,
            "season": a4.SEALED_HOLDOUT_SEASON,
            "outcome_a_won": int(holdout_lookup.loc[mid, "outcome_a_won"]),
            "surface": holdout_lookup.loc[mid, "surface"],
            "ranking_baseline_p_a_win": ranking_preds.get(mid, ""),
            "global_elo_p_a_win": global_preds.get(mid, ""),
        })
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(pred_rows).to_csv(PREDICTIONS_PATH, index=False)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(summary))

    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {PREDICTIONS_PATH}")
    print(f"Wrote {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
