"""Pure analysis functions for the Outcome Discovery & Winner/Loser research cycle.

No I/O, no model fitting -- these functions take already-loaded candidate/match dicts and
compute descriptive statistics (winner-vs-loser effect sizes, probability-band calibration,
top-pick accuracy, favourite/underdog/draw splits, conditional-market analysis, and
discovery-vs-validation feature stability). Kept separate from
scripts/run_outcome_discovery_analysis.py (which handles all file I/O) so this logic is
directly unit-testable, mirroring probability_model_v2_diagnostics.py's split from Phase 2.
"""
from __future__ import annotations

import statistics as stats
from collections import defaultdict

DISCOVERY_SEASONS = {"2020_21", "2021_22", "2022_23"}
VALIDATION_SEASONS = {"2023_24", "2024_25"}
HOLDOUT_SEASONS = {"2025_26"}
ALL_SEASONS_ORDER = ["2020_21", "2021_22", "2022_23", "2023_24", "2024_25", "2025_26"]

PROBABILITY_BANDS = [
    ("<30%", 0.0, 0.30),
    ("30-39.9%", 0.30, 0.40),
    ("40-49.9%", 0.40, 0.50),
    ("50-54.9%", 0.50, 0.55),
    ("55-59.9%", 0.55, 0.60),
    ("60-64.9%", 0.60, 0.65),
    ("65-69.9%", 0.65, 0.70),
    ("70-79.9%", 0.70, 0.80),
    ("80%+", 0.80, 1.0000001),
]

MODEL_PREFIXES = {
    "market": "model_0_market",
    "elo_poisson": "model_1_elo_poisson_blend",
    "fundamentals": "model_2_fundamentals",
    "market_fundamentals": "model_3_market_fundamentals",
    "ensemble": "model_4_ensemble",
}

SIGNED_FEATURES = [
    "elo_gap",
    "diff_goals_for_last10",
    "diff_shots_for_last10",
    "diff_points_per_game_last10",
    "diff_goals_for_last5",
    "diff_shots_for_last5",
    "diff_points_per_game_last5",
    "diff_sot_for_last10",
    "diff_sot_against_last10",
    "diff_corners_for_last10",
    "diff_cards_for_last10",
]

OUTCOME_LETTER = {"home": "home", "draw": "draw", "away": "away"}


def build_candidates(matches, feats):
    """One row per (match, side in {home, draw, away}). target=1 iff that side occurred.

    Signed features are oriented toward the candidate side: positive means an advantage FOR
    that side (home candidate keeps the raw home-minus-away value, away candidate negates it,
    draw candidate uses -abs(value), i.e. closer matches score higher for the draw candidate).
    """
    candidates = []
    for mid, m in matches.items():
        f = feats.get(mid)
        for side in ("home", "draw", "away"):
            target = 1 if m["outcome"] == OUTCOME_LETTER[side] else 0
            row = {
                "match_id": mid,
                "competition_code": m["competition_code"],
                "season": m["season"],
                "side": side,
                "target": target,
            }
            for model_key in MODEL_PREFIXES:
                row[f"prob_{model_key}"] = m["probs"][model_key][side]
            for feat_name in SIGNED_FEATURES:
                val = f.get(feat_name) if f is not None else None
                if val is None:
                    row[f"signed_{feat_name}"] = None
                elif side == "home":
                    row[f"signed_{feat_name}"] = val
                elif side == "away":
                    row[f"signed_{feat_name}"] = -val
                else:
                    row[f"signed_{feat_name}"] = -abs(val)
            candidates.append(row)
    return candidates


def partition_season(season):
    if season in DISCOVERY_SEASONS:
        return "discovery"
    if season in VALIDATION_SEASONS:
        return "validation"
    if season in HOLDOUT_SEASONS:
        return "holdout"
    return "unknown"


def cohens_d(a, b):
    """Pooled-variance Cohen's d for two samples, skipping None values. Returns
    (d, n_a, n_b, mean_a, mean_b); d and the means are None when either sample has fewer
    than 5 usable observations."""
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if len(a) < 5 or len(b) < 5:
        return None, len(a), len(b), None, None
    ma, mb = stats.mean(a), stats.mean(b)
    va = stats.pvariance(a)
    vb = stats.pvariance(b)
    na, nb = len(a), len(b)
    pooled_var = ((na - 1) * va + (nb - 1) * vb) / max(na + nb - 2, 1)
    pooled_sd = pooled_var ** 0.5
    d = (ma - mb) / pooled_sd if pooled_sd > 0 else None
    return d, na, nb, ma, mb


