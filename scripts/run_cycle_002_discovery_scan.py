"""Football Cycle 2 -- broad, bounded, pre-declared behavioural discovery
scan (operator's step F, Football Cycle 2 direction-change execution
plan, 2026-09-16).

PRE-DECLARED CHECK LIST (fixed before this script was run against real
data; per the operator's statistical-discipline instruction, this list
is not expanded, re-binned, or re-run with variant thresholds after
seeing results -- a check that comes back null is reported as null):

  D1. Favourite-longshot bias, 1X2 (opening prices).
  D2. Favourite-longshot bias, Over/Under 2.5 (opening prices).
  D3. Does market calibration differ across Elo-gap magnitude terciles?
  D4. Does rolling SOT differential add information beyond the market's
      own opening price (within price-band control)?
  D5. Recent-form/underlying-quality divergence vs market movement
      ("overreaction to recent goals" proxy).
  D6. Does opening-to-closing market movement predict the outcome
      beyond the closing price alone?
  D7. Home-favourite vs away-favourite calibration asymmetry.
  D8. Competition-specific calibration differences (E0 / E1 / SC0).
  D9. Dominant-Side Mispricing (LOCKED pre-registered family): does the
      market price the Asian Handicap correctly for the most dominant
      1X2 favourites specifically, vs moderate favourites?

Scope discipline, per research/cycles/CYCLE_003_FOOTBALL/
CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md (step E, frozen before this
script was written): every check below runs ONLY on the discovery
slice (2020/21-2022/23, competition E0/E1/SC0, N=3,480). The
2023/24-2024/25 slice is never touched by this script -- the stability
check against it is a separate, later step, done only for whichever
candidates survive here.

Statistical discipline: every subgroup requires >= MIN_SUBGROUP_N
matches; every rate/mean comparison reports a percentage-point or
probability-point effect size with a bootstrap 95% CI (seeded,
percentile method, same style as probability/uncertainty.py); no
threshold is tuned post hoc to make a result significant; every check
either runs to completion and is reported, or is explicitly marked
NULL/negative -- no check is discarded silently.

Outcome-of-the-match statistics (goals, shots, SOT, etc.) are used
here only as PRE-MATCH rolling features (already lagged in step D) or
as the settlement inputs for actual results -- never as same-match
predictors, consistent with every earlier step in this cycle.
"""

from __future__ import annotations

import csv
import json
import random
import statistics
from pathlib import Path

from prediction_markets_lab.performance.calibration import compute_calibration_bins

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_ROOT = REPO_ROOT / "data" / "processed" / "football"
DISCOVERY_SEASONS = {"2020_21", "2021_22", "2022_23"}

