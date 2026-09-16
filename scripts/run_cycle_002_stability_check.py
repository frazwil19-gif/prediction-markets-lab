"""Football Cycle 2 -- stability check for discovery-slice CANDIDATES
(part of step F, run immediately after run_cycle_002_discovery_scan.py).

IMPORTANT LABELLING RULE, per research/cycles/CYCLE_003_FOOTBALL/
CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md (step E, frozen): this script
runs against the 2023/24-2024/25 slice, which Cycle 1's Stage 3B
already touched in aggregate (see that document). This is NOT a blind
out-of-sample test. Its only purpose is to check whether a candidate's
SIGN and rough magnitude persist outside the discovery slice. Nothing
here may be described as "out-of-sample," "holdout," or "validated,"
and no candidate is promoted past CANDIDATE status on the strength of
this check alone (rule enforced by convention here, not by code --
this script only measures and reports).

Only the three checks that reached CANDIDATE status in the discovery
scan are re-run here, on the SAME pre-declared definitions (same price
bands via quintile/quartile of THIS slice, same settlement logic, same
minimum-n gate) -- nothing is re-tuned to fit this slice:

  D4. SOT differential incremental info (five price quintiles).
  D8. Competition-specific 1X2 calibration (E0 / E1 / SC0).
  D9. Dominant-Side Mispricing: AH cover calibration, extreme
      favourites (top quartile) vs the rest.
"""

from __future__ import annotations

import json
from pathlib import Path

from run_cycle_002_discovery_scan import (
    MIN_SUBGROUP_N,
    PROCESSED_ROOT,
    _f,
    _settle_asian_handicap_home,
    bootstrap_ci_mean_diff,
    summarise_calibration,
)
import csv

STABILITY_SEASONS = {"2023_24", "2024_25"}


def load_stability_rows() -> list[dict]:
    with open(PROCESSED_ROOT / "cycle_002_discovery_features.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["season"] in STABILITY_SEASONS]


def check_d4(rows: list[dict]) -> dict:
    d4_rows = []
    for r in rows:
        p = _f(r["market_1x2_opening_home_probability"])
        sot_h = _f(r["home_team_overall_last10_avg_sot_for"])
        sot_a = _f(r["away_team_overall_last10_avg_sot_for"])
        if p is None or sot_h is None or sot_a is None:
            continue
        d4_rows.append({"p": p, "sot_diff": sot_h - sot_a, "home_win": r["outcome_full_time_result"] == "H"})
    d4_rows.sort(key=lambda r: r["p"])
    n = len(d4_rows)
    q_size = n // 5
    out = {}
    for q in range(5):
        start, end = q * q_size, (q + 1) * q_size if q < 4 else n
        band = d4_rows[start:end]
        if len(band) < MIN_SUBGROUP_N:
            out[f"price_quintile_{q}"] = {"n": len(band), "status": "insufficient_n"}
            continue
        band_sorted = sorted(band, key=lambda r: r["sot_diff"])
        half = len(band_sorted) // 2
        low_sot, high_sot = band_sorted[:half], band_sorted[half:]
        ci = bootstrap_ci_mean_diff(
            [1.0 if r["home_win"] else 0.0 for r in high_sot],
            [1.0 if r["home_win"] else 0.0 for r in low_sot],
        )
        out[f"price_quintile_{q}"] = {
            "n": len(band),
            "diff_high_minus_low": round(ci["point_estimate"], 4),
            "diff_ci_95": [round(ci["ci_lower"], 4), round(ci["ci_upper"], 4)],
        }
    return out


def check_d8(rows: list[dict]) -> dict:
    out = {}
    for comp in ("E0", "E1", "SC0"):
        comp_rows = [r for r in rows if r["competition_code"] == comp and _f(r["market_1x2_opening_home_probability"]) is not None]
        if len(comp_rows) < MIN_SUBGROUP_N:
            out[comp] = {"n": len(comp_rows), "status": "insufficient_n"}
            continue
        predicted = [_f(r["market_1x2_opening_home_probability"]) for r in comp_rows]
        actual = [r["outcome_full_time_result"] == "H" for r in comp_rows]
        c = summarise_calibration(predicted, actual, n_bins=5)
        out[comp] = {"n": c["n"], "ece": round(c["ece"], 4)}
    return out


def check_d9(rows: list[dict]) -> dict:
    d9_rows = []
    for r in rows:
        hp = _f(r["market_1x2_opening_home_probability"])
        ap = _f(r["market_1x2_opening_away_probability"])
        ah_line = _f(r["market_ah_opening_line"])
        ah_home_p = _f(r["market_ah_opening_source_avg_home_probability"])
        hg = r["outcome_full_time_home_goals"]
        ag = r["outcome_full_time_away_goals"]
        if None in (hp, ap, ah_line, ah_home_p) or hg in (None, "") or ag in (None, ""):
            continue
        favourite_p = max(hp, ap)
        margin = int(float(hg)) - int(float(ag))
        home_result_fraction = _settle_asian_handicap_home(margin, ah_line)
        d9_rows.append({"favourite_p": favourite_p, "home_result_fraction": home_result_fraction, "ah_home_p": ah_home_p})

    d9_rows.sort(key=lambda r: r["favourite_p"])
    n = len(d9_rows)
    out: dict = {"n_total_ah_settled": n, "n_pushes": sum(1 for r in d9_rows if r["home_result_fraction"] == 0.5)}
    if n < MIN_SUBGROUP_N * 2:
        return out
    extreme_cut = n // 4
    extreme = d9_rows[-extreme_cut:]
    rest = d9_rows[: n - extreme_cut]
    for label, group in (("extreme_favourite_top_quartile", extreme), ("non_extreme_rest", rest)):
        clean = [r for r in group if r["home_result_fraction"] in (0.0, 1.0)]
        if len(clean) < MIN_SUBGROUP_N:
            out[label] = {"n": len(clean), "status": "insufficient_n"}
            continue
        predicted = [r["ah_home_p"] for r in clean]
        actual = [r["home_result_fraction"] == 1.0 for r in clean]
        c = summarise_calibration(predicted, actual, n_bins=5)
        out[label] = {
            "n": c["n"],
            "ece_ah_home_cover": round(c["ece"], 4),
            "mean_favourite_probability": round(sum(r["favourite_p"] for r in group) / len(group), 4),
        }
    return out


def main() -> int:
    rows = load_stability_rows()
    results = {
        "label": "STABILITY CHECK ONLY -- NOT out-of-sample, NOT a holdout, NOT a validation test. "
                  "See CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md.",
        "stability_slice_n": len(rows),
        "seasons": sorted(STABILITY_SEASONS),
        "D4_sot_differential_incremental_info": check_d4(rows),
        "D8_competition_specific_calibration": check_d8(rows),
        "D9_dominant_side_mispricing_locked_family": check_d9(rows),
    }
    out_path = PROCESSED_ROOT / "cycle_002_stability_check_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"stability_slice_n": results["stability_slice_n"]}, indent=2))
    print(f"Full results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
