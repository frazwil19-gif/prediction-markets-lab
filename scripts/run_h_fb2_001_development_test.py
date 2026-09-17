"""H-FB2-001 development test -- Dominant-Side Mispricing (Asian Handicap).

Pre-registered specification (frozen BEFORE this script was run, commit
4757031): research/cycles/CYCLE_003_FOOTBALL/
HYPOTHESIS_PREREGISTRATION_H-FB2-001_H-FB2-002.md, section 3.

Runs on the FULL existing development corpus (2020/21-2024/25, both the
former discovery slice and stability slice combined -- no genuine sealed
OOS survives inside this corpus per CYCLE_002_CHRONOLOGICAL_SPLIT_
DECISION.md, so the combined corpus is used for this development-phase
test). 2025/26 data is not read, referenced, or required by this script.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from prediction_markets_lab.performance.calibration import compute_calibration_bins
from prediction_markets_lab.research.development_verdict import (
    DevelopmentVerdictInput,
    classify_development_result,
)
from prediction_markets_lab.research.football_cycle2_development import (
    FavouritePerspective,
    bootstrap_ci_mean,
    favourite_perspective,
    settle_asian_handicap_home,
    signed_ah_pricing_residual,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_ROOT = REPO_ROOT / "data" / "processed" / "football"
SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24", "2024_25"]
COMPETITIONS = ["E0", "E1", "SC0"]
MIN_SUBGROUP_N = 100


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_rows() -> list[dict]:
    with open(PROCESSED_ROOT / "cycle_002_discovery_features.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_eligible(rows: list[dict]) -> list[dict]:
    eligible = []
    for r in rows:
        hp = _f(r["market_1x2_opening_home_probability"])
        ap = _f(r["market_1x2_opening_away_probability"])
        ah_line = _f(r["market_ah_opening_line"])
        ah_home_p = _f(r["market_ah_opening_source_avg_home_probability"])
        ah_away_p = _f(r["market_ah_opening_source_avg_away_probability"])
        hg = r["outcome_full_time_home_goals"]
        ag = r["outcome_full_time_away_goals"]
        if None in (hp, ap, ah_line, ah_home_p, ah_away_p) or hg in (None, "") or ag in (None, ""):
            continue
        favourite_side = "home" if hp > ap else "away"
        favourite_p = max(hp, ap)
        margin = int(float(hg)) - int(float(ag))
        home_result_fraction = settle_asian_handicap_home(margin, ah_line)
        fp = favourite_perspective(favourite_side, ah_home_p, ah_away_p, home_result_fraction)
        eligible.append({
            "season": r["season"],
            "competition_code": r["competition_code"],
            "favourite_p": favourite_p,
            "favourite_side": favourite_side,
            "fp": fp,
            "ah_home_p": ah_home_p,
            "home_result_fraction": home_result_fraction,
        })
    return eligible


def split_extreme(eligible: list[dict], top_fraction: float) -> tuple[list[dict], list[dict]]:
    ordered = sorted(eligible, key=lambda r: r["favourite_p"])
    n = len(ordered)
    cut = int(round(n * (1 - top_fraction)))
    return ordered[cut:], ordered[:cut]  # extreme, rest


def residual_for(group: list[dict]) -> dict:
    return signed_ah_pricing_residual([g["fp"] for g in group])


def main() -> int:
    rows = load_rows()
    raw_eligible = build_eligible(rows)

    results: dict = {"eligible_n": len(raw_eligible), "total_corpus_n": len(rows)}

    # ---- Primary: extreme-favourite top quartile signed residual ----
    extreme_q, rest_q = split_extreme(raw_eligible, 0.25)
    primary = residual_for(extreme_q)
    secondary_rest = residual_for(rest_q)
    results["primary_extreme_favourite_top_quartile"] = primary
    results["secondary_non_extreme_rest"] = secondary_rest

    # ---- Secondary: unsigned ECE, home-cover perspective (continuity with discovery) ----
    def unsigned_ece(group):
        clean = [g for g in group if g["home_result_fraction"] in (0.0, 1.0)]
        if len(clean) < MIN_SUBGROUP_N:
            return {"n": len(clean), "status": "insufficient_n"}
        predicted = [g["ah_home_p"] for g in clean]
        actual = [g["home_result_fraction"] == 1.0 for g in clean]
        bins = compute_calibration_bins(predicted, actual, n_bins=5)
        ece = sum(b.n * b.gap for b in bins) / sum(b.n for b in bins)
        return {"n": len(clean), "ece": round(ece, 4)}

    results["secondary_unsigned_ece_extreme"] = unsigned_ece(extreme_q)
    results["secondary_unsigned_ece_rest"] = unsigned_ece(rest_q)

    # ---- Robustness: top quintile (20%) cut instead of quartile (25%) ----
    extreme_quintile, _ = split_extreme(raw_eligible, 0.20)
    results["robustness_top_quintile_cut"] = residual_for(extreme_quintile)

    # ---- Season-by-season breakdown (extreme-favourite quartile group) ----
    season_out = {}
    n_seasons_same_sign = 0
    n_seasons_tested = 0
    n_floor_met_every_season = True
    overall_sign = 1 if primary.get("mean_signed_residual", 0) >= 0 else -1
    for season in SEASONS:
        group = [g for g in extreme_q if g["season"] == season]
        r = residual_for(group)
        season_out[season] = r
        if r.get("n", 0) > 0:
            n_seasons_tested += 1
            season_sign = 1 if r.get("mean_signed_residual", 0) >= 0 else -1
            if season_sign == overall_sign:
                n_seasons_same_sign += 1
            if r.get("n", 0) < MIN_SUBGROUP_N:
                n_floor_met_every_season = False
    results["season_breakdown_extreme_favourite_quartile"] = season_out

    # ---- Competition-by-competition breakdown (extreme-favourite quartile group) ----
    comp_out = {}
    for comp in COMPETITIONS:
        group = [g for g in extreme_q if g["competition_code"] == comp]
        comp_out[comp] = residual_for(group)
    results["competition_breakdown_extreme_favourite_quartile"] = comp_out

    # ---- Single-competition independence: exclude each competition in turn ----
    single_comp_independent = True
    exclusion_out = {}
    for comp in COMPETITIONS:
        group = [g for g in extreme_q if g["competition_code"] != comp]
        r = residual_for(group)
        exclusion_out[f"excluding_{comp}"] = r
        if r.get("n", 0) > 0:
            sign_excl = 1 if r.get("mean_signed_residual", 0) >= 0 else -1
            if sign_excl != overall_sign:
                single_comp_independent = False
    results["single_competition_exclusion_check"] = exclusion_out
    results["single_competition_independent"] = single_comp_independent

    # ---- Mechanical DEVELOPMENT-* verdict ----
    ci_lower, ci_upper = primary["ci_95"]
    verdict_input = DevelopmentVerdictInput(
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        point_estimate=primary["mean_signed_residual"],
        one_sided_positive_required=False,
        n_seasons_same_sign=n_seasons_same_sign,
        n_seasons_tested=n_seasons_tested,
        n_floor_met_in_every_reported_season=n_floor_met_every_season,
        single_competition_independent=single_comp_independent,
    )
    verdict = classify_development_result(verdict_input)
    results["verdict"] = {"verdict": verdict.verdict, "reason": verdict.reason}
    results["verdict_inputs"] = {
        "n_seasons_same_sign": n_seasons_same_sign,
        "n_seasons_tested": n_seasons_tested,
        "n_floor_met_in_every_reported_season": n_floor_met_every_season,
        "single_competition_independent": single_comp_independent,
    }

    out_path = PROCESSED_ROOT / "h_fb2_001_development_test_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({
        "eligible_n": results["eligible_n"],
        "primary": primary,
        "verdict": results["verdict"],
    }, indent=2))
    print(f"Full results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
