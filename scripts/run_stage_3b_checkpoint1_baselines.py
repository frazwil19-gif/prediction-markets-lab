#!/usr/bin/env python3
"""Stage 3B Checkpoint 1: naive-frequency and market-consensus baselines.

Computes BASELINE 0 (naive historical frequency) and BASELINE 1
(market closing consensus) across the walk-forward development folds
defined in research/cycles/CYCLE_001/STAGE_3B_PLAN.md, entirely within
the 2020/21-2023/24 development seasons. The 2024/25 season is never
read by this script.

Outputs (all regenerable, not committed -- see data/interim/ in
.gitignore):
    data/interim/stage_3b_checkpoint1_predictions.csv
    data/interim/stage_3b_checkpoint1_metrics.json

Run:
    python scripts/run_stage_3b_checkpoint1_baselines.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.models.football_naive_frequency import (  # noqa: E402
    NaiveFrequencyMatchInput,
    compute_naive_frequency_predictions,
)
from prediction_markets_lab.performance.brier import multiclass_brier_score  # noqa: E402
from prediction_markets_lab.performance.log_loss import multiclass_log_loss  # noqa: E402
from prediction_markets_lab.validation.time_splits import (  # noqa: E402
    generate_expanding_walk_forward_folds,
)

DEVELOPMENT_SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24"]
SEALED_HOLDOUT_SEASON = "2024_25"  # must never be read by this script
RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}


def load_matches(path: Path) -> list[dict]:
    """Load match rows, keeping ONLY development seasons.

    The source CSV legitimately contains the sealed 2024_25 holdout
    season too (it is one combined file across all 5 seasons) -- the
    seal is enforced here by construction: rows outside
    DEVELOPMENT_SEASONS are filtered out before this function returns
    anything, so no code downstream of this call can ever see or
    accidentally use a 2024_25 row.
    """
    with open(path) as f:
        rows = list(csv.DictReader(f))
    development_rows = [row for row in rows if row["season"] in DEVELOPMENT_SEASONS]
    assert all(row["season"] != SEALED_HOLDOUT_SEASON for row in development_rows), (
        "internal error: a sealed-holdout-season row leaked past the development-season filter"
    )
    return development_rows


def load_closing_consensus(path: Path) -> dict[str, dict]:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return {row["match_id"]: row for row in rows if row["price_timing"] == "closing"}


def main() -> int:
    verify_script = REPO_ROOT / "scripts" / "verify_frozen_data_hashes.py"
    sys.path.insert(0, str(verify_script.parent))
    import importlib.util

    spec = importlib.util.spec_from_file_location("verify_frozen_data_hashes", verify_script)
    verify_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verify_module)

    freeze_record_path = REPO_ROOT / "reports" / "audits" / "CYCLE_001_FREEZE_RECORD.json"
    with open(freeze_record_path) as f:
        freeze_record = json.load(f)
    problems = verify_module.verify_frozen_data_hashes(freeze_record, repo_root=REPO_ROOT)
    if problems:
        print("STOP -- frozen data hash verification failed:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Frozen data hashes verified OK (data_version {freeze_record['data_version']}).")

    matches = load_matches(REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv")
    closing_consensus = load_closing_consensus(
        REPO_ROOT / "data" / "processed" / "football" / "cycle_001_consensus_full.csv"
    )

    # Sort globally chronologically (ties broken by match_id for determinism)
    # -- required by compute_naive_frequency_predictions, and correct here
    # since naive frequency tracks each competition's own count independently.
    matches.sort(key=lambda r: (r["match_date"], r["match_id"]))

    folds = generate_expanding_walk_forward_folds(DEVELOPMENT_SEASONS)
    print(f"Generated {len(folds)} walk-forward folds: {[f.fold_id for f in folds]}")

    all_rows: list[dict] = []
    fold_metrics: list[dict] = []

    for fold in folds:
        fold_seasons = set(fold.train_seasons) | {fold.evaluate_season}
        fold_matches = [m for m in matches if m["season"] in fold_seasons]
        fold_matches.sort(key=lambda r: (r["match_date"], r["match_id"]))

        naive_inputs = [
            NaiveFrequencyMatchInput(
                match_id=m["match_id"],
                competition_code=m["competition_code"],
                match_date=date.fromisoformat(m["match_date"]),
                full_time_result=m["full_time_result"],
            )
            for m in fold_matches
        ]
        naive_preds_by_id = {
            p.match_id: p for p in compute_naive_frequency_predictions(naive_inputs)
        }

        eval_matches = [m for m in fold_matches if m["season"] == fold.evaluate_season]

        naive_full_preds, naive_full_actuals, naive_full_ids = [], [], []
        common_naive_preds, common_market_preds, common_actuals, common_ids = [], [], [], []

        for m in eval_matches:
            match_id = m["match_id"]
            actual = RESULT_TO_OUTCOME[m["full_time_result"]]
            naive_pred = naive_preds_by_id[match_id]
            naive_dict = {"home": naive_pred.p_home, "draw": naive_pred.p_draw, "away": naive_pred.p_away}

            naive_full_preds.append(naive_dict)
            naive_full_actuals.append(actual)
            naive_full_ids.append(match_id)

            consensus_row = closing_consensus.get(match_id)
            has_market = consensus_row is not None and m["eligible_consensus_model"] == "True"

            market_dict = None
            if has_market:
                raw_market = {
                    "home": float(consensus_row["median_fair_home_probability"]),
                    "draw": float(consensus_row["median_fair_draw_probability"]),
                    "away": float(consensus_row["median_fair_away_probability"]),
                }
                # The per-outcome MEDIAN across bookmakers does not exactly
                # sum to 1.0 (see reports/audits/CURRENT_STATE_AUDIT.md
                # Update 4: up to 1.18% deviation, median 0.13% -- expected
                # for a per-outcome median, not a joint renormalisation).
                # Log loss/Brier require a genuine probability vector, so
                # renormalise here (divide by the sum) rather than loosen
                # the metric functions' sum-to-1 tolerance to paper over it.
                market_sum = sum(raw_market.values())
                market_dict = {k: v / market_sum for k, v in raw_market.items()}
                common_naive_preds.append(naive_dict)
                common_market_preds.append(market_dict)
                common_actuals.append(actual)
                common_ids.append(match_id)

            all_rows.append({
                "fold_id": fold.fold_id,
                "match_id": match_id,
                "competition_code": m["competition_code"],
                "season": m["season"],
                "match_date": m["match_date"],
                "full_time_result": m["full_time_result"],
                "naive_p_home": naive_dict["home"],
                "naive_p_draw": naive_dict["draw"],
                "naive_p_away": naive_dict["away"],
                "naive_n_prior_matches": naive_pred.n_prior_matches,
                "market_p_home": market_dict["home"] if market_dict else "",
                "market_p_draw": market_dict["draw"] if market_dict else "",
                "market_p_away": market_dict["away"] if market_dict else "",
                "in_common_sample": has_market,
            })

        fold_metrics.append({
            "fold_id": fold.fold_id,
            "train_seasons": list(fold.train_seasons),
            "evaluate_season": fold.evaluate_season,
            "naive_full_coverage_n": len(naive_full_ids),
            "naive_full_coverage_log_loss": multiclass_log_loss(naive_full_preds, naive_full_actuals),
            "naive_full_coverage_brier": multiclass_brier_score(naive_full_preds, naive_full_actuals),
            "common_sample_n": len(common_ids),
            "naive_common_log_loss": multiclass_log_loss(common_naive_preds, common_actuals) if common_ids else None,
            "naive_common_brier": multiclass_brier_score(common_naive_preds, common_actuals) if common_ids else None,
            "market_common_log_loss": multiclass_log_loss(common_market_preds, common_actuals) if common_ids else None,
            "market_common_brier": multiclass_brier_score(common_market_preds, common_actuals) if common_ids else None,
        })

    # Pooled summary across all evaluation matches (2021_22 + 2022_23 + 2023_24,
    # i.e. every season except 2020_21, which is only ever used for training).
    pooled_common_naive = [r for r in all_rows if r["in_common_sample"]]
    pooled_naive_preds = [{"home": r["naive_p_home"], "draw": r["naive_p_draw"], "away": r["naive_p_away"]} for r in pooled_common_naive]
    pooled_market_preds = [{"home": r["market_p_home"], "draw": r["market_p_draw"], "away": r["market_p_away"]} for r in pooled_common_naive]
    pooled_actuals = [RESULT_TO_OUTCOME[r["full_time_result"]] for r in pooled_common_naive]

    pooled_full_naive_preds = [{"home": r["naive_p_home"], "draw": r["naive_p_draw"], "away": r["naive_p_away"]} for r in all_rows]
    pooled_full_actuals = [RESULT_TO_OUTCOME[r["full_time_result"]] for r in all_rows]

    summary = {
        "data_version": freeze_record["data_version"],
        "development_seasons": DEVELOPMENT_SEASONS,
        "sealed_holdout_season": SEALED_HOLDOUT_SEASON,
        "fold_definitions": [f.fold_id for f in folds],
        "laplace_alpha": 1.0,
        "market_price_timing_used": "closing",
        "market_benchmark_classification": "market_predictive_benchmark (NOT historically_executable_entry_price)",
        "pooled_naive_full_coverage_n": len(all_rows),
        "pooled_naive_full_coverage_log_loss": multiclass_log_loss(pooled_full_naive_preds, pooled_full_actuals),
        "pooled_naive_full_coverage_brier": multiclass_brier_score(pooled_full_naive_preds, pooled_full_actuals),
        "pooled_common_sample_n": len(pooled_common_naive),
        "pooled_naive_common_log_loss": multiclass_log_loss(pooled_naive_preds, pooled_actuals),
        "pooled_naive_common_brier": multiclass_brier_score(pooled_naive_preds, pooled_actuals),
        "pooled_market_common_log_loss": multiclass_log_loss(pooled_market_preds, pooled_actuals),
        "pooled_market_common_brier": multiclass_brier_score(pooled_market_preds, pooled_actuals),
        "delta_convention": "delta = naive_metric - market_metric; negative means naive beats market, positive means market beats naive",
        "pooled_delta_log_loss_naive_minus_market": multiclass_log_loss(pooled_naive_preds, pooled_actuals) - multiclass_log_loss(pooled_market_preds, pooled_actuals),
        "pooled_delta_brier_naive_minus_market": multiclass_brier_score(pooled_naive_preds, pooled_actuals) - multiclass_brier_score(pooled_market_preds, pooled_actuals),
        "fold_metrics": fold_metrics,
    }

    interim_dir = REPO_ROOT / "data" / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)

    with open(interim_dir / "stage_3b_checkpoint1_predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    with open(interim_dir / "stage_3b_checkpoint1_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