MIN_SUBGROUP_N = 100
BOOTSTRAP_N_RESAMPLES = 2000
BOOTSTRAP_SEED = 42


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_discovery_rows() -> list[dict]:
    with open(PROCESSED_ROOT / "cycle_002_discovery_features.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["season"] in DISCOVERY_SEASONS]


def bootstrap_ci_mean_diff(group_a: list[float], group_b: list[float], seed: int = BOOTSTRAP_SEED) -> dict:
    """Percentile bootstrap CI for mean(group_a) - mean(group_b), i.i.d. resampling within each group."""
    rng = random.Random(seed)
    point = (sum(group_a) / len(group_a)) - (sum(group_b) / len(group_b))
    deltas = []
    for _ in range(BOOTSTRAP_N_RESAMPLES):
        ra = [rng.choice(group_a) for _ in group_a]
        rb = [rng.choice(group_b) for _ in group_b]
        deltas.append((sum(ra) / len(ra)) - (sum(rb) / len(rb)))
    deltas.sort()
    lo = deltas[int(0.025 * len(deltas))]
    hi = deltas[int(0.975 * len(deltas))]
    return {"point_estimate": point, "ci_lower": lo, "ci_upper": hi, "n_a": len(group_a), "n_b": len(group_b)}


def _settle_half_line_home(margin: int, line: float) -> float:
    """Settle a whole/half Asian Handicap line (a multiple of 0.5) for the
    home side. Returns 1.0 (home covers), 0.0 (away covers), or 0.5
    (push -- possible only on whole-number lines)."""
    adjusted = margin + line
    if adjusted > 0:
        return 1.0
    if adjusted < 0:
        return 0.0
    return 0.5


def _settle_asian_handicap_home(margin: int, line: float) -> float:
    """Settle any Asian Handicap line for the home side, including quarter
    lines (e.g. -0.25, -0.75), which split the stake 50/50 between the two
    neighbouring half-lines (e.g. -0.25 -> average of settling at 0 and at
    -0.5). Returns a fraction in {0.0, 0.25, 0.5, 0.75, 1.0}: 0.5 exactly
    means a genuine push (whole-line only); a quarter-line result of 0.25
    or 0.75 means "half-lost/half-won", a real settlement outcome distinct
    from a push and excluded from the clean win/loss calibration read
    the same way pushes are.
    """
    doubled = line * 4
    is_quarter_line = abs(doubled - round(doubled)) < 1e-9 and round(doubled) % 2 != 0
    if is_quarter_line:
        lo, hi = line - 0.25, line + 0.25
        return (_settle_half_line_home(margin, lo) + _settle_half_line_home(margin, hi)) / 2
    return _settle_half_line_home(margin, line)


def summarise_calibration(predicted: list[float], actual: list[bool], n_bins: int = 10) -> dict:
    bins = compute_calibration_bins(predicted, actual, n_bins=n_bins)
    ece = sum(b.n * b.gap for b in bins) / sum(b.n for b in bins)
    return {
        "n": sum(b.n for b in bins),
        "ece": ece,
        "bins": [
            {
                "n": b.n,
                "mean_predicted": round(b.mean_predicted_probability, 4),
                "observed_frequency": round(b.observed_frequency, 4),
                "gap": round(b.gap, 4),
            }
            for b in bins
        ],
    }


def run() -> dict:
    rows = load_discovery_rows()
    results: dict = {"discovery_slice_n": len(rows), "checks": {}}

    # ---------------- D1: FLB, 1X2 ----------------
    d1_rows = [r for r in rows if _f(r["market_1x2_opening_home_probability"]) is not None]
    predicted = [_f(r["market_1x2_opening_home_probability"]) for r in d1_rows]
    actual = [r["outcome_full_time_result"] == "H" for r in d1_rows]
    calib = summarise_calibration(predicted, actual, n_bins=10)
    # FLB signature: lowest-probability bin observed > predicted (longshots overpriced favourably
    # to bettors i.e. underdogs win MORE than market implies is the classic bias direction... but
    # convention varies -- we report the raw bin gaps with SIGN (observed - predicted) so direction
    # is unambiguous rather than asserted.
    for b in calib["bins"]:
        b["signed_gap"] = round(b["observed_frequency"] - b["mean_predicted"], 4)
    results["checks"]["D1_flb_1x2_home_favourite"] = {
        "description": "Calibration of market 1X2 home-win opening probability across 10 equal-count bins.",
        **calib,
    }

    # ---------------- D2: FLB, Over/Under 2.5 ----------------
    d2_rows = [
        r for r in rows
        if _f(r["market_ou25_opening_source_avg_over_probability"]) is not None
        and r["outcome_full_time_home_goals"] not in (None, "") and r["outcome_full_time_away_goals"] not in (None, "")
    ]
    predicted = [_f(r["market_ou25_opening_source_avg_over_probability"]) for r in d2_rows]
    actual = [
        (int(float(r["outcome_full_time_home_goals"])) + int(float(r["outcome_full_time_away_goals"]))) > 2.5
        for r in d2_rows
    ]
    calib = summarise_calibration(predicted, actual, n_bins=10)
    for b in calib["bins"]:
        b["signed_gap"] = round(b["observed_frequency"] - b["mean_predicted"], 4)
    results["checks"]["D2_flb_over_under_2_5"] = {
        "description": "Calibration of market Over 2.5 opening probability (source Avg) across 10 equal-count bins.",
        **calib,
    }

    # ---------------- D3: Elo-gap magnitude vs calibration ----------------
    gap_rows = [
        r for r in rows
        if _f(r["elo_rating_gap_incl_home_advantage"]) is not None and _f(r["market_1x2_opening_home_probability"]) is not None
    ]
    gaps = sorted(gap_rows, key=lambda r: abs(_f(r["elo_rating_gap_incl_home_advantage"])))
    n = len(gaps)
    tercile_bounds = [n // 3, 2 * n // 3]
    terciles = {
        "low_elo_gap": gaps[: tercile_bounds[0]],
        "mid_elo_gap": gaps[tercile_bounds[0]: tercile_bounds[1]],
        "high_elo_gap": gaps[tercile_bounds[1]:],
    }
    d3_out = {}
    for label, group in terciles.items():
        if len(group) < MIN_SUBGROUP_N:
            d3_out[label] = {"n": len(group), "status": "insufficient_n"}
            continue
        predicted = [_f(r["market_1x2_opening_home_probability"]) for r in group]
        actual = [r["outcome_full_time_result"] == "H" for r in group]
        calib = summarise_calibration(predicted, actual, n_bins=5)
        d3_out[label] = {"n": len(group), "ece": round(calib["ece"], 4)}
    results["checks"]["D3_elo_gap_magnitude_vs_calibration"] = {
        "description": "Market 1X2 home-win calibration (ECE, 5 bins) within Elo-gap-magnitude terciles.",
        "terciles": d3_out,
    }

    # ---------------- D4: SOT differential incremental info, controlling for price band ----------------
    d4_rows = []
    for r in rows:
        p = _f(r["market_1x2_opening_home_probability"])
        sot_h = _f(r["home_team_overall_last10_avg_sot_for"])
        sot_a = _f(r["away_team_overall_last10_avg_sot_for"])
        if p is None or sot_h is None or sot_a is None:
            continue
        d4_rows.append({"p": p, "sot_diff": sot_h - sot_a, "home_win": r["outcome_full_time_result"] == "H"})
    d4_rows.sort(key=lambda r: r["p"])
    n4 = len(d4_rows)
    quintile_size = n4 // 5
    d4_out = {}
    for q in range(5):
        start = q * quintile_size
        end = (q + 1) * quintile_size if q < 4 else n4
        band = d4_rows[start:end]
        if len(band) < MIN_SUBGROUP_N:
            d4_out[f"price_quintile_{q}"] = {"n": len(band), "status": "insufficient_n"}
            continue
        band_sorted = sorted(band, key=lambda r: r["sot_diff"])
        half = len(band_sorted) // 2
        low_sot, high_sot = band_sorted[:half], band_sorted[half:]
        low_rate = sum(1 for r in low_sot if r["home_win"]) / len(low_sot)
        high_rate = sum(1 for r in high_sot if r["home_win"]) / len(high_sot)
        ci = bootstrap_ci_mean_diff(
            [1.0 if r["home_win"] else 0.0 for r in high_sot],
            [1.0 if r["home_win"] else 0.0 for r in low_sot],
        )
        d4_out[f"price_quintile_{q}"] = {
            "n": len(band),
            "mean_market_p_home": round(sum(r["p"] for r in band) / len(band), 4),
            "high_sot_diff_home_win_rate": round(high_rate, 4),
            "low_sot_diff_home_win_rate": round(low_rate, 4),
            "diff_high_minus_low": round(ci["point_estimate"], 4),
            "diff_ci_95": [round(ci["ci_lower"], 4), round(ci["ci_upper"], 4)],
        }
    results["checks"]["D4_sot_differential_incremental_info"] = {
        "description": (
            "Within each opening-price quintile (proxy for 'controlling for the market's own view'), "
            "compare home-win rate for top-half vs bottom-half of rolling-last-10 SOT differential "
            "(home minus away). A nonzero, stable-signed gap would suggest SOT carries information "
            "beyond the market's opening price."
        ),
        "quintiles": d4_out,
    }

    # ---------------- D5: recent-form vs underlying-quality divergence vs market movement ----------------
    d5_rows = []
    for r in rows:
        form5 = _f(r["diff_points_per_game_last5"])
        sot10_h = _f(r["home_team_overall_last10_avg_sot_for"])
        sot10_a = _f(r["away_team_overall_last10_avg_sot_for"])
        movement = _f(r["market_1x2_home_movement_close_minus_open"])
        if form5 is None or sot10_h is None or sot10_a is None or movement is None:
            continue
        d5_rows.append({"form5_diff": form5, "sot10_diff": sot10_h - sot10_a, "movement": movement})

    def _pearson(xs: list[float], ys: list[float]) -> float:
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
        sy = (sum((y - my) ** 2 for y in ys)) ** 0.5
        return cov / (sx * sy) if sx > 0 and sy > 0 else 0.0

    if len(d5_rows) >= MIN_SUBGROUP_N:
        corr_form_movement = _pearson([r["form5_diff"] for r in d5_rows], [r["movement"] for r in d5_rows])
        corr_sot_movement = _pearson([r["sot10_diff"] for r in d5_rows], [r["movement"] for r in d5_rows])
        results["checks"]["D5_recent_form_overreaction_proxy"] = {
            "description": (
                "Correlation of last-5-match points-per-game differential (short-term form) vs "
                "opening-to-closing 1X2 home-probability movement, compared to the same correlation "
                "using last-10-match SOT differential (longer-window underlying quality). A "
                "meaningfully stronger correlation for form-5 than SOT-10 would be consistent with "
                "the market moving more on recent results than on underlying process quality."
            ),
            "n": len(d5_rows),
            "corr_form5_diff_vs_movement": round(corr_form_movement, 4),
            "corr_sot10_diff_vs_movement": round(corr_sot_movement, 4),
        }
    else:
        results["checks"]["D5_recent_form_overreaction_proxy"] = {"status": "insufficient_n", "n": len(d5_rows)}

    # ---------------- D6: does market movement predict outcome beyond closing price? ----------------
    d6_rows = []
    for r in rows:
        close_p = _f(r["market_1x2_closing_home_probability"])
        movement = _f(r["market_1x2_home_movement_close_minus_open"])
        if close_p is None or movement is None:
            continue
        d6_rows.append({"close_p": close_p, "movement": movement, "home_win": r["outcome_full_time_result"] == "H"})
    d6_rows.sort(key=lambda r: r["close_p"])
    n6 = len(d6_rows)
    q_size = n6 // 5
    d6_out = {}
    for q in range(5):
        start, end = q * q_size, (q + 1) * q_size if q < 4 else n6
        band = d6_rows[start:end]
        if len(band) < MIN_SUBGROUP_N:
            d6_out[f"close_price_quintile_{q}"] = {"n": len(band), "status": "insufficient_n"}
            continue
        band_sorted = sorted(band, key=lambda r: r["movement"])
        half = len(band_sorted) // 2
        moved_away, moved_home = band_sorted[:half], band_sorted[half:]
        ci = bootstrap_ci_mean_diff(
            [1.0 if r["home_win"] else 0.0 for r in moved_home],
            [1.0 if r["home_win"] else 0.0 for r in moved_away],
        )
        d6_out[f"close_price_quintile_{q}"] = {
            "n": len(band),
            "home_win_rate_if_moved_toward_home": round(sum(1.0 if r["home_win"] else 0.0 for r in moved_home) / len(moved_home), 4),
            "home_win_rate_if_moved_toward_away": round(sum(1.0 if r["home_win"] else 0.0 for r in moved_away) / len(moved_away), 4),
            "diff": round(ci["point_estimate"], 4),
            "diff_ci_95": [round(ci["ci_lower"], 4), round(ci["ci_upper"], 4)],
        }
    results["checks"]["D6_market_movement_informativeness"] = {
        "description": (
            "Within closing-price quintiles, does having moved toward the home side (opening-to-"
            "closing) predict a higher home win rate than moving toward the away side, i.e. does "
            "movement carry information beyond the closing price snapshot alone?"
        ),
        "quintiles": d6_out,
    }

    # ---------------- D7: home-favourite vs away-favourite calibration asymmetry ----------------
    home_fav_rows, away_fav_rows = [], []
    for r in rows:
        hp = _f(r["market_1x2_opening_home_probability"])
        ap = _f(r["market_1x2_opening_away_probability"])
        if hp is None or ap is None:
            continue
        if hp > ap:
            home_fav_rows.append(r)
        else:
            away_fav_rows.append(r)
    d7_out = {}
    if len(home_fav_rows) >= MIN_SUBGROUP_N:
        predicted = [_f(r["market_1x2_opening_home_probability"]) for r in home_fav_rows]
        actual = [r["outcome_full_time_result"] == "H" for r in home_fav_rows]
        c = summarise_calibration(predicted, actual, n_bins=5)
        d7_out["home_favourite"] = {"n": c["n"], "ece": round(c["ece"], 4)}
    if len(away_fav_rows) >= MIN_SUBGROUP_N:
        predicted = [_f(r["market_1x2_opening_away_probability"]) for r in away_fav_rows]
        actual = [r["outcome_full_time_result"] == "A" for r in away_fav_rows]
        c = summarise_calibration(predicted, actual, n_bins=5)
        d7_out["away_favourite"] = {"n": c["n"], "ece": round(c["ece"], 4)}
    results["checks"]["D7_home_vs_away_favourite_calibration"] = {
        "description": "Market calibration (own favourite's own win probability, ECE, 5 bins) split by whether the home or away side is the market favourite.",
        **d7_out,
    }

    # ---------------- D8: competition-specific calibration ----------------
    d8_out = {}
    for comp in ("E0", "E1", "SC0"):
        comp_rows = [r for r in rows if r["competition_code"] == comp and _f(r["market_1x2_opening_home_probability"]) is not None]
        if len(comp_rows) < MIN_SUBGROUP_N:
            d8_out[comp] = {"n": len(comp_rows), "status": "insufficient_n"}
            continue
        predicted = [_f(r["market_1x2_opening_home_probability"]) for r in comp_rows]
        actual = [r["outcome_full_time_result"] == "H" for r in comp_rows]
        c = summarise_calibration(predicted, actual, n_bins=5)
        d8_out[comp] = {"n": c["n"], "ece": round(c["ece"], 4)}
    results["checks"]["D8_competition_specific_calibration"] = {
        "description": "Market 1X2 home-win calibration (ECE, 5 bins) computed separately per competition.",
        **d8_out,
    }

    # ---------------- D9: Dominant-Side Mispricing (LOCKED family) ----------------
    # Dominance defined PRE-MATCH, by the market's own favourite probability (never by outcome).
    d9_rows = []
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
        favourite_p = max(hp, ap)
        favourite_side = "home" if hp > ap else "away"
        margin = int(float(hg)) - int(float(ag))  # home goals minus away goals
        home_result_fraction = _settle_asian_handicap_home(margin, ah_line)
        d9_rows.append({
            "favourite_p": favourite_p,
            "favourite_side": favourite_side,
            "home_result_fraction": home_result_fraction,  # 1.0 = home covers, 0.0 = away covers, 0.5 = push
            "ah_home_p": ah_home_p,
        })

    d9_rows.sort(key=lambda r: r["favourite_p"])
    n9 = len(d9_rows)
    d9_out = {}
    if n9 >= MIN_SUBGROUP_N * 2:
        extreme_cut = n9 // 4  # top quartile by favourite strength
        extreme = d9_rows[-extreme_cut:]
        moderate = d9_rows[:n9 - extreme_cut]
        for label, group in (("extreme_favourite_top_quartile", extreme), ("non_extreme_rest", moderate)):
            # Restrict to non-push matches for a clean cover-rate calibration read.
            clean = [r for r in group if r["home_result_fraction"] in (0.0, 1.0)]
            if len(clean) < MIN_SUBGROUP_N:
                d9_out[label] = {"n": len(clean), "status": "insufficient_n"}
                continue
            predicted = [r["ah_home_p"] for r in clean]
            actual = [r["home_result_fraction"] == 1.0 for r in clean]
            c = summarise_calibration(predicted, actual, n_bins=5)
            d9_out[label] = {
                "n": c["n"],
                "ece_ah_home_cover": round(c["ece"], 4),
                "mean_favourite_probability": round(sum(r["favourite_p"] for r in group) / len(group), 4),
            }
    results["checks"]["D9_dominant_side_mispricing_locked_family"] = {
        "description": (
            "LOCKED pre-registered family. Dominance defined pre-match by the market's own 1X2 "
            "favourite probability (top quartile = 'extreme favourite'), never by the outcome. "
            "Compares Asian Handicap home-cover calibration (ECE) for extreme favourites vs the "
            "rest of the sample. A materially higher ECE for extreme favourites would be consistent "
            "with the market pricing WHO wins efficiently (1X2) but the MAGNITUDE of dominance "
            "(the handicap line) less efficiently -- exactly the mechanism this family investigates. "
            "Non-push matches only (pushes excluded from the calibration read, counted separately)."
        ),
        "n_total_ah_settled": n9,
        "n_pushes": sum(1 for r in d9_rows if r["home_result_fraction"] == 0.5),
        **d9_out,
    }

    return results


def main() -> int:
    results = run()
    out_path = PROCESSED_ROOT / "cycle_002_discovery_scan_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"discovery_slice_n": results["discovery_slice_n"], "n_checks": len(results["checks"])}, indent=2))
    print(f"Full results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
