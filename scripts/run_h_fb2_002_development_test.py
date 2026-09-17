"""H-FB2-002 development test -- SOT Differential x Extreme-Favourite Price Band.

Pre-registered specification (frozen BEFORE this script was run, commit
4757031): research/cycles/CYCLE_003_FOOTBALL/
HYPOTHESIS_PREREGISTRATION_H-FB2-001_H-FB2-002.md, section 4.

Runs on the FULL existing development corpus (2020/21-2024/25, discovery
and stability slices combined, per the same rationale as H-FB2-001's
script). 2025/26 data is not read, referenced, or required.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from prediction_markets_lab.research.development_verdict import (
    DevelopmentVerdictInput,
    classify_development_result,
)
from prediction_markets_lab.research.football_cycle2_development import (
    bootstrap_ci_mean_diff,
    pearson_correlation,
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


def build_eligible(rows: list[dict], sot_window: str = "10") -> list[dict]:
    """sot_window: "10" (frozen primary) or "5" (robustness check, item I)."""
    field_h = f"home_team_overall_last{sot_window}_avg_sot_for"
    field_a = f"away_team_overall_last{sot_window}_avg_sot_for"
    eligible = []
    for r in rows:
        p = _f(r["market_1x2_opening_home_probability"])
        sot_h = _f(r[field_h])
        sot_a = _f(r[field_a])
        if p is None or sot_h is None or sot_a is None:
            continue
        eligible.append({
            "season": r["season"],
            "competition_code": r["competition_code"],
            "p": p,
            "sot_diff": sot_h - sot_a,
            "home_win": r["outcome_full_time_result"] == "H",
        })
    return eligible


def top_price_band(eligible: list[dict], n_bands: int, top_index: int) -> list[dict]:
    """Sort ascending by opening home-win probability, split into n_bands
    equal-count bands, return the band at top_index (0-indexed, highest
    band = n_bands - 1)."""
    ordered = sorted(eligible, key=lambda r: r["p"])
    n = len(ordered)
    band_size = n // n_bands
    start = top_index * band_size
    end = (top_index + 1) * band_size if top_index < n_bands - 1 else n
    return ordered[start:end]


def median_split_diff(group: list[dict]) -> dict:
    if len(group) < MIN_SUBGROUP_N:
        return {"n": len(group), "status": "insufficient_n"}
    ordered = sorted(group, key=lambda r: r["sot_diff"])
    half = len(ordered) // 2
    low, high = ordered[:half], ordered[half:]
    ci = bootstrap_ci_mean_diff(
        [1.0 if r["home_win"] else 0.0 for r in high],
        [1.0 if r["home_win"] else 0.0 for r in low],
    )
    return {
        "n": len(group),
        "high_sot_diff_home_win_rate": sum(1.0 if r["home_win"] else 0.0 for r in high) / len(high),
        "low_sot_diff_home_win_rate": sum(1.0 if r["home_win"] else 0.0 for r in low) / len(low),
        "diff_high_minus_low": ci["point_estimate"],
        "ci_95": [ci["ci_lower"], ci["ci_upper"]],
    }


def main() -> int:
    rows = load_rows()
    eligible = build_eligible(rows, sot_window="10")
    results: dict = {"eligible_n": len(eligible), "total_corpus_n": len(rows)}

    # ---- Primary: quintile 4 (top 20% by home-win probability), median SOT split ----
    quintile4 = top_price_band(eligible, n_bands=5, top_index=4)
    primary = median_split_diff(quintile4)
    results["primary_price_quintile_4"] = primary

    # ---- All five quintiles reported for context (not primary) ----
    all_quintiles = {}
    for q in range(5):
        band = top_price_band(eligible, n_bands=5, top_index=q)
        all_quintiles[f"quintile_{q}"] = median_split_diff(band)
    results["all_quintiles_for_context"] = all_quintiles

    # ---- Secondary diagnostic: Pearson correlation of sot_diff vs market residual, within quintile 4 ----
    residuals = [(1.0 if r["home_win"] else 0.0) - r["p"] for r in quintile4]
    sot_diffs = [r["sot_diff"] for r in quintile4]
    results["secondary_correlation_sot_diff_vs_market_residual_quintile_4"] = {
        "n": len(quintile4),
        "pearson_r": pearson_correlation(sot_diffs, residuals),
    }

    # ---- Robustness: quartiles (4-way) instead of quintiles (5-way) ----
    top_quartile = top_price_band(eligible, n_bands=4, top_index=3)
    results["robustness_top_quartile_cut"] = median_split_diff(top_quartile)

    # ---- Robustness: last-5 SOT window instead of last-10 ----
    eligible_sot5 = build_eligible(rows, sot_window="5")
    quintile4_sot5 = top_price_band(eligible_sot5, n_bands=5, top_index=4)
    results["robustness_last5_sot_window"] = median_split_diff(quintile4_sot5)

    # ---- Season-by-season breakdown (quintile 4) ----
    season_out = {}
    n_seasons_same_sign = 0
    n_seasons_tested = 0
    n_floor_met_every_season = True
    overall_sign = 1 if primary.get("diff_high_minus_low", 0) >= 0 else -1
    for season in SEASONS:
        group = [r for r in quintile4 if r["season"] == season]
        r_out = median_split_diff(group)
        season_out[season] = r_out
        if len(group) > 0 and "diff_high_minus_low" in r_out:
            n_seasons_tested += 1
            sign = 1 if r_out["diff_high_minus_low"] >= 0 else -1
            if sign == overall_sign:
                n_seasons_same_sign += 1
            if r_out["n"] < MIN_SUBGROUP_N:
                n_floor_met_every_season = False
        elif len(group) > 0:
            # insufficient_n at the season level -- counted as tested but
            # not meeting the floor, and its sign (from the raw rates,
            # even below the formal N floor) still checked for stability.
            n_seasons_tested += 1
            n_floor_met_every_season = False
            if len(group) >= 4:
                ordered = sorted(group, key=lambda r: r["sot_diff"])
                half = len(ordered) // 2
                low, high = ordered[:half], ordered[half:]
                if low and high:
                    diff = (sum(1.0 if r["home_win"] else 0.0 for r in high) / len(high)) - (
                        sum(1.0 if r["home_win"] else 0.0 for r in low) / len(low)
                    )
                    sign = 1 if diff >= 0 else -1
                    if sign == overall_sign:
                        n_seasons_same_sign += 1
    results["season_breakdown_price_quintile_4"] = season_out

    # ---- Competition-by-competition breakdown (quintile 4) ----
    comp_out = {}
    for comp in COMPETITIONS:
        group = [r for r in quintile4 if r["competition_code"] == comp]
        comp_out[comp] = median_split_diff(group)
    results["competition_breakdown_price_quintile_4"] = comp_out

    # ---- Single-competition independence: exclude each competition in turn ----
    single_comp_independent = True
    exclusion_out = {}
    for comp in COMPETITIONS:
        group = [r for r in quintile4 if r["competition_code"] != comp]
        r_out = median_split_diff(group)
        exclusion_out[f"excluding_{comp}"] = r_out
        if "diff_high_minus_low" in r_out:
            sign = 1 if r_out["diff_high_minus_low"] >= 0 else -1
            if sign != overall_sign:
                single_comp_independent = False
    results["single_competition_exclusion_check"] = exclusion_out
    results["single_competition_independent"] = single_comp_independent

    # ---- Mechanical DEVELOPMENT-* verdict ----
    ci_lower, ci_upper = primary["ci_95"]
    verdict_input = DevelopmentVerdictInput(
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        point_estimate=primary["diff_high_minus_low"],
        one_sided_positive_required=True,
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

    out_path = PROCESSED_ROOT / "h_fb2_002_development_test_results.json"
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
