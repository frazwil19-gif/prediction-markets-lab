#!/usr/bin/env python3
"""Stage 3B Checkpoint 4: blends (Model 3) + paired bootstrap uncertainty.

Per the predeclared comparison matrix (STAGE_3B_PLAN.md / BLEND_REPORT.md):
Market-only, Elo-only, and Poisson-only are already evaluated in
Checkpoints 1-3 and are NOT recomputed here. This script computes the
4 genuinely new combinations -- justified because both Elo and Poisson
individually already demonstrated real signal (beating the naive
floor) in their own checkpoints, which is the predeclared bar for
progressing past single components:

    Elo + Poisson (fundamentals-only)
    Market + Elo
    Market + Poisson
    Market + Elo + Poisson

Blend weights are calibrated per walk-forward fold on that fold's
TRAINING period only (never its evaluation season), via an exhaustive
predeclared grid search (models.football_blended), then scored on the
same evaluation-season common sample used throughout Stage 3B.

Finally computes paired bootstrap confidence intervals (both
match-level and block-by-date methods) for every candidate's pooled
delta vs. the market, for both log loss and Brier.

Run:
    python scripts/run_stage_3b_checkpoint4_blends_and_uncertainty.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.match_identity import build_match_id  # noqa: E402
from prediction_markets_lab.models.football_blended import (  # noqa: E402
    BlendWeights,
    blend_probabilities,
    calibrate_blend_weights,
)
from prediction_markets_lab.models.football_elo import (  # noqa: E402
    EloConfig,
    EloMatchInput,
    calibrate_draw_margin,
    run_elo_over_matches,
)
from prediction_markets_lab.models.football_poisson import (  # noqa: E402
    PoissonConfig,
    PoissonMatchInput,
    run_poisson_over_matches,
)
from prediction_markets_lab.normalisation.team_names import (  # noqa: E402
    load_alias_table,
    normalise_team_name,
)
from prediction_markets_lab.performance.brier import multiclass_brier_score  # noqa: E402
from prediction_markets_lab.performance.log_loss import multiclass_log_loss  # noqa: E402
from prediction_markets_lab.probability.uncertainty import paired_bootstrap_delta  # noqa: E402
from prediction_markets_lab.validation.time_splits import (  # noqa: E402
    generate_expanding_walk_forward_folds,
)

DEVELOPMENT_SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24"]
SEALED_HOLDOUT_SEASON = "2024_25"
RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}
COMPETITIONS = ["E0", "E1", "SC0"]
DRAW_MARGIN_CANDIDATES = [25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0]
BASE_ELO_CONFIG = EloConfig()
POISSON_CONFIG = PoissonConfig()
BLEND_STEP = 0.1
BLEND_COMBOS = [
    ("elo_poisson", ("elo", "poisson")),
    ("market_elo", ("market", "elo")),
    ("market_poisson", ("market", "poisson")),
    ("market_elo_poisson", ("market", "elo", "poisson")),
]


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


def build_goals_by_match_id(repo_root: Path, alias_table: dict[str, str]) -> dict[str, tuple[int, int]]:
    goals: dict[str, tuple[int, int]] = {}
    for code in COMPETITIONS:
        for season in DEVELOPMENT_SEASONS:
            raw_path = repo_root / "data" / "raw" / "football" / "football_data_co_uk" / code / season / f"{code}.csv"
            with open(raw_path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if not row.get("Date") or not row.get("HomeTeam"):
                        continue
                    try:
                        day, month, year = row["Date"].split("/")
                        match_date = f"{year}-{month}-{day}"
                    except (ValueError, KeyError):
                        continue
                    home_norm = normalise_team_name(row["HomeTeam"], alias_table)
                    away_norm = normalise_team_name(row["AwayTeam"], alias_table)
                    match_id = build_match_id(code, season, match_date, home_norm or row["HomeTeam"], away_norm or row["AwayTeam"])
                    if not row.get("FTHG") or not row.get("FTAG"):
                        continue
                    goals[match_id] = (int(row["FTHG"]), int(row["FTAG"]))
    return goals


def market_dict_for(consensus_row: dict) -> dict:
    raw = {
        "home": float(consensus_row["median_fair_home_probability"]),
        "draw": float(consensus_row["median_fair_draw_probability"]),
        "away": float(consensus_row["median_fair_away_probability"]),
    }
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


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
    closing_consensus = load_closing_consensus(REPO_ROOT / "data" / "processed" / "football" / "cycle_001_consensus_full.csv")
    matches.sort(key=lambda r: (r["match_date"], r["match_id"]))

    alias_table = load_alias_table(REPO_ROOT / "config" / "football_team_aliases.yaml")
    goals_by_match_id = build_goals_by_match_id(REPO_ROOT, alias_table)

    folds = generate_expanding_walk_forward_folds(DEVELOPMENT_SEASONS)
    print(f"Generated {len(folds)} walk-forward folds: {[f.fold_id for f in folds]}")

    # Pooled prediction store per combo, across all folds' evaluation matches
    # (common sample: eligible_consensus_model AND closing consensus present).
    pooled_preds = {combo_name: [] for combo_name, _ in BLEND_COMBOS}
    pooled_elo_preds, pooled_poisson_preds, pooled_market_preds = [], [], []
    pooled_actuals, pooled_dates = [], []
    pooled_match_ids, pooled_seasons = [], []
    fold_reports = []

    for fold in folds:
        fold_seasons = set(fold.train_seasons) | {fold.evaluate_season}
        fold_matches = [m for m in matches if m["season"] in fold_seasons]
        fold_matches.sort(key=lambda r: (r["match_date"], r["match_id"]))

        elo_inputs = [
            EloMatchInput(m["match_id"], m["season"], date.fromisoformat(m["match_date"]),
                          m["home_team_normalised"], m["away_team_normalised"], m["full_time_result"])
            for m in fold_matches
        ]
        train_elo_inputs = [ei for ei in elo_inputs if ei.season in fold.train_seasons]
        best_draw_margin = calibrate_draw_margin(train_elo_inputs, BASE_ELO_CONFIG, DRAW_MARGIN_CANDIDATES)
        fold_elo_config = EloConfig(
            initial_rating=BASE_ELO_CONFIG.initial_rating, k_factor=BASE_ELO_CONFIG.k_factor,
            home_advantage=BASE_ELO_CONFIG.home_advantage,
            season_reversion_fraction=BASE_ELO_CONFIG.season_reversion_fraction,
            draw_margin=best_draw_margin,
        )
        elo_preds_by_id = {p.match_id: {"home": p.p_home, "draw": p.p_draw, "away": p.p_away}
                            for p in run_elo_over_matches(elo_inputs, fold_elo_config)}

        poisson_inputs = [
            PoissonMatchInput(m["match_id"], m["season"], date.fromisoformat(m["match_date"]), m["competition_code"],
                               m["home_team_normalised"], m["away_team_normalised"],
                               *goals_by_match_id[m["match_id"]], m["full_time_result"])
            for m in fold_matches
        ]
        poisson_preds_by_id = {p.match_id: {"home": p.p_home, "draw": p.p_draw, "away": p.p_away}
                                for p in run_poisson_over_matches(poisson_inputs, POISSON_CONFIG)}

        fold_matches_by_id = {m["match_id"]: m for m in fold_matches}
        train_ids = {m["match_id"] for m in fold_matches if m["season"] in fold.train_seasons}
        # Restrict to training matches with usable market data (needed for any market-containing blend).
        train_common_ids = [
            m["match_id"] for m in fold_matches
            if m["match_id"] in train_ids
            and m["eligible_consensus_model"] == "True"
            and m["match_id"] in closing_consensus
        ]
        train_actuals = [RESULT_TO_OUTCOME[fold_matches_by_id[mid]["full_time_result"]] for mid in train_common_ids]
        train_market = [market_dict_for(closing_consensus[mid]) for mid in train_common_ids]
        train_elo = [elo_preds_by_id[mid] for mid in train_common_ids]
        train_poisson = [poisson_preds_by_id[mid] for mid in train_common_ids]
        train_components = {"market": train_market, "elo": train_elo, "poisson": train_poisson}

        fold_blend_weights = {}
        for combo_name, component_names in BLEND_COMBOS:
            sub_components = {name: train_components[name] for name in component_names}
            fold_blend_weights[combo_name] = calibrate_blend_weights(sub_components, train_actuals, step=BLEND_STEP)

        eval_matches = [m for m in fold_matches if m["season"] == fold.evaluate_season]
        fold_combo_preds = {combo_name: [] for combo_name, _ in BLEND_COMBOS}
        fold_elo_eval, fold_poisson_eval, fold_market_eval, fold_actuals_eval, fold_dates_eval = [], [], [], [], []

        for m in eval_matches:
            match_id = m["match_id"]
            if not (m["eligible_consensus_model"] == "True" and match_id in closing_consensus):
                continue
            actual = RESULT_TO_OUTCOME[m["full_time_result"]]
            elo_p = elo_preds_by_id[match_id]
            poisson_p = poisson_preds_by_id[match_id]
            market_p = market_dict_for(closing_consensus[match_id])
            components_here = {"market": market_p, "elo": elo_p, "poisson": poisson_p}

            for combo_name, component_names in BLEND_COMBOS:
                sub = {name: components_here[name] for name in component_names}
                blended = blend_probabilities(sub, fold_blend_weights[combo_name])
                fold_combo_preds[combo_name].append(blended)
                pooled_preds[combo_name].append(blended)

            fold_elo_eval.append(elo_p)
            fold_poisson_eval.append(poisson_p)
            fold_market_eval.append(market_p)
            fold_actuals_eval.append(actual)
            fold_dates_eval.append(m["match_date"])

            pooled_elo_preds.append(elo_p)
            pooled_poisson_preds.append(poisson_p)
            pooled_market_preds.append(market_p)
            pooled_actuals.append(actual)
            pooled_dates.append(m["match_date"])
            pooled_match_ids.append(match_id)
            pooled_seasons.append(m["season"])

        fold_report = {
            "fold_id": fold.fold_id,
            "evaluate_season": fold.evaluate_season,
            "common_sample_n": len(fold_actuals_eval),
            "calibrated_draw_margin": best_draw_margin,
            "blend_weights": {name: fold_blend_weights[name].weights for name, _ in BLEND_COMBOS},
            "metrics": {},
        }
        for combo_name, _ in BLEND_COMBOS:
            fold_report["metrics"][combo_name] = {
                "log_loss": multiclass_log_loss(fold_combo_preds[combo_name], fold_actuals_eval),
                "brier": multiclass_brier_score(fold_combo_preds[combo_name], fold_actuals_eval),
            }
        fold_report["metrics"]["market"] = {
            "log_loss": multiclass_log_loss(fold_market_eval, fold_actuals_eval),
            "brier": multiclass_brier_score(fold_market_eval, fold_actuals_eval),
        }
        fold_reports.append(fold_report)

    # Pooled metrics for every combo + market/elo/poisson (elo/poisson pooled here
    # for direct comparison, recomputed on this script's own common sample so
    # every number in this report is drawn from one consistent pass).
    pooled_metrics = {
        "market": {
            "log_loss": multiclass_log_loss(pooled_market_preds, pooled_actuals),
            "brier": multiclass_brier_score(pooled_market_preds, pooled_actuals),
        },
        "elo": {
            "log_loss": multiclass_log_loss(pooled_elo_preds, pooled_actuals),
            "brier": multiclass_brier_score(pooled_elo_preds, pooled_actuals),
        },
        "poisson": {
            "log_loss": multiclass_log_loss(pooled_poisson_preds, pooled_actuals),
            "brier": multiclass_brier_score(pooled_poisson_preds, pooled_actuals),
        },
    }
    for combo_name, _ in BLEND_COMBOS:
        pooled_metrics[combo_name] = {
            "log_loss": multiclass_log_loss(pooled_preds[combo_name], pooled_actuals),
            "brier": multiclass_brier_score(pooled_preds[combo_name], pooled_actuals),
        }

    # Paired bootstrap CIs vs market, pooled, both methods, both metrics,
    # for every candidate that is not the market itself.
    candidates = {"elo": pooled_elo_preds, "poisson": pooled_poisson_preds}
    candidates.update({name: pooled_preds[name] for name, _ in BLEND_COMBOS})

    bootstrap_results = {}
    for name, preds in candidates.items():
        bootstrap_results[name] = {}
        for metric in ("log_loss", "brier"):
            for method in ("match_level", "block_by_date"):
                result = paired_bootstrap_delta(
                    preds, pooled_market_preds, pooled_actuals, metric=metric,
                    dates=pooled_dates, method=method, n_resamples=2000, seed=42,
                )
                bootstrap_results[name][f"{metric}_{method}"] = asdict(result)

    summary = {
        "data_version": freeze_record["data_version"],
        "development_seasons": DEVELOPMENT_SEASONS,
        "sealed_holdout_season": SEALED_HOLDOUT_SEASON,
        "blend_combos_run": {name: list(components) for name, components in BLEND_COMBOS},
        "blend_step": BLEND_STEP,
        "pooled_common_sample_n": len(pooled_actuals),
        "pooled_metrics": pooled_metrics,
        "delta_convention": "delta = candidate_metric - market_metric; negative means candidate beats market",
        "bootstrap_n_resamples": 2000,
        "bootstrap_seed": 42,
        "bootstrap_results": bootstrap_results,
        "fold_reports": fold_reports,
    }

    interim_dir = REPO_ROOT / "data" / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)
    with open(interim_dir / "stage_3b_checkpoint4_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Pooled per-match predictions, one row per match_id, for downstream
    # calibration/reliability diagnostics (CALIBRATION_REPORT.md) -- avoids
    # re-deriving these exact pooled prediction vectors a second time.
    combo_names = [name for name, _ in BLEND_COMBOS]
    predictions_path = interim_dir / "stage_3b_checkpoint4_predictions.csv"
    fieldnames = ["match_id", "season", "match_date", "actual_outcome",
                  "market_p_home", "market_p_draw", "market_p_away",
                  "elo_p_home", "elo_p_draw", "elo_p_away",
                  "poisson_p_home", "poisson_p_draw", "poisson_p_away"]
    for combo_name in combo_names:
        fieldnames += [f"{combo_name}_p_home", f"{combo_name}_p_draw", f"{combo_name}_p_away"]
    with open(predictions_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(len(pooled_actuals)):
            row = {
                "match_id": pooled_match_ids[i],
                "season": pooled_seasons[i],
                "match_date": pooled_dates[i],
                "actual_outcome": pooled_actuals[i],
                "market_p_home": pooled_market_preds[i]["home"],
                "market_p_draw": pooled_market_preds[i]["draw"],
                "market_p_away": pooled_market_preds[i]["away"],
                "elo_p_home": pooled_elo_preds[i]["home"],
                "elo_p_draw": pooled_elo_preds[i]["draw"],
                "elo_p_away": pooled_elo_preds[i]["away"],
                "poisson_p_home": pooled_poisson_preds[i]["home"],
                "poisson_p_draw": pooled_poisson_preds[i]["draw"],
                "poisson_p_away": pooled_poisson_preds[i]["away"],
            }
            for combo_name in combo_names:
                row[f"{combo_name}_p_home"] = pooled_preds[combo_name][i]["home"]
                row[f"{combo_name}_p_draw"] = pooled_preds[combo_name][i]["draw"]
                row[f"{combo_name}_p_away"] = pooled_preds[combo_name][i]["away"]
            writer.writerow(row)

    print(json.dumps({k: v for k, v in summary.items() if k != "fold_reports"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
