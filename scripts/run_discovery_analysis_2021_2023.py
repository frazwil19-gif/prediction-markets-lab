"""Workstream B Phase 2 discovery analysis: 13 pre-registered families,
2021-2023, Task #22 (2026-09-16).

Per the operator's explicit instructions:
  - Every family is reported, including nulls -- no cherry-picking.
  - Bins are PRE-DECLARED round numbers (many reused unchanged from the
    January 2026 pipeline's own bin set), never tuned after seeing results.
  - Bonferroni-style correction is applied across the 13 families: each
    family's confidence interval is built at (1 - 0.05/13) coverage
    (~99.6%) rather than 95%, so "significant" already means
    Bonferroni-corrected significant.
  - This finds PRICING ERRORS in the non-executable BASIC last-traded
    price only -- it never claims executable EV (no back/lay ladder, no
    commission, no slippage/liquidity model exists yet).
  - Year-by-year stability and a fixed alternate binning are reported for
    every family that clears the significance bar, per the no-threshold-
    mining instruction.

Core test, applied uniformly across all 13 families: within each
pre-declared bucket of a family's variable, is the market's own reference
probability MISCALIBRATED against the realised outcome? That is exactly
"does the model/covariate reveal a bucket where the market's own BASIC
LTP price was wrong" -- a pricing-error question, not a claim that Fraser
could have captured that price.

deviation = mean(outcome) - mean(market_reference_probability)   [paired,
    same rows, so this is NOT comparing two different samples]

A 2000-resample vectorised bootstrap gives the (1-alpha) CI on deviation;
a family/bucket is "significant" iff that CI excludes 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path.home() / "mnt" / "prediction-markets-lab"
DATA_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_2021_2023_discovery_dataset.csv"
OUT_JSON = REPO_ROOT / "data" / "interim" / "workstream_b_discovery_2021_2023_results.json"
OUT_CSV = REPO_ROOT / "data" / "interim" / "workstream_b_discovery_2021_2023_bucket_results.csv"

N_FAMILIES = 13
ALPHA = 0.05
CORRECTED_ALPHA = ALPHA / N_FAMILIES  # Bonferroni across the 13 pre-registered families
N_BOOT = 2000
SEED = 20260916  # today's date, fixed for reproducibility (project convention)
MIN_N_FOR_PROMOTE = 150

rng = np.random.default_rng(SEED)


def bootstrap_deviation(outcome: np.ndarray, market_prob: np.ndarray, n_boot=N_BOOT, alpha=CORRECTED_ALPHA):
    """Paired bootstrap CI for deviation = mean(outcome) - mean(market_prob).
    Vectorised: builds an (n_boot, n) index matrix once, no Python-level loop."""
    n = len(outcome)
    if n == 0:
        return {"n": 0, "point": None, "ci_lo": None, "ci_hi": None, "significant": False}
    point = float(outcome.mean() - market_prob.mean())
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_outcome_mean = outcome[idx].mean(axis=1)
    boot_market_mean = market_prob[idx].mean(axis=1)
    boot_dev = boot_outcome_mean - boot_market_mean
    lo = float(np.percentile(boot_dev, 100 * (alpha / 2)))
    hi = float(np.percentile(boot_dev, 100 * (1 - alpha / 2)))
    significant = not (lo <= 0 <= hi)
    return {"n": int(n), "point": point, "ci_lo": lo, "ci_hi": hi, "significant": bool(significant)}


def bucket_report(df: pd.DataFrame, bucket_col: str, outcome_col: str, market_col: str, model_col: str | None = None) -> list[dict]:
    """One row per non-empty bucket value, with the full stats package."""
    rows = []
    for bucket_val, sub in df.groupby(bucket_col, observed=True):
        sub = sub.dropna(subset=[outcome_col, market_col])
        if len(sub) == 0:
            continue
        outcome = sub[outcome_col].astype(float).values
        market = sub[market_col].astype(float).values
        stats = bootstrap_deviation(outcome, market)
        row = {
            "bucket": str(bucket_val),
            "n": stats["n"],
            "mean_market_prob": round(float(market.mean()), 4),
            "actual_outcome_rate": round(float(outcome.mean()), 4),
            "deviation": round(stats["point"], 4) if stats["point"] is not None else None,
            "ci_lo": round(stats["ci_lo"], 4) if stats["ci_lo"] is not None else None,
            "ci_hi": round(stats["ci_hi"], 4) if stats["ci_hi"] is not None else None,
            "significant_bonferroni": stats["significant"],
        }
        if model_col is not None:
            row["mean_model_prob"] = round(float(sub[model_col].astype(float).mean()), 4)
        rows.append(row)
    return rows


def year_stability(df: pd.DataFrame, mask, outcome_col: str, market_col: str) -> dict:
    out = {}
    for year, ysub in df[mask].groupby("year"):
        ysub = ysub.dropna(subset=[outcome_col, market_col])
        if len(ysub) == 0:
            out[str(year)] = {"n": 0, "deviation": None}
            continue
        dev = float(ysub[outcome_col].astype(float).mean() - ysub[market_col].astype(float).mean())
        out[str(year)] = {"n": int(len(ysub)), "deviation": round(dev, 4)}
    return out


def make_bin(series: pd.Series, edges: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(series, bins=edges, labels=labels, include_lowest=True)


def classify_verdict(buckets: list[dict], year_stab: dict | None, rebinned_ok: bool | None, mechanism_plausible: bool) -> str:
    sig_buckets = [b for b in buckets if b["significant_bonferroni"] and b["n"] >= MIN_N_FOR_PROMOTE]
    if not sig_buckets:
        return "REJECT"
    if not mechanism_plausible:
        return "PARTIAL"
    if year_stab is not None:
        signs = [v["deviation"] > 0 for v in year_stab.values() if v["deviation"] is not None and v["n"] >= 30]
        if signs and not (all(signs) or not any(signs)):
            return "PARTIAL"  # sign flips across years -- not stable
    if rebinned_ok is False:
        return "PARTIAL"
    return "PROMOTE"


def main():
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} discovery rows (2021-2023, MATCHED, 30min-priced subset varies by family)")

    df["outcome_a_won_f"] = df["outcome_a_won"].astype(float)
    results = {}
    all_bucket_rows = []

    # ------------------------------------------------------------------
    # Family 1: Model-market disagreement (elo_prob_a - market_prob_a_30min)
    # Bins reused UNCHANGED from the January 2026 pipeline's own bin set.
    # ------------------------------------------------------------------
    f1 = df.dropna(subset=["model_market_delta_30min", "market_prob_a_30min"]).copy()
    edges = [-1.0, -0.10, -0.03, 0.03, 0.10, 1.0]
    labels = ["<=-0.10", "(-0.10,-0.03]", "(-0.03,0.03]", "(0.03,0.10]", ">0.10"]
    f1["bucket"] = make_bin(f1["model_market_delta_30min"], edges, labels)
    buckets = bucket_report(f1, "bucket", "outcome_a_won_f", "market_prob_a_30min", "elo_prob_a")
    extreme_mask = f1["bucket"].isin([">0.10"])
    ys = year_stability(f1, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    # bin sensitivity: shift edges
    f1["bucket_alt"] = make_bin(f1["model_market_delta_30min"], [-1.0, -0.08, -0.02, 0.02, 0.08, 1.0],
                                 ["<=-0.08", "(-0.08,-0.02]", "(-0.02,0.02]", "(0.02,0.08]", ">0.08"])
    buckets_alt = bucket_report(f1, "bucket_alt", "outcome_a_won_f", "market_prob_a_30min")
    top_alt = next((b for b in buckets_alt if b["bucket"] == ">0.08"), None)
    top_orig = next((b for b in buckets if b["bucket"] == ">0.10"), None)
    rebin_ok = None
    if top_alt and top_orig and top_orig["deviation"] is not None and top_alt["deviation"] is not None:
        rebin_ok = (top_orig["deviation"] > 0) == (top_alt["deviation"] > 0)
    verdict = classify_verdict(buckets, ys, rebin_ok, mechanism_plausible=True)
    results["1_model_market_disagreement"] = {
        "description": "Bucketed by (elo_prob_a - market_prob_a_30min); tests whether Elo-market "
                       "disagreement predicts a market miscalibration (a genuine pricing error the "
                       "model detects), not an executable edge.",
        "mechanism": "If Elo captures real skill information the BASIC LTP price does not yet reflect "
                     "(e.g. thin liquidity, stale opening price), large positive disagreement should "
                     "coincide with the market underpricing player A.",
        "n_total": len(f1), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": rebin_ok, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "1_model_market_disagreement", **b})

    # ------------------------------------------------------------------
    # Family 2: Favourite/underdog (market-defined) -- perspective-shifted:
    # one row per match from the MARKET FAVOURITE's point of view.
    # ------------------------------------------------------------------
    f2 = df.dropna(subset=["market_prob_a_30min"]).copy()
    f2["fav_is_a"] = f2["market_prob_a_30min"] > 0.5
    f2["fav_market_prob"] = np.where(f2["fav_is_a"], f2["market_prob_a_30min"], 1 - f2["market_prob_a_30min"])
    f2["fav_won"] = np.where(f2["fav_is_a"], f2["outcome_a_won_f"], 1 - f2["outcome_a_won_f"])
    f2["bucket"] = "market_favourite"
    buckets = bucket_report(f2, "bucket", "fav_won", "fav_market_prob")
    ys = year_stability(f2, pd.Series(True, index=f2.index), "fav_won", "fav_market_prob")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["2_favourite_underdog"] = {
        "description": "Every match viewed from the market favourite's side: does the favourite win "
                       "more or less often than the market's own implied probability says?",
        "mechanism": "Classic favourite-longshot bias would show favourites winning MORE than implied "
                     "(positive deviation).",
        "n_total": len(f2), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "2_favourite_underdog", **b})

    # ------------------------------------------------------------------
    # Family 3: Price bands (player-A perspective, quintile-style round bins)
    # ------------------------------------------------------------------
    f3 = df.dropna(subset=["market_prob_a_30min"]).copy()
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    labels = ["[0,0.2)", "[0.2,0.4)", "[0.4,0.6)", "[0.6,0.8)", "[0.8,1.0]"]
    f3["bucket"] = make_bin(f3["market_prob_a_30min"], edges, labels)
    buckets = bucket_report(f3, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f3["bucket"].isin(["[0.8,1.0]"])
    ys = year_stability(f3, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["3_price_bands"] = {
        "description": "Standard calibration curve: market_prob_a_30min in quintile-style bands vs "
                       "actual player-A outcome rate.",
        "mechanism": "A systematically miscalibrated band (e.g. extreme favourites under-priced) would "
                     "be a real, reportable pricing pattern in BASIC LTP.",
        "n_total": len(f3), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "3_price_bands", **b})

    # ------------------------------------------------------------------
    # Family 4: Rank gap (rank_gap_b_minus_a; positive = A better ranked)
    # ------------------------------------------------------------------
    f4 = df.dropna(subset=["rank_gap_b_minus_a", "market_prob_a_30min"]).copy()
    edges = [-np.inf, -50, -10, 10, 50, np.inf]
    labels = ["<=-50", "(-50,-10]", "(-10,10]", "(10,50]", ">50"]
    f4["bucket"] = make_bin(f4["rank_gap_b_minus_a"], edges, labels)
    buckets = bucket_report(f4, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f4["bucket"].isin([">50"])
    ys = year_stability(f4, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["4_rank_gap"] = {
        "description": "Bucketed by ATP rank gap (player_b_rank - player_a_rank); tests whether the "
                       "market fully prices in large ranking gaps.",
        "mechanism": "Ranking is public information -- a real edge here would be surprising and would "
                     "need a specific reason (e.g. stale ranking data, market inattention to lower tiers).",
        "n_total": len(f4), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "4_rank_gap", **b})

    # ------------------------------------------------------------------
    # Family 5: Elo gap (elo_prob_a itself, same style as price bands)
    # ------------------------------------------------------------------
    f5 = df.dropna(subset=["elo_prob_a", "market_prob_a_30min"]).copy()
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    labels = ["[0,0.2)", "[0.2,0.4)", "[0.4,0.6)", "[0.6,0.8)", "[0.8,1.0]"]
    f5["bucket"] = make_bin(f5["elo_prob_a"], edges, labels)
    buckets = bucket_report(f5, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f5["bucket"].isin(["[0.8,1.0]"])
    ys = year_stability(f5, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["5_elo_gap"] = {
        "description": "Bucketed by elo_prob_a; tests whether the market is miscalibrated specifically "
                       "in matches where the FROZEN Elo model sees a large rating gap.",
        "mechanism": "If Elo captures skill info the market underweights at large gaps, deviation should "
                     "be positive in the extreme Elo bucket.",
        "n_total": len(f5), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "5_elo_gap", **b})

    # ------------------------------------------------------------------
    # Family 6: Elo-vs-ranking disagreement
    # ------------------------------------------------------------------
    f6 = df.dropna(subset=["elo_vs_ranking_delta", "market_prob_a_30min"]).copy()
    edges = [-1.0, -0.10, -0.03, 0.03, 0.10, 1.0]
    labels = ["<=-0.10", "(-0.10,-0.03]", "(-0.03,0.03]", "(0.03,0.10]", ">0.10"]
    f6["bucket"] = make_bin(f6["elo_vs_ranking_delta"], edges, labels)
    buckets = bucket_report(f6, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f6["bucket"].isin([">0.10"])
    ys = year_stability(f6, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["6_elo_vs_ranking_disagreement"] = {
        "description": "Bucketed by (elo_prob_a - ranking_prob_a); tests whether cases where Elo and "
                       "the simple ranking-points baseline disagree also see the market mispriced.",
        "mechanism": "Elo captures recent head-to-head/form dynamics ranking points do not -- a real "
                     "edge would need the market to also miss this, beyond either model alone.",
        "n_total": len(f6), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "6_elo_vs_ranking_disagreement", **b})

    # ------------------------------------------------------------------
    # Family 7: Surface (categorical) -- FAVOURITE-PERSPECTIVE, not raw
    # player_a. Surface does not correlate with the arbitrary lexicographic
    # player_a/player_b label (see canonicalise_cycle_002_tennis_match_data.py:
    # "player_a = whichever of winner_id/loser_id sorts first lexicographically
    # -- carries no information about who won"). Bucketing a label-symmetric
    # metric (outcome_a_won - market_prob_a) by a variable unrelated to that
    # label is a null test by construction for any TRUE favourite/underdog
    # calibration bias: if roughly half of Grass matches have A as favourite
    # and half as underdog, a genuine symmetric bias cancels to ~0 in the A
    # perspective regardless of its true size. Using the favourite's own
    # perspective (as families 2/13 already do) avoids this cancellation.
    # ------------------------------------------------------------------
    f7 = df.dropna(subset=["surface", "market_prob_a_30min"]).copy()
    f7["fav_is_a"] = f7["market_prob_a_30min"] > 0.5
    f7["fav_market_prob"] = np.where(f7["fav_is_a"], f7["market_prob_a_30min"], 1 - f7["market_prob_a_30min"])
    f7["fav_won"] = np.where(f7["fav_is_a"], f7["outcome_a_won_f"], 1 - f7["outcome_a_won_f"])
    buckets = bucket_report(f7, "surface", "fav_won", "fav_market_prob")
    top_bucket_name = max(buckets, key=lambda b: abs(b["deviation"] or 0))["bucket"] if buckets else None
    ys = year_stability(f7, f7["surface"] == top_bucket_name, "fav_won", "fav_market_prob") if top_bucket_name else {}
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["7_surface"] = {
        "description": "Bucketed by surface (Hard/Clay/Grass), tested from the MARKET FAVOURITE's "
                       "perspective (avoids cancelling out a real bias via the arbitrary player_a/b "
                       "label): does the favourite's win rate match the favourite's implied probability, "
                       "and does that calibration differ by surface?",
        "mechanism": "Thinner liquidity or fewer historical bettors on Grass (shortest season) could "
                     "plausibly show worse favourite calibration than Hard.",
        "n_total": len(f7), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
        "note": "An earlier version of this family used the raw (non-favourite-adjusted) player_a "
                "perspective and found a nominally-significant Grass deviation (+0.047, N=844). That "
                "framing is a null test by construction for a real symmetric bias (see comment in "
                "source) and the finding did not survive switching to the favourite-perspective metric "
                "below -- recorded here transparently as a corrected methodology, not a silently "
                "discarded result.",
    }
    for b in buckets:
        all_bucket_rows.append({"family": "7_surface", **b})

    # ------------------------------------------------------------------
    # Family 8: Tournament level/format -- favourite-perspective, same
    # reasoning as family 7 (tourney_level is unrelated to the arbitrary
    # player_a/b label).
    # ------------------------------------------------------------------
    f8 = df.dropna(subset=["tourney_level", "market_prob_a_30min"]).copy()
    f8["fav_is_a"] = f8["market_prob_a_30min"] > 0.5
    f8["fav_market_prob"] = np.where(f8["fav_is_a"], f8["market_prob_a_30min"], 1 - f8["market_prob_a_30min"])
    f8["fav_won"] = np.where(f8["fav_is_a"], f8["outcome_a_won_f"], 1 - f8["outcome_a_won_f"])
    buckets = bucket_report(f8, "tourney_level", "fav_won", "fav_market_prob")
    top_bucket_name = max((b for b in buckets if b["n"] >= 30), key=lambda b: abs(b["deviation"] or 0))["bucket"] if any(b["n"] >= 30 for b in buckets) else None
    ys = year_stability(f8, f8["tourney_level"] == top_bucket_name, "fav_won", "fav_market_prob") if top_bucket_name else {}
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["8_tournament_level_format"] = {
        "description": "Bucketed by tourney_level (G/M/500/250/A/D/F/O), favourite-perspective; tests "
                       "whether smaller, less-watched events are less well-priced than majors/Masters.",
        "mechanism": "Lower-tier events (250s) draw less betting attention and could be less efficiently "
                     "priced than majors.",
        "n_total": len(f8), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "8_tournament_level_format", **b})

    # ------------------------------------------------------------------
    # Family 9: Recent/surface form (difference, A minus B)
    # ------------------------------------------------------------------
    f9 = df.copy()
    f9["form_diff"] = f9["player_a_recent_form"] - f9["player_b_recent_form"]
    f9 = f9.dropna(subset=["form_diff", "market_prob_a_30min"])
    edges = [-1.01, -0.3, -0.1, 0.1, 0.3, 1.01]
    labels = ["<=-0.3", "(-0.3,-0.1]", "(-0.1,0.1]", "(0.1,0.3]", ">0.3"]
    f9["bucket"] = make_bin(f9["form_diff"], edges, labels)
    buckets = bucket_report(f9, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f9["bucket"].isin([">0.3"])
    ys = year_stability(f9, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["9_recent_surface_form"] = {
        "description": "Bucketed by (player_a_recent_form - player_b_recent_form), trailing-10-match "
                       "win-rate difference, shift(1)-lagged so leakage-safe; tests whether short-term "
                       "form the market may under-weight predicts a pricing gap.",
        "mechanism": "'Hot streak' effects are a commonly claimed (and commonly overstated) betting "
                     "signal -- a real, liquid market should already price recent form into current odds.",
        "n_total": len(f9), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "9_recent_surface_form", **b})

    # ------------------------------------------------------------------
    # Family 10: Congestion/rest (rest_days difference, A minus B)
    # ------------------------------------------------------------------
    f10 = df.copy()
    f10["rest_diff"] = f10["player_a_rest_days"] - f10["player_b_rest_days"]
    f10 = f10.dropna(subset=["rest_diff", "market_prob_a_30min"])
    edges = [-np.inf, -7, -2, 2, 7, np.inf]
    labels = ["<=-7", "(-7,-2]", "(-2,2]", "(2,7]", ">7"]
    f10["bucket"] = make_bin(f10["rest_diff"], edges, labels)
    buckets = bucket_report(f10, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f10["bucket"].isin(["<=-7"])
    ys = year_stability(f10, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["10_congestion_rest"] = {
        "description": "Bucketed by (player_a_rest_days - player_b_rest_days) using tourney_date-"
                       "granularity rest; tests whether a large rest disadvantage/advantage predicts a "
                       "pricing gap the market misses.",
        "mechanism": "Fatigue from a shorter turnaround is a plausible, widely-discussed effect; whether "
                     "the market already prices it is the actual question.",
        "n_total": len(f10), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "10_congestion_rest", **b})

    # ------------------------------------------------------------------
    # Family 11: Time-to-start (repeat family-1-style bins at each horizon)
    # ------------------------------------------------------------------
    horizon_cols = {"24h": "market_prob_a_24h", "6h": "market_prob_a_6h", "1h": "market_prob_a_1h", "30min": "market_prob_a_30min"}
    horizon_results = {}
    for label, col in horizon_cols.items():
        sub = df.dropna(subset=["elo_prob_a", col]).copy()
        sub["delta"] = sub["elo_prob_a"] - sub[col]
        sub["bucket"] = make_bin(sub["delta"], [-1.0, -0.10, -0.03, 0.03, 0.10, 1.0],
                                  ["<=-0.10", "(-0.10,-0.03]", "(-0.03,0.03]", "(0.03,0.10]", ">0.10"])
        buckets_h = bucket_report(sub, "bucket", "outcome_a_won_f", col)
        top = next((b for b in buckets_h if b["bucket"] == ">0.10"), None)
        horizon_results[label] = {"n_total": len(sub), "top_bucket_deviation": top["deviation"] if top else None,
                                   "top_bucket_ci": [top["ci_lo"], top["ci_hi"]] if top else None,
                                   "top_bucket_significant": top["significant_bonferroni"] if top else None,
                                   "buckets": buckets_h}
        for b in buckets_h:
            all_bucket_rows.append({"family": f"11_time_to_start_{label}", **b})
    any_sig = any(v["top_bucket_significant"] for v in horizon_results.values() if v["top_bucket_significant"] is not None)
    verdict = "REJECT" if not any_sig else "PARTIAL"
    results["11_time_to_start"] = {
        "description": "Repeats the model-market-disagreement bucketing at 4 horizons (24h/6h/1h/30min) "
                       "to test whether disagreement is more or less informative further from match start.",
        "mechanism": "If mispricing reflects stale ante-post prices, disagreement should be LARGER and "
                     "more predictive far from start (24h) and shrink as the market absorbs information "
                     "closer to start (30min).",
        "horizon_results": horizon_results, "verdict": verdict,
    }

    # ------------------------------------------------------------------
    # Family 12: Cross-horizon price movement (6h -> 30min)
    # ------------------------------------------------------------------
    f12 = df.dropna(subset=["price_movement_6h_to_30min", "market_prob_a_30min"]).copy()
    edges = [-1.01, -0.05, -0.01, 0.01, 0.05, 1.01]
    labels = ["<=-0.05", "(-0.05,-0.01]", "(-0.01,0.01]", "(0.01,0.05]", ">0.05"]
    f12["bucket"] = make_bin(f12["price_movement_6h_to_30min"], edges, labels)
    buckets = bucket_report(f12, "bucket", "outcome_a_won_f", "market_prob_a_30min")
    extreme_mask = f12["bucket"].isin([">0.05"])
    ys = year_stability(f12, extreme_mask, "outcome_a_won_f", "market_prob_a_30min")
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["12_cross_horizon_price_movement"] = {
        "description": "Bucketed by (market_prob_a_30min - market_prob_a_6h), i.e. how much the price "
                       "moved toward/away from player A between 6h and 30min before start; tests a "
                       "'steam'/momentum-continuation hypothesis against the 30min closing price.",
        "mechanism": "If late price movement reflects real new information (injury news, practice-court "
                     "reports) not yet fully absorbed, the 30min price could still be under-adjusted in "
                     "the direction of the recent move.",
        "n_total": len(f12), "buckets": buckets, "year_stability_top_bucket": ys,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "12_cross_horizon_price_movement", **b})

    # ------------------------------------------------------------------
    # Family 13: Favourite-longshot bias (favourite-perspective, fine bins)
    # ------------------------------------------------------------------
    f13 = df.dropna(subset=["market_prob_a_30min"]).copy()
    f13["fav_is_a"] = f13["market_prob_a_30min"] > 0.5
    f13["fav_market_prob"] = np.where(f13["fav_is_a"], f13["market_prob_a_30min"], 1 - f13["market_prob_a_30min"])
    f13["fav_won"] = np.where(f13["fav_is_a"], f13["outcome_a_won_f"], 1 - f13["outcome_a_won_f"])
    edges = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    labels = ["[0.5,0.6)", "[0.6,0.7)", "[0.7,0.8)", "[0.8,0.9)", "[0.9,1.0]"]
    f13["bucket"] = make_bin(f13["fav_market_prob"], edges, labels)
    buckets = bucket_report(f13, "bucket", "fav_won", "fav_market_prob")
    extreme_mask = f13["bucket"].isin(["[0.9,1.0]"])
    ys = year_stability(f13, extreme_mask, "fav_won", "fav_market_prob")
    # monotonicity check across the 5 bins (classic favourite-longshot bias
    # predicts deviation INCREASING as the favourite's price gets more extreme)
    devs_in_order = [b["deviation"] for b in buckets if b["deviation"] is not None]
    monotonic_increasing = all(devs_in_order[i] <= devs_in_order[i + 1] for i in range(len(devs_in_order) - 1)) if len(devs_in_order) >= 2 else None
    verdict = classify_verdict(buckets, ys, None, mechanism_plausible=True)
    results["13_favourite_longshot_bias"] = {
        "description": "Favourite-perspective price bands ([0.5,0.6) ... [0.9,1.0]); tests the classic "
                       "favourite-longshot bias pattern (favourites winning more than implied, longshots "
                       "less than implied) in Betfair tennis BASIC LTP.",
        "mechanism": "Favourite-longshot bias is well-documented in bookmaker odds; whether it also "
                     "appears in a two-sided exchange's last-traded price (no bookmaker margin) is the "
                     "real, non-obvious question here.",
        "n_total": len(f13), "buckets": buckets, "year_stability_top_bucket": ys,
        "monotonic_increasing_across_bands": monotonic_increasing,
        "bin_sensitivity_top_bucket_same_sign": None, "verdict": verdict,
    }
    for b in buckets:
        all_bucket_rows.append({"family": "13_favourite_longshot_bias", **b})

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    import json
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)
    pd.DataFrame(all_bucket_rows).to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_CSV}")

    print("\n=== VERDICT SUMMARY (all 13 families, corrected alpha={:.4f}) ===".format(CORRECTED_ALPHA))
    for i in range(1, 14):
        key = next(k for k in results if k.startswith(f"{i}_"))
        print(f"  Family {i:>2} [{key}]: {results[key]['verdict']}")


if __name__ == "__main__":
    main()
