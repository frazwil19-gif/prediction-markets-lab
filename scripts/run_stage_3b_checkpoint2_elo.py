#!/usr/bin/env python3
"""Stage 3B Checkpoint 2: leakage-safe Elo model (Model 1), scored
against the frozen dataset's naive and market baselines.

Per fold: replays Elo ratings from scratch through that fold's
training seasons only, calibrates draw_margin using ONLY that
training-period data (never the evaluation season), then predicts the
evaluation season from the resulting pre-match ratings. 2024/25 is
never read (see load_matches's development-season filter, shared with
Checkpoint 1).

Outputs:
    data/interim/stage_3b_checkpoint2_predictions.csv
    data/interim/stage_3b_checkpoint2_metrics.json

Run:
    python scripts/run_stage_3b_checkpoint2_elo.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.models.football_elo import (  # noqa: E402
    EloConfig,
    EloMatchInput,
    calibrate_draw_margin,
    run_elo_over_matches,
)
from prediction_markets_lab.performance.brier import multiclass_brier_score  # noqa: E402
from prediction_markets_lab.performance.log_loss import multiclass_log_loss  # noqa: E402
from prediction_markets_lab.validation.time_splits import (  # noqa: E402
    generate_expanding_walk_forward_folds,
)

DEVELOPMENT_SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24"]
SEALED_HOLDOUT_SEASON = "2024_25"
RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}
DRAW_MARGIN_CANDIDATES = [25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0]
BASE_ELO_CONFIG = EloConfig()  # literature-standard defaults; see football_elo.py docstring


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_matches(path: Path) -> list[dict]:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    development_rows = [row for row in rows if row["season"] in DEVELOPMENT_SEASONS]
    assert all(row["season"] != SEALED_HOLDOUT_SEASON for row in development_rows)
    return development_rows


def load_closing_consensus(path: Path) -> dict[str, dict]:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return {row["match_id"]: row for row in rows if row["price_timing"] == "closing"}


def to_elo_input(m: dict) -> EloMatchInput:
    return EloMatchInput(
        match_id=m["match_id"],
        season=m["season"],
        match_date=date.fromisoformat(m["match_date"]),
        home_team=m["home_team_normalised"],
        away_team=m["away_team_normalised"],
        full_time_result=m["full_time_result"],
    )


def main() -> int:
    verify_module = _load_module(REPO_ROOT / "scripts" / "verify_frozen_data_hashes.py", "verify_frozen_data_hashes")
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
    matches.sort(key=lambda r: (r["match_date"], r["match_id"]))

    folds = generate_expanding_walk_forward_folds(DEVELOPMENT_SEASONS)
    print(f"Generated {len(folds)} walk-forward folds: {[f.fold_id for f in folds]}")

    all_rows: list[dict] = []
    fold_metrics: list[dict] = []

    for fold in folds:
        fold_seasons = set(fold.train_seasons) | {fold.evaluate_season}
        fold_matches = [m for m in matches if m["season"] in fold_seasons]
        fold_matches.sort(key=lambda r: (r["match_date"], r["match_id"]))
        elo_inputs = [to_elo_input(m) for m in fold_matches]

        train_inputs = [ei for ei in elo_inputs if ei.season in fold.train_seasons]
        best_draw_margin = calibrate_draw_margin(train_inputs, BASE_ELO_CONFIG, DRAW_MARGIN_CANDIDATES)
        fold_config = EloConfig(
            initial_rating=BASE_ELO_CONFIG.initial_rating,
            k_factor=BASE_ELO_CONFIG.k_factor,
            home_advantage=BASE_ELO_CONFIG.home_advantage,
            season_reversion_fraction=BASE_ELO_CONFIG.season_reversion_fraction,
            draw_margin=best_draw_margin,
        )

        elo_preds_by_id = {p.match_id: p for p in run_elo_over_matches(elo_inputs, fold_config)}

        eval_matches = [m for m in fold_matches if m["season"] == fold.evaluate_season]

        elo_full_preds, elo_full_actuals = [], []
        common_elo_preds, common_market_preds, common_naive_preds, common_actuals = [], [], [], []

        for m in eval_matches:
            match_id = m["match_id"]
            actual = RESULT_TO_OUTCOME[m["full_time_result"]]
            elo_pred = elo_preds_by_id[match_id]
            elo_dict = {"home": elo_pred.p_home, "draw": elo_pred.p_draw, "away": elo_pred.p_away}

            elo_full_preds.append(elo_dict)
            elo_full_actuals.append(actual)

            consensus_row = closing_consensus.get(match_id)
            has_market = consensus_row is not None and m["eligible_consensus_model"] == "True"
            market_dict = None
            if has_market:
                raw_market = {
                    "home": float(consensus_row["median_fair_home_probability"]),
                    "draw": float(consensus_row["median_fair_draw_probability"]),
                    "away": float(consensus_row["median_fair_away_probability"]),
                }
                market_sum = sum(raw_market.values())
                market_dict = {k: v / market_sum for k, v in raw_market.items()}
                common_elo_preds.append(elo_dict)
                common_market_preds.append(market_dict)
                common_actuals.append(actual)

            all_rows.append({
                "fold_id": fold.fold_id,
                "match_id": match_id,
                "competition_code": m["competition_code"],
                "season": m["season"],
                "match_date": m["match_date"],
                "full_time_result": m["full_time_result"],
                "elo_p_home": elo_dict["home"],
                "elo_p_draw": elo_dict["draw"],
                "elo_p_away": elo_dict["away"],
                "elo_pre_match_home_rating": elo_pred.pre_match_home_rating,
                "elo_pre_match_away_rating": elo_pred.pre_match_away_rating,
                "market_p_home": market_dict["home"] if market_dict else "",
                "market_p_draw": market_dict["draw"] if market_dict else "",
                "market_p_away": market_dict["away"] if market_dict else "",
                "in_common_sample": has_market,
            })

        fold_metrics.append({
            "fold_id": fold.fold_id,
            "train_seasons": list(fold.train_seasons),
            "evaluate_season": fold.evaluate_season,
            "calibrated_draw_margin": best_draw_margin,
            "elo_full_coverage_n": len(elo_full_actuals),
            "elo_full_coverage_log_loss": multiclass_log_loss(elo_full_preds, elo_full_actuals),
            "elo_full_coverage_brier": multiclass_brier_score(elo_full_preds, elo_full_actuals),
            "common_sample_n": len(common_actuals),
            "elo_common_log_loss": multiclass_log_loss(common_elo_preds, common_actuals) if common_actuals else None,
            "elo_common_brier": multiclass_brier_score(common_elo_preds, common_actuals) if common_actuals else None,
            "market_common_log_loss": multiclass_log_loss(common_market_preds, common_actuals) if common_actuals else None,
            "market_common_brier": multiclass_brier_score(common_market_preds, common_actuals) if common_actuals else None,
        })

    pooled_common = [r for r in all_rows if r["in_common_sample"]]
    pooled_elo_preds = [{"home": r["elo_p_home"], "draw": r["elo_p_draw"], "away": r["elo_p_away"]} for r in pooled_common]
    pooled_market_preds = [{"home": r["market_p_home"], "draw": r["market_p_draw"], "away": r["market_p_away"]} for r in pooled_common]
    pooled_actuals = [RESULT_TO_OUTCOME[r["full_time_result"]] for r in pooled_common]
    pooled_full_elo_preds = [{"home": r["elo_p_home"], "draw": r["elo_p_draw"], "away": r["elo_p_away"]} for r in all_rows]
    pooled_full_actuals = [RESULT_TO_OUTCOME[r["full_time_result"]] for r in all_rows]

    summary = {
        "data_version": freeze_record["data_version"],
        "development_seasons": DEVELOPMENT_SEASONS,
        "sealed_holdout_season": SEALED_HOLDOUT_SEASON,
        "elo_base_config": {
            "initial_rating": BASE_ELO_CONFIG.initial_rating,
            "k_factor": BASE_ELO_CONFIG.k_factor,
            "home_advantage": BASE_ELO_CONFIG.home_advantage,
            "season_reversion_fraction": BASE_ELO_CONFIG.season_reversion_fraction,
        },
        "draw_margin_candidates": DRAW_MARGIN_CANDIDATES,
        "draw_margin_calibrated_per_fold_on": "training seasons only, in-sample log loss",
        "pooled_elo_full_coverage_n": len(all_rows),
        "pooled_elo_full_coverage_log_loss": multiclass_log_loss(pooled_full_elo_preds, pooled_full_actuals),
        "pooled_elo_full_coverage_brier": multiclass_brier_score(pooled_full_elo_preds, pooled_full_actuals),
        "pooled_common_sample_n": len(pooled_common),
        "pooled_elo_common_log_loss": multiclass_log_loss(pooled_elo_preds, pooled_actuals),
        "pooled_elo_common_brier": multiclass_brier_score(pooled_elo_preds, pooled_actuals),
        "pooled_market_common_log_loss": multiclass_log_loss(pooled_market_preds, pooled_actuals),
        "pooled_market_common_brier": multiclass_brier_score(pooled_market_preds, pooled_actuals),
        "delta_convention": "delta = elo_metric - market_metric; negative means Elo beats market, positive means market beats Elo",
        "pooled_delta_log_loss_elo_minus_market": multiclass_log_loss(pooled_elo_preds, pooled_actuals) - multiclass_log_loss(pooled_market_preds, pooled_actuals),
        "pooled_delta_brier_elo_minus_market": multiclass_brier_score(pooled_elo_preds, pooled_actuals) - multiclass_brier_score(pooled_market_preds, pooled_actuals),
        "fold_metrics": fold_metrics,
    }

    interim_dir = REPO_ROOT / "data" / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)
    with open(interim_dir / "stage_3b_checkpoint2_predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    with open(interim_dir / "stage_3b_checkpoint2_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
