#!/usr/bin/env python3
"""Stage 3B Checkpoint 6: the sealed 2024/25 holdout evaluation.

THIS IS THE ONE SCRIPT IN STAGE 3B THAT IS AUTHORISED TO READ THE 2024/25
SEASON. Every other Stage 3B script filters it out by construction and
asserts its absence (see each checkpoint script's own load_matches() and
seal-guard test). This script may only be run once its procedure has been
pre-registered and frozen -- see
research/cycles/CYCLE_001/results/FINAL_HOLDOUT_PROTOCOL.md and
reports/audits/STAGE_3B_PRE_HOLDOUT_FREEZE.json, both verified before any
holdout data is read.

Procedure (exactly as pre-registered, no deviation):
    1. Verify frozen data hashes AND the pre-holdout freeze record.
    2. Fit every model on all 4 development seasons (2020_21-2023_24) as
       training data -- this is exactly the natural 4th walk-forward fold
       (train on all of 2020_21..2023_24, evaluate on 2024_25), reusing
       validation.time_splits.generate_expanding_walk_forward_folds rather
       than hand-rolling new fold logic.
    3. Calibrate Elo's draw_margin and all 4 blend weight combinations on
       that training period only (never on 2024_25).
    4. Score all 8 predeclared candidates once on the 2024/25 common
       sample: log loss, Brier, raw calibration (ECE), and paired
       bootstrap CI vs. market (both methods).
    5. Apply the frozen verdict rubric mechanically and write the result.

Run:
    python scripts/run_stage_3b_checkpoint6_holdout_evaluation.py
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
    blend_probabilities,
    calibrate_blend_weights,
)
from prediction_markets_lab.models.football_elo import (  # noqa: E402
    EloConfig,
    EloMatchInput,
    calibrate_draw_margin,
    run_elo_over_matches,
)
from prediction_markets_lab.models.football_naive_frequency import (  # noqa: E402
    NaiveFrequencyMatchInput,
    compute_naive_frequency_predictions,
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
from prediction_markets_lab.performance.calibration import compute_outcome_calibration  # noqa: E402
from prediction_markets_lab.performance.log_loss import multiclass_log_loss  # noqa: E402
from prediction_markets_lab.probability.uncertainty import paired_bootstrap_delta  # noqa: E402
from prediction_markets_lab.validation.time_splits import (  # noqa: E402
    generate_expanding_walk_forward_folds,
)

ALL_SEASONS_INCLUDING_HOLDOUT = ["2020_21", "2021_22", "2022_23", "2023_24", "2024_25"]
TRAINING_SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24"]
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
CALIBRATION_MODELS = ("market", "elo", "poisson", "elo_poisson")
CALIBRATION_N_BINS = 5


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_matches_including_holdout(path: Path) -> list[dict]:
    """UNIQUE to this script: does NOT filter out 2024_25.

    Every other Stage 3B script's load_matches() excludes the sealed
    holdout season by construction. This is the one authorised exception,
    gated on the pre-holdout freeze verification in main() running first.
    """
    with open(path) as f:
        rows = list(csv.DictReader(f))
    included_rows = [row for row in rows if row["season"] in ALL_SEASONS_INCLUDING_HOLDOUT]
    return included_rows


def load_closing_consensus(path: Path) -> dict[str, dict]:
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return {row["match_id"]: row for row in rows if row["price_timing"] == "closing"}


def build_goals_by_match_id(repo_root: Path, alias_table: dict[str, str]) -> dict[str, tuple[int, int]]:
    goals: dict[str, tuple[int, int]] = {}
    for code in COMPETITIONS:
        for season in ALL_SEASONS_INCLUDING_HOLDOUT:
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


def apply_verdict_rubric(best_candidate_name: str, best_delta: float, best_ci_lower: float, best_ci_upper: float) -> str:
    """Mechanical application of FINAL_HOLDOUT_PROTOCOL.md section 5.

    Args:
        best_candidate_name: name of the best-performing non-market
            candidate by pooled holdout log loss.
        best_delta: that candidate's log-loss point-estimate delta vs.
            market (delta = candidate - market; negative = candidate wins).
        best_ci_lower, best_ci_upper: that candidate's block-by-date 95%
            bootstrap CI on the log-loss delta.

    Returns:
        One of "STRONG SIGNAL", "WEAK-UNCERTAIN SIGNAL",
        "MARKET DOMINATES / NULL RESULT".  ("INVALID" is applied
        separately, before this function is even called, if a hash
        verification fails or a dataset defect is found -- see main().)
    """
    if best_delta < 0 and best_ci_upper < 0:
        return "STRONG SIGNAL"
    if best_delta > 0 and best_ci_lower > 0:
        return "MARKET DOMINATES / NULL RESULT"
    if (best_delta < 0 and best_ci_lower <= 0 <= best_ci_upper) or abs(best_delta) < 0.005:
        return "WEAK-UNCERTAIN SIGNAL"
    # Any remaining shape (e.g. positive point estimate but CI includes
    # zero) is also an uncertain result -- not a confirmed market win.
    return "WEAK-UNCERTAIN SIGNAL"


def main() -> int:
    # Step 1: verify BOTH the frozen data AND the frozen holdout protocol
    # before reading a single row of 2024/25 data.
    verify_data_module = _load_module(REPO_ROOT / "scripts" / "verify_frozen_data_hashes.py", "verify_frozen_data_hashes")
    freeze_record_path = REPO_ROOT / "reports" / "audits" / "CYCLE_001_FREEZE_RECORD.json"
    with open(freeze_record_path) as f:
        data_freeze_record = json.load(f)
    data_problems = verify_data_module.verify_frozen_data_hashes(data_freeze_record, repo_root=REPO_ROOT)
    if data_problems:
        print("STOP -- frozen data hash verification failed (INVALID run):")
        for p in data_problems:
            print(f"  - {p}")
        return 1

    verify_protocol_module = _load_module(REPO_ROOT / "scripts" / "verify_pre_holdout_freeze.py", "verify_pre_holdout_freeze")
    protocol_freeze_path = REPO_ROOT / "reports" / "audits" / "STAGE_3B_PRE_HOLDOUT_FREEZE.json"
    with open(protocol_freeze_path) as f:
        protocol_freeze_record = json.load(f)
    protocol_problems = verify_protocol_module.verify_pre_holdout_freeze(protocol_freeze_record, repo_root=REPO_ROOT)
    if protocol_problems:
        print("STOP -- pre-holdout freeze verification failed (INVALID run):")
        for p in protocol_problems:
            print(f"  - {p}")
        return 1
    print(f"Frozen data hashes verified OK (data_version {data_freeze_record['data_version']}).")
    print(f"Pre-holdout freeze verified OK ({protocol_freeze_record['freeze_name']}).")

    matches = load_matches_including_holdout(REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv")
    closing_consensus = load_closing_consensus(REPO_ROOT / "data" / "processed" / "football" / "cycle_001_consensus_full.csv")
    matches.sort(key=lambda r: (r["match_date"], r["match_id"]))

    # Predeclared coverage check (FINAL_HOLDOUT_PROTOCOL.md section 2) --
    # any deviation is itself reported, not silently absorbed.
    holdout_rows = [m for m in matches if m["season"] == SEALED_HOLDOUT_SEASON]
    expected = protocol_freeze_record["predeclared_holdout_coverage"]
    coverage_problems = []
    if len(holdout_rows) != expected["full_coverage_n"]:
        coverage_problems.append(
            f"holdout full coverage is {len(holdout_rows)}, predeclared expectation was {expected['full_coverage_n']}"
        )
    by_comp = {}
    for r in holdout_rows:
        by_comp[r["competition_code"]] = by_comp.get(r["competition_code"], 0) + 1
    if by_comp != expected["by_competition"]:
        coverage_problems.append(f"holdout per-competition coverage is {by_comp}, predeclared expectation was {expected['by_competition']}")
    if coverage_problems:
        print("STOP -- holdout coverage does not match the pre-registered expectation (INVALID run):")
        for p in coverage_problems:
            print(f"  - {p}")
        return 1
    print(f"Holdout coverage verified OK ({len(holdout_rows)} matches, {by_comp}).")

    alias_table = load_alias_table(REPO_ROOT / "config" / "football_team_aliases.yaml")
    goals_by_match_id = build_goals_by_match_id(REPO_ROOT, alias_table)
    matches_by_id = {m["match_id"]: m for m in matches}

    # This is exactly the natural 4th walk-forward fold -- reuse the
    # existing, already-tested fold generator rather than hand-rolling.
    folds = generate_expanding_walk_forward_folds(ALL_SEASONS_INCLUDING_HOLDOUT)
    holdout_fold = folds[-1]
    assert holdout_fold.evaluate_season == SEALED_HOLDOUT_SEASON
    assert set(holdout_fold.train_seasons) == set(TRAINING_SEASONS)
    print(f"Holdout fold: {holdout_fold.fold_id}")

    # --- Fit every model on the training period, predict over train+holdout ---
    naive_inputs = [
        NaiveFrequencyMatchInput(m["match_id"], m["competition_code"], date.fromisoformat(m["match_date"]), m["full_time_result"])
        for m in matches
    ]
    naive_preds_by_id = {p.match_id: {"home": p.p_home, "draw": p.p_draw, "away": p.p_away} for p in compute_naive_frequency_predictions(naive_inputs)}

    elo_inputs = [
        EloMatchInput(m["match_id"], m["season"], date.fromisoformat(m["match_date"]),
                      m["home_team_normalised"], m["away_team_normalised"], m["full_time_result"])
        for m in matches
    ]
    train_elo_inputs = [ei for ei in elo_inputs if ei.season in TRAINING_SEASONS]
    best_draw_margin = calibrate_draw_margin(train_elo_inputs, BASE_ELO_CONFIG, DRAW_MARGIN_CANDIDATES)
    elo_config = EloConfig(
        initial_rating=BASE_ELO_CONFIG.initial_rating, k_factor=BASE_ELO_CONFIG.k_factor,
        home_advantage=BASE_ELO_CONFIG.home_advantage,
        season_reversion_fraction=BASE_ELO_CONFIG.season_reversion_fraction,
        draw_margin=best_draw_margin,
    )
    elo_preds_by_id = {p.match_id: {"home": p.p_home, "draw": p.p_draw, "away": p.p_away} for p in run_elo_over_matches(elo_inputs, elo_config)}

    poisson_inputs = [
        PoissonMatchInput(m["match_id"], m["season"], date.fromisoformat(m["match_date"]), m["competition_code"],
                           m["home_team_normalised"], m["away_team_normalised"],
                           *goals_by_match_id[m["match_id"]], m["full_time_result"])
        for m in matches
    ]
    poisson_preds_by_id = {p.match_id: {"home": p.p_home, "draw": p.p_draw, "away": p.p_away} for p in run_poisson_over_matches(poisson_inputs, POISSON_CONFIG)}

    # --- Calibrate blend weights on TRAINING data only ---
    train_ids = {m["match_id"] for m in matches if m["season"] in TRAINING_SEASONS}
    train_common_ids = [
        m["match_id"] for m in matches
        if m["match_id"] in train_ids
        and m["eligible_consensus_model"] == "True"
        and m["match_id"] in closing_consensus
    ]
    train_actuals = [RESULT_TO_OUTCOME[matches_by_id[mid]["full_time_result"]] for mid in train_common_ids]
    train_market = [market_dict_for(closing_consensus[mid]) for mid in train_common_ids]
    train_elo = [elo_preds_by_id[mid] for mid in train_common_ids]
    train_poisson = [poisson_preds_by_id[mid] for mid in train_common_ids]
    train_components = {"market": train_market, "elo": train_elo, "poisson": train_poisson}

    blend_weights = {}
    for combo_name, component_names in BLEND_COMBOS:
        sub_components = {name: train_components[name] for name in component_names}
        blend_weights[combo_name] = calibrate_blend_weights(sub_components, train_actuals, step=BLEND_STEP)
    print(f"Calibrated draw_margin: {best_draw_margin}")
    print("Calibrated blend weights:", json.dumps({name: bw.weights for name, bw in blend_weights.items()}, indent=2))

    # --- Score every candidate ONCE on the 2024/25 common sample ---
    eval_matches = [m for m in matches if m["season"] == SEALED_HOLDOUT_SEASON]
    candidate_names = ["naive", "elo", "poisson"] + [name for name, _ in BLEND_COMBOS]
    pooled_preds: dict[str, list[dict]] = {name: [] for name in candidate_names}
    pooled_market_preds: list[dict] = []
    pooled_actuals: list[str] = []
    pooled_dates: list[str] = []

    for m in eval_matches:
        match_id = m["match_id"]
        if not (m["eligible_consensus_model"] == "True" and match_id in closing_consensus):
            continue
        actual = RESULT_TO_OUTCOME[m["full_time_result"]]
        naive_p = naive_preds_by_id[match_id]
        elo_p = elo_preds_by_id[match_id]
        poisson_p = poisson_preds_by_id[match_id]
        market_p = market_dict_for(closing_consensus[match_id])
        components_here = {"market": market_p, "elo": elo_p, "poisson": poisson_p}

        pooled_preds["naive"].append(naive_p)
        pooled_preds["elo"].append(elo_p)
        pooled_preds["poisson"].append(poisson_p)
        for combo_name, component_names in BLEND_COMBOS:
            sub = {name: components_here[name] for name in component_names}
            blended = blend_probabilities(sub, blend_weights[combo_name])
            pooled_preds[combo_name].append(blended)

        pooled_market_preds.append(market_p)
        pooled_actuals.append(actual)
        pooled_dates.append(m["match_date"])

    n_common = len(pooled_actuals)
    print(f"Holdout common sample scored: N={n_common}")

    pooled_metrics = {
        "market": {
            "log_loss": multiclass_log_loss(pooled_market_preds, pooled_actuals),
            "brier": multiclass_brier_score(pooled_market_preds, pooled_actuals),
        }
    }
    for name in candidate_names:
        pooled_metrics[name] = {
            "log_loss": multiclass_log_loss(pooled_preds[name], pooled_actuals),
            "brier": multiclass_brier_score(pooled_preds[name], pooled_actuals),
        }

    # --- Paired bootstrap CIs vs market for every non-market candidate ---
    bootstrap_results = {}
    for name in candidate_names:
        bootstrap_results[name] = {}
        for metric in ("log_loss", "brier"):
            for method in ("match_level", "block_by_date"):
                result = paired_bootstrap_delta(
                    pooled_preds[name], pooled_market_preds, pooled_actuals, metric=metric,
                    dates=pooled_dates, method=method, n_resamples=2000, seed=42,
                )
                bootstrap_results[name][f"{metric}_{method}"] = asdict(result)

    # --- Raw calibration diagnostics ---
    calibration_results = {}
    calib_source_preds = dict(pooled_preds)
    calib_source_preds["market"] = pooled_market_preds
    for name in CALIBRATION_MODELS:
        calibration_results[name] = {}
        for outcome in ("home", "draw", "away"):
            report = compute_outcome_calibration(calib_source_preds[name], pooled_actuals, outcome=outcome, n_bins=CALIBRATION_N_BINS)
            calibration_results[name][outcome] = {
                "ece": report.expected_calibration_error,
                "bins": [asdict(b) for b in report.bins],
            }

    # --- Apply the frozen verdict rubric mechanically ---
    non_market_candidates = [name for name in candidate_names]
    best_candidate = min(non_market_candidates, key=lambda name: pooled_metrics[name]["log_loss"])
    best_delta = pooled_metrics[best_candidate]["log_loss"] - pooled_metrics["market"]["log_loss"]
    best_ci = bootstrap_results[best_candidate]["log_loss_block_by_date"]
    verdict = apply_verdict_rubric(best_candidate, best_delta, best_ci["ci_lower"], best_ci["ci_upper"])

    summary = {
        "checkpoint": "Stage 3B Checkpoint 6 -- sealed 2024/25 holdout evaluation",
        "data_version": data_freeze_record["data_version"],
        "protocol_document_sha256": protocol_freeze_record["protocol_document_sha256"],
        "holdout_season": SEALED_HOLDOUT_SEASON,
        "training_seasons": TRAINING_SEASONS,
        "holdout_fold_id": holdout_fold.fold_id,
        "common_sample_n": n_common,
        "calibrated_draw_margin": best_draw_margin,
        "calibrated_blend_weights": {name: bw.weights for name, bw in blend_weights.items()},
        "pooled_metrics": pooled_metrics,
        "delta_convention": "delta = candidate_metric - market_metric; negative means candidate beats market",
        "bootstrap_n_resamples": 2000,
        "bootstrap_seed": 42,
        "bootstrap_results": bootstrap_results,
        "calibration_n_bins": CALIBRATION_N_BINS,
        "calibration_results": calibration_results,
        "best_non_market_candidate": best_candidate,
        "best_candidate_log_loss_delta": best_delta,
        "best_candidate_block_by_date_ci": [best_ci["ci_lower"], best_ci["ci_upper"]],
        "verdict": verdict,
    }

    interim_dir = REPO_ROOT / "data" / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)
    with open(interim_dir / "stage_3b_checkpoint6_holdout_metrics.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps({k: v for k, v in summary.items() if k not in ("bootstrap_results", "calibration_results")}, indent=2))
    print(f"\nVERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
