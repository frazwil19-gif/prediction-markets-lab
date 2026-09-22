"""Outcome Discovery & Winner/Loser Prediction analysis -- orchestration/I/O only.

Research-direction correction (2026-09-22, second directive of the day): reframe the primary
research question as outcome-prediction/calibration first, betting-value second. See
research/outcome_discovery/DATASET_AUDIT.md for the full provenance discussion.

Reuses rather than refits:
 - Gate 1's chronological walk-forward OOS predictions
   (research/probability_model_v2/per_match_predictions_gate1_reproduction.csv) as Model A
   (market), Model B (fundamentals/historical-only), Model C (market+fundamentals), plus the
   existing Elo+Poisson blend and calibrated ensemble. These were already fit chronologically,
   walk-forward, leakage-safe, and published (Gate 1, 2026-09-18) -- refitting them here would
   repeat exhausted research. This script performs new analyses on those existing predictions.
 - Cycle 2's discovery features (data/processed/football/cycle_002_discovery_features.csv) for
   pre-match engineered variables (Elo gap, rolling shots/SOT/corners/cards diffs, points-per-game
   diffs) needed for winner/loser and conditional-market analysis. This file covers 2020/21-2024/25
   only; the 2025/26 sealed-OOS season is not in it -- so the additional feature join is
   unavailable for 2025/26 candidates. This is a stated scope limit: 2025/26 still has full model
   probabilities and realised outcomes via the predictions file, so all probability/calibration/
   top-pick analysis remains complete across all 6 seasons; only the deeper feature-level
   winner/loser mining is restricted to 2020/21-2024/25 (see FEATURE_STABILITY.csv).

Pure computation lives in
src/prediction_markets_lab/research/outcome_discovery_analysis.py (unit-tested separately).
This script only loads CSVs, builds the candidate dataset, calls that module, and writes outputs
to research/outcome_discovery/. No production file is read or written.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.research.outcome_discovery_analysis import (  # noqa: E402
    DISCOVERY_SEASONS,
    HOLDOUT_SEASONS,
    MODEL_PREFIXES,
    VALIDATION_SEASONS,
    ALL_SEASONS_ORDER,
    SIGNED_FEATURES,
    build_candidates,
    conditional_market_analysis,
    draw_analysis,
    favourite_analysis,
    feature_stability,
    partition_season,
    probability_bands_report,
    top_pick_accuracy,
    underdog_analysis,
    winner_loser_table,
)

PRED_CSV = REPO_ROOT / "research/probability_model_v2/per_match_predictions_gate1_reproduction.csv"
FEAT_CSV = REPO_ROOT / "data/processed/football/cycle_002_discovery_features.csv"
OUT_DIR = REPO_ROOT / "research/outcome_discovery"


def _f(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def load_predictions():
    with open(PRED_CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    matches = {}
    for row in rows:
        mid = row["match_id"]
        probs = {}
        for model_key, prefix in MODEL_PREFIXES.items():
            probs[model_key] = {
                "home": _f(row[f"{prefix}_home"]),
                "draw": _f(row[f"{prefix}_draw"]),
                "away": _f(row[f"{prefix}_away"]),
            }
        matches[mid] = {
            "match_id": mid,
            "competition_code": row["competition_code"],
            "season": row["season"],
            "outcome": row["outcome"],
            "probs": probs,
        }
    return matches


def load_features():
    with open(FEAT_CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    feats = {}
    for row in rows:
        mid = row["match_id"]
        h_sot_for = _f(row["home_team_overall_last10_avg_sot_for"])
        a_sot_for = _f(row["away_team_overall_last10_avg_sot_for"])
        h_sot_against = _f(row["home_team_overall_last10_avg_sot_against"])
        a_sot_against = _f(row["away_team_overall_last10_avg_sot_against"])
        h_corners_for = _f(row["home_team_overall_last10_avg_corners_for"])
        a_corners_for = _f(row["away_team_overall_last10_avg_corners_for"])
        h_cards_for = _f(row["home_team_overall_last10_avg_cards_for"])
        a_cards_for = _f(row["away_team_overall_last10_avg_cards_for"])
        feats[mid] = {
            "elo_gap": _f(row["elo_rating_gap_incl_home_advantage"]),
            "diff_goals_for_last10": _f(row["diff_avg_goals_for_last10"]),
            "diff_shots_for_last10": _f(row["diff_avg_shots_for_last10"]),
            "diff_points_per_game_last10": _f(row["diff_points_per_game_last10"]),
            "diff_goals_for_last5": _f(row["diff_avg_goals_for_last5"]),
            "diff_shots_for_last5": _f(row["diff_avg_shots_for_last5"]),
            "diff_points_per_game_last5": _f(row["diff_points_per_game_last5"]),
            "diff_sot_for_last10": (h_sot_for - a_sot_for if h_sot_for is not None and a_sot_for is not None else None),
            "diff_sot_against_last10": (h_sot_against - a_sot_against if h_sot_against is not None and a_sot_against is not None else None),
            "diff_corners_for_last10": (h_corners_for - a_corners_for if h_corners_for is not None and a_corners_for is not None else None),
            "diff_cards_for_last10": (h_cards_for - a_cards_for if h_cards_for is not None and a_cards_for is not None else None),
        }
    return feats


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matches = load_predictions()
    feats = load_features()
    candidates = build_candidates(matches, feats)

    n_matches = len(matches)
    n_candidates = len(candidates)
    n_winners = sum(1 for c in candidates if c["target"] == 1)
    n_losers = n_candidates - n_winners
    n_by_partition = defaultdict(int)
    for c in candidates:
        n_by_partition[partition_season(c["season"])] += 1

    wl_discovery = winner_loser_table(candidates, SIGNED_FEATURES, DISCOVERY_SEASONS)
    write_csv(OUT_DIR / "WINNER_LOSER_ANALYSIS.csv", wl_discovery, list(wl_discovery[0].keys()))

    fav_rows, n_fav_won, n_fav_lost = favourite_analysis(matches, feats)
    write_csv(OUT_DIR / "FAVOURITE_WIN_LOSS_ANALYSIS.csv", fav_rows, list(fav_rows[0].keys()))

    dog_rows, n_dog_won, n_dog_lost = underdog_analysis(matches, feats)
    write_csv(OUT_DIR / "UNDERDOG_ANALYSIS.csv", dog_rows, list(dog_rows[0].keys()))

    draw_rows = draw_analysis(candidates, set(ALL_SEASONS_ORDER))
    write_csv(OUT_DIR / "DRAW_ANALYSIS.csv", draw_rows, list(draw_rows[0].keys()))

    cond_rows = conditional_market_analysis(candidates, DISCOVERY_SEASONS, 0.50, 0.65)
    cond_rows_validation = conditional_market_analysis(candidates, VALIDATION_SEASONS, 0.50, 0.65)
    cond_rows_holdout = conditional_market_analysis(candidates, HOLDOUT_SEASONS, 0.50, 0.65)
    write_csv(OUT_DIR / "CONDITIONAL_MARKET_ANALYSIS.csv", cond_rows, list(cond_rows[0].keys()))

    stability_rows = feature_stability(candidates)
    write_csv(OUT_DIR / "FEATURE_STABILITY.csv", stability_rows, list(stability_rows[0].keys()))

    bands_market = probability_bands_report(candidates, "market")
    bands_fundamentals = probability_bands_report(candidates, "fundamentals")
    all_bands = bands_market + bands_fundamentals
    write_csv(OUT_DIR / "PROBABILITY_BANDS.csv", all_bands, list(all_bands[0].keys()))
    write_csv(OUT_DIR / "CALIBRATION.csv", all_bands, list(all_bands[0].keys()))

    top_pick_all = {mk: top_pick_accuracy(matches, mk) for mk in MODEL_PREFIXES}
    top_pick_holdout = {mk: top_pick_accuracy(matches, mk, HOLDOUT_SEASONS) for mk in MODEL_PREFIXES}
    top_pick_discovery = {mk: top_pick_accuracy(matches, mk, DISCOVERY_SEASONS) for mk in MODEL_PREFIXES}
    top_pick_validation = {mk: top_pick_accuracy(matches, mk, VALIDATION_SEASONS) for mk in MODEL_PREFIXES}

    model_comparison_rows = [
        {
            "model": mk,
            "top_pick_accuracy_pooled": top_pick_all[mk]["accuracy"],
            "top_pick_accuracy_discovery": top_pick_discovery[mk]["accuracy"],
            "top_pick_accuracy_validation": top_pick_validation[mk]["accuracy"],
            "top_pick_accuracy_holdout": top_pick_holdout[mk]["accuracy"],
            "n_matches_pooled": top_pick_all[mk]["n_matches"],
        }
        for mk in MODEL_PREFIXES
    ]
    write_csv(OUT_DIR / "MODEL_COMPARISON.csv", model_comparison_rows, list(model_comparison_rows[0].keys()))

    misses = []
    for m in matches.values():
        probs = m["probs"]["market"]
        if any(v is None for v in probs.values()):
            continue
        pick = max(probs, key=probs.get)
        actual_side = m["outcome"]
        if pick != actual_side:
            misses.append(
                {
                    "match_id": m["match_id"],
                    "competition_code": m["competition_code"],
                    "season": m["season"],
                    "predicted_side": pick,
                    "predicted_probability": round(probs[pick], 4),
                    "actual_outcome": actual_side,
                }
            )
    misses.sort(key=lambda r: r["predicted_probability"], reverse=True)
    top_misses = misses[:20]

    summary = {
        "n_matches": n_matches,
        "n_candidates": n_candidates,
        "n_winners": n_winners,
        "n_losers": n_losers,
        "n_by_partition": dict(n_by_partition),
        "n_favourite_won": n_fav_won,
        "n_favourite_lost": n_fav_lost,
        "n_underdog_won": n_dog_won,
        "n_underdog_lost": n_dog_lost,
        "top_pick_accuracy_pooled": {mk: top_pick_all[mk]["accuracy"] for mk in MODEL_PREFIXES},
        "top_pick_accuracy_by_season_market": top_pick_all["market"]["by_season"],
        "top_pick_by_side_market": top_pick_all["market"]["by_side"],
        "top_pick_by_side_fundamentals": top_pick_all["fundamentals"]["by_side"],
        "n_draw_candidates": sum(1 for c in candidates if c["side"] == "draw"),
        "n_draw_occurred": sum(1 for c in candidates if c["side"] == "draw" and c["target"] == 1),
        "n_stable_features": sum(1 for r in stability_rows if r["verdict"].startswith("STABLE")),
        "n_unstable_features": sum(1 for r in stability_rows if r["verdict"].startswith("UNSTABLE")),
        "top_misses_market": top_misses,
        "conditional_market_band_50_65_discovery": cond_rows,
        "conditional_market_band_50_65_validation": cond_rows_validation,
        "conditional_market_band_50_65_holdout": cond_rows_holdout,
    }
    with open(OUT_DIR / "analysis_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print("n_matches", n_matches)
    print("n_candidates", n_candidates)
    print("n_by_partition", dict(n_by_partition))
    print("top_pick_accuracy (pooled):", {mk: top_pick_all[mk]["accuracy"] for mk in MODEL_PREFIXES})
    print("stable features:", summary["n_stable_features"], "unstable:", summary["n_unstable_features"])
    print("wrote outputs to", OUT_DIR)


if __name__ == "__main__":
    main()
