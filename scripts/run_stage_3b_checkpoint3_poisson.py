#!/usr/bin/env python3
"""Stage 3B Checkpoint 3: leakage-safe Poisson model (Model 2), scored
against the frozen dataset's naive and market baselines (and Elo).

cycle_001_matches_full.csv does not carry full-time goal counts (only
FTR, the win/draw/loss result) -- the acquisition script never
extracted FTHG/FTAG. Rather than re-running the whole acquisition
pipeline again for one missing field, this script rebuilds the exact
same match_id used throughout the frozen dataset (via
ingestion.match_identity.build_match_id, the same function the
acquisition script itself uses) directly from the already-frozen raw
source CSVs, and joins FTHG/FTAG back onto the frozen match rows by
that match_id. This reads no new external data -- only the same 15
already-hash-verified raw files already used to build the frozen
processed tables -- so it does not change the dataset or its
provenance in any way; it only recovers a field the processing step
happened not to keep.

Run:
    python scripts/run_stage_3b_checkpoint3_poisson.py
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

from prediction_markets_lab.ingestion.match_identity import build_match_id  # noqa: E402
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
from prediction_markets_lab.validation.time_splits import (  # noqa: E402
    generate_expanding_walk_forward_folds,
)

DEVELOPMENT_SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24"]
SEALED_HOLDOUT_SEASON = "2024_25"
RESULT_TO_OUTCOME = {"H": "home", "D": "draw", "A": "away"}
COMPETITIONS = ["E0", "E1", "SC0"]


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
    """Rebuild {match_id: (home_goals, away_goals)} from the frozen raw CSVs.

    Uses the exact same match_id construction as the acquisition script
    (build_match_id keyed on competition/season/date/normalised names),
    so every match_id here matches cycle_001_matches_full.csv exactly.
    """
    goals: dict[str, tuple[int, int]] = {}
    for code in COMPETITIONS:
        for season in DEVELOPMENT_SEASONS:
            raw_path = (
                repo_root / "data" / "raw" / "football" / "football_data_co_uk" / code / season / f"{code}.csv"
            )
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
                    match_id = build_match_id(
                        code, season, match_date, home_norm or row["HomeTeam"], away_norm or row["AwayTeam"]
                    )
                    if not row.get("FTHG") or not row.get("FTAG"):
                        continue
                    goals[match_id] = (int(row["FTHG"]), int(row["FTAG"]))
    return goals


def to_poisson_input(m: dict, home_goals: int, away_goals: int) -> PoissonMatchInput:
    return PoissonMatchInput(
        match_id=m["match_id"],
        season=m["season"],
        match_date=date.fromisoformat(m["match_date"]),
        competition_code=m["competition_code"],
        home_team=m["home_team_normalised"],
        away_team=m["away_team_normalised"],
        home_goals=home_goals,
        away_goals=away_goals,
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

    alias_table = load_alias_table(REPO_ROOT / "config" / "football_team_aliases.yaml")
    goals_by_match_id = build_goals_by_match_id(REPO_ROOT, alias_table)

    missing = [m["match_id"] for m in matches if m["match_id"] not in goals_by_match_id]
    if missing:
        print(f"STOP -- {len(missing)} development match(es) have no goals joined from raw CSVs "
              f"(match_id reconstruction mismatch): {missing[:5]}")
        return 1
    print(f"Joined FTHG/FTAG for all {len(matches)} development matches from the frozen raw CSVs.")

    folds = generate_expanding_walk_forward_folds(DEVELOPMENT_SEASONS)
    print(f"Generated {len(folds)} walk-forward folds: {[f.fold_id for f in folds]}")

    poisson_config = PoissonConfig()
    all_rows: list[dict] = []
    fold_metrics: list[dict] = []

    for fold in folds:
        fold_seasons = set(fold.train_seasons) | {fold.evaluate_season}
        fold_matches = [m for m in matches if m["season"] in fold_seasons]
        fold_matches.sort(key=lambda r: (r["match_date"], r["match_id"]))
        poisson_inputs = [
            to_poisson_input(m, *goals_by_match_id[m["match_id"]]) for m in fold_matches
        ]
        poisson_preds_by_id = {p.match_id: p for p in run_poisson_over_matches(poisson_inputs, poisson_config)}

        eval_matches = [m for m in fold_matches if m["season"] == fold.evaluate_season]

        poisson_full_preds, poisson_full_actuals = [], []
        common_poisson_preds, common_market_preds, common_actuals = [], [], []

        for m in eval_matches:
            match_id = m["match_id"]
            actual = RESULT_TO_OUTCOME[m["full_time_result"]]
            pred = poisson_preds_by_id[match_id]
            pred_dict = {"home": pred.p_home, "draw": pred.p_draw, "away": pred.p_away}

            poisson_full_preds.append(pred_dict)
            poisson_full_actuals.append(actual)

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
                common_poisson_preds.append(pred_dict)
                common_market_preds.append(market_dict)
                common_actuals.append(actual)

            all_rows.append({
                "fold_id": fold.fold_id,
                "match_id": match_id,
                "competition_code": m["competition_code"],
                "season": m["season"],
                "match_date": m["match_date"],
                "full_time_result": m["full_time_result"],
                "poisson_p_home": pred_dict["home"],
                "poisson_p_draw": pred_dict["draw"],
                "poisson_p_away": pred_dict["away"],
                "poisson_lambda_home": pred.lambda_home,
                "poisson_lambda_away": pred.lambda_away,
                "market_p_home": market_dict["home"] if market_dict else "",
                "market_p_draw": market_dict["draw"] if market_dict else "",
                "market_p_away": market_dict["away"] if market_dict else "",
                "in_common_sample": has_market,
            })

        fold_metrics.append({
            "fold_id": fold.fold_id,
            "train_seasons": list(fold.train_seasons),
            "evaluate_season": fold.evaluate_season,
            "poisson_full_coverage_n": len(poisson_full_actuals),
            "poisson_full_coverage_log_loss": multiclass_log_loss(poisson_full_preds, poisson_full_actuals),
            "poisson_full_coverage_brier": multiclass_brier_score(poisson_full_preds, poisson_full_actuals),
            "common_sample_n": len(common_actuals),
            "poisson_common_log_loss": multiclass_log_loss(common_poisson_preds, common_actuals) if common_actuals else None,
            "poisson_common_brier": multiclass_brier_score(common_poisson_preds, common_actuals) if common_actuals else None,
            "market_common_log_loss": multiclass_log_loss(common_market_preds, common_actuals) if common_actuals else None,
            "market_common_brier": multiclass_brier_score(common_market_preds, common_actuals) if common_actuals else None,
        })

    pooled_common = [r for r in all_rows if r["in_common_sample"]]
    pooled_poisson_preds = [{"home": r["poisson_p_home"], "draw": r["poisson_p_draw"], "away": r["poisson_p_away"]} for r in pooled_common]
    pooled_market_preds = [{"home": r["market_p_home"], "draw": r["market_p_draw"], "away": r["market_p_away"]} for r in pooled_common]
    pooled_actuals = [RESULT_TO_OUTCOME[r["full_time_result"]] for r in pooled_common]
    pooled_full_poisson_preds = [{"home": r["poisson_p_home"], "draw": r["poisson_p_draw"], "away": r["poisson_p_away"]} for r in all_rows]
    pooled_full_actuals = [RESULT_TO_OUTCOME[r["full_time_result"]] for r in all_rows]

    summary = {
        "data_version": freeze_record["data_version"],
        "development_seasons": DEVELOPMENT_SEASONS,
        "sealed_holdout_season": SEALED_HOLDOUT_SEASON,
        "poisson_config": {
            "max_goals": poisson_config.max_goals,
            "shrinkage_matches": poisson_config.shrinkage_matches,
            "default_league_avg_home_goals": poisson_config.default_league_avg_home_goals,
            "default_league_avg_away_goals": poisson_config.default_league_avg_away_goals,
        },
        "pooled_poisson_full_coverage_n": len(all_rows),
        "pooled_poisson_full_coverage_log_loss": multiclass_log_loss(pooled_full_poisson_preds, pooled_full_actuals),
        "pooled_poisson_full_coverage_brier": multiclass_brier_score(pooled_full_poisson_preds, pooled_full_actuals),
        "pooled_common_sample_n": len(pooled_common),
        "pooled_poisson_common_log_loss": multiclass_log_loss(pooled_poisson_preds, pooled_actuals),
        "pooled_poisson_common_brier": multiclass_brier_score(pooled_poisson_preds, pooled_actuals),
        "pooled_market_common_log_loss": multiclass_log_loss(pooled_market_preds, pooled_actuals),
        "pooled_market_common_brier": multiclass_brier_score(pooled_market_preds, pooled_actuals),
        "delta_convention": "delta = poisson_metric - market_metric; negative means Poisson beats market, positive means market beats Poisson",
        "pooled_delta_log_loss_poisson_minus_market": multiclass_log_loss(pooled_poisson_preds, pooled_actuals) - multiclass_log_loss(pooled_market_preds, pooled_actuals),
        "pooled_delta_brier_poisson_minus_market": multiclass_brier_score(pooled_poisson_preds, pooled_actuals) - multiclass_brier_score(pooled_market_preds, pooled_actuals),
        "fold_metrics": fold_metrics,
    }

    interim_dir = REPO_ROOT / "data" / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)
    with open(interim_dir / "stage_3b_checkpoint3_predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    with open(interim_dir / "stage_3b_checkpoint3_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