def winner_loser_table(candidates, feature_names, seasons_filter, sides=("home", "away")):
    out = []
    for feat in feature_names:
        winners = [
            c[f"signed_{feat}"]
            for c in candidates
            if c["side"] in sides and c["season"] in seasons_filter and c["target"] == 1
        ]
        losers = [
            c[f"signed_{feat}"]
            for c in candidates
            if c["side"] in sides and c["season"] in seasons_filter and c["target"] == 0
        ]
        d, n_w, n_l, mean_w, mean_l = cohens_d(winners, losers)
        out.append(
            {
                "feature": feat,
                "n_winners": n_w,
                "n_losers": n_l,
                "mean_winners": round(mean_w, 4) if mean_w is not None else None,
                "mean_losers": round(mean_l, 4) if mean_l is not None else None,
                "mean_diff": round(mean_w - mean_l, 4) if (mean_w is not None and mean_l is not None) else None,
                "cohens_d": round(d, 4) if d is not None else None,
            }
        )
    return out


def probability_bands_report(candidates, model_key):
    out = []
    for label, lo, hi in PROBABILITY_BANDS:
        in_band = [
            c for c in candidates
            if c[f"prob_{model_key}"] is not None and lo <= c[f"prob_{model_key}"] < hi
        ]
        n = len(in_band)
        if n == 0:
            out.append({"band": label, "model": model_key, "n": 0, "mean_predicted": None, "actual_win_rate": None, "calibration_error": None})
            continue
        mean_pred = stats.mean(c[f"prob_{model_key}"] for c in in_band)
        actual_rate = stats.mean(c["target"] for c in in_band)
        out.append(
            {
                "band": label,
                "model": model_key,
                "n": n,
                "mean_predicted": round(mean_pred, 4),
                "actual_win_rate": round(actual_rate, 4),
                "calibration_error": round(actual_rate - mean_pred, 4),
            }
        )
    return out


def top_pick_accuracy(matches, model_key, seasons_filter=None):
    total = 0
    correct = 0
    by_side_total = defaultdict(int)
    by_side_correct = defaultdict(int)
    by_season = defaultdict(lambda: [0, 0])
    for m in matches.values():
        if seasons_filter is not None and m["season"] not in seasons_filter:
            continue
        probs = m["probs"][model_key]
        if any(v is None for v in probs.values()):
            continue
        pick = max(probs, key=probs.get)
        actual_side = m["outcome"]
        total += 1
        by_season[m["season"]][1] += 1
        is_correct = 1 if pick == actual_side else 0
        correct += is_correct
        by_side_total[pick] += 1
        by_side_correct[pick] += is_correct
        by_season[m["season"]][0] += is_correct
    return {
        "model": model_key,
        "n_matches": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else None,
        "by_side": {
            side: {
                "n_picked": by_side_total[side],
                "correct": by_side_correct[side],
                "accuracy": round(by_side_correct[side] / by_side_total[side], 4) if by_side_total[side] else None,
            }
            for side in ("home", "draw", "away")
        },
        "by_season": {
            s: {"correct": v[0], "n": v[1], "accuracy": round(v[0] / v[1], 4) if v[1] else None}
            for s, v in sorted(by_season.items())
        },
    }


def favourite_analysis(matches, feats, seasons_filter=None):
    """Favourite = argmax(market home/draw/away), restricted to home/away favourites."""
    fav_won_feats = defaultdict(list)
    fav_lost_feats = defaultdict(list)
    n_fav_won = 0
    n_fav_lost = 0
    for m in matches.values():
        if seasons_filter is not None and m["season"] not in seasons_filter:
            continue
        probs = m["probs"]["market"]
        if any(v is None for v in probs.values()):
            continue
        fav_side = max(probs, key=probs.get)
        if fav_side == "draw":
            continue
        actual_side = m["outcome"]
        fav_won = 1 if actual_side == fav_side else 0
        f = feats.get(m["match_id"])
        for feat_name in SIGNED_FEATURES:
            val = None
            if f is not None:
                raw = f.get(feat_name)
                if raw is not None:
                    val = raw if fav_side == "home" else -raw
            (fav_won_feats if fav_won else fav_lost_feats)[feat_name].append(val)
        if fav_won:
            n_fav_won += 1
        else:
            n_fav_lost += 1
    rows = []
    for feat_name in SIGNED_FEATURES:
        d, n_w, n_l, mean_w, mean_l = cohens_d(fav_won_feats[feat_name], fav_lost_feats[feat_name])
        rows.append(
            {
                "feature": feat_name,
                "n_favourite_won": n_w,
                "n_favourite_lost": n_l,
                "mean_when_won": round(mean_w, 4) if mean_w is not None else None,
                "mean_when_lost": round(mean_l, 4) if mean_l is not None else None,
                "cohens_d": round(d, 4) if d is not None else None,
            }
        )
    return rows, n_fav_won, n_fav_lost


def underdog_analysis(matches, feats, seasons_filter=None):
    """Underdog = whichever of home/away has the lower market probability."""
    dog_won_feats = defaultdict(list)
    dog_lost_feats = defaultdict(list)
    n_dog_won = 0
    n_dog_lost = 0
    for m in matches.values():
        if seasons_filter is not None and m["season"] not in seasons_filter:
            continue
        probs = m["probs"]["market"]
        if any(v is None for v in probs.values()):
            continue
        ha_only = {"home": probs["home"], "away": probs["away"]}
        dog_side = min(ha_only, key=ha_only.get)
        actual_side = m["outcome"]
        dog_won = 1 if actual_side == dog_side else 0
        f = feats.get(m["match_id"])
        for feat_name in SIGNED_FEATURES:
            val = None
            if f is not None:
                raw = f.get(feat_name)
                if raw is not None:
                    val = raw if dog_side == "home" else -raw
            (dog_won_feats if dog_won else dog_lost_feats)[feat_name].append(val)
        if dog_won:
            n_dog_won += 1
        else:
            n_dog_lost += 1
    rows = []
    for feat_name in SIGNED_FEATURES:
        d, n_w, n_l, mean_w, mean_l = cohens_d(dog_won_feats[feat_name], dog_lost_feats[feat_name])
        rows.append(
            {
                "feature": feat_name,
                "n_underdog_won": n_w,
                "n_underdog_lost": n_l,
                "mean_when_won": round(mean_w, 4) if mean_w is not None else None,
                "mean_when_lost": round(mean_l, 4) if mean_l is not None else None,
                "cohens_d": round(d, 4) if d is not None else None,
            }
        )
    return rows, n_dog_won, n_dog_lost


def draw_analysis(candidates, seasons_filter):
    return winner_loser_table(candidates, SIGNED_FEATURES, seasons_filter, sides=("draw",))


def conditional_market_analysis(candidates, seasons_filter, band_lo=0.50, band_hi=0.65):
    """Within a market-probability band, do the signed features still separate winners from
    losers? This is the direct test of whether historical features add information BEYOND
    what the market already prices in for candidates of similar market-estimated strength."""
    in_band = [
        c for c in candidates
        if c["side"] in ("home", "away")
        and c["season"] in seasons_filter
        and c["prob_market"] is not None
        and band_lo <= c["prob_market"] < band_hi
    ]
    rows = []
    for feat in SIGNED_FEATURES:
        winners = [c[f"signed_{feat}"] for c in in_band if c["target"] == 1]
        losers = [c[f"signed_{feat}"] for c in in_band if c["target"] == 0]
        d, n_w, n_l, mean_w, mean_l = cohens_d(winners, losers)
        rows.append(
            {
                "feature": feat,
                "band": f"{band_lo:.3f}-{band_hi:.3f}",
                "n_winners": n_w,
                "n_losers": n_l,
                "mean_diff": round(mean_w - mean_l, 4) if (mean_w is not None and mean_l is not None) else None,
                "cohens_d": round(d, 4) if d is not None else None,
            }
        )
    return rows


def feature_stability(candidates):
    """Discovery-vs-validation replication is the actual stability test (both partitions have
    the engineered-feature join available). Holdout (2025/26) is reported separately as
    DATA UNAVAILABLE, never folded into the STABLE/UNSTABLE verdict -- a None cohens_d (because
    cycle_002_discovery_features.csv does not cover 2025/26) must not be silently treated as a
    sign-disagreement / instability finding.
    """
    rows = []
    for feat in SIGNED_FEATURES:
        d_disc = winner_loser_table(candidates, [feat], DISCOVERY_SEASONS)[0]
        d_val = winner_loser_table(candidates, [feat], VALIDATION_SEASONS)[0]
        d_hold = winner_loser_table(candidates, [feat], HOLDOUT_SEASONS)[0]
        cd, cv = d_disc["cohens_d"], d_val["cohens_d"]
        if cd is None or cv is None:
            verdict = "INSUFFICIENT_DATA"
        else:
            same_sign = (cd > 0) == (cv > 0)
            both_nontrivial = abs(cd) >= 0.03 and abs(cv) >= 0.03
            verdict = "STABLE (discovery-validation)" if (same_sign and both_nontrivial) else "UNSTABLE (discovery-validation)"
        holdout_status = (
            "DATA UNAVAILABLE (2025/26 not in cycle_002_discovery_features.csv)"
            if d_hold["cohens_d"] is None
            else round(d_hold["cohens_d"], 4)
        )
        rows.append(
            {
                "feature": feat,
                "cohens_d_discovery": cd,
                "cohens_d_validation": cv,
                "cohens_d_holdout": holdout_status,
                "verdict": verdict,
            }
        )
    return rows
