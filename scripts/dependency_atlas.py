"""Bounded Dependency Atlas expansion (plan: research/platform_v2/props_c1/dependency/ATLAS_PLAN.md). DESCRIPTIVE ONLY.

Usage: python scripts/dependency_atlas.py <Matches.csv>  -> research/platform_v2/props_c1/dependency/ATLAS.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "research/platform_v2/props_c1/dependency/ATLAS.json"
DIVS = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1"]
START, END = "2015-07-01", "2026-07-01"
BOOT, SEED = 1000, 7


def main(path: str) -> int:
    d = pd.read_csv(path, low_memory=False, parse_dates=["MatchDate"])
    d = d[d.Division.isin(DIVS) & (d.MatchDate >= START) & (d.MatchDate < END)].dropna(
        subset=["HomeCorners", "AwayCorners", "HomeYellow", "AwayYellow", "HomeTarget", "AwayTarget", "FTHome", "FTAway", "OddHome", "OddDraw", "OddAway"]).copy()
    inv = 1 / d[["OddHome", "OddDraw", "OddAway"]]
    fav_home = (inv.OddHome >= inv.OddAway).to_numpy()
    ev = {
        "fav_win": np.where(fav_home, d.FTResult == "H", d.FTResult == "A"),
        "fav_sot_over_4.5": np.where(fav_home, d.HomeTarget, d.AwayTarget) > 4.5,
        "total_corners_over_9.5": (d.HomeCorners + d.AwayCorners > 9.5).to_numpy(),
        "total_cards_over_4.5": (d.HomeYellow + d.AwayYellow + d.HomeRed.fillna(0) + d.AwayRed.fillna(0) > 4.5).to_numpy(),
        "total_goals_over_2.5": (d.FTHome + d.FTAway > 2.5).to_numpy(),
        "total_sot_over_8.5": (d.HomeTarget + d.AwayTarget > 8.5).to_numpy(),
    }
    pairs = [("WIN_x_SOT", "fav_win", "fav_sot_over_4.5"), ("WIN_x_CORNERS", "fav_win", "total_corners_over_9.5"),
             ("WIN_x_CARDS", "fav_win", "total_cards_over_4.5"), ("GOALS_x_SOT", "total_goals_over_2.5", "total_sot_over_8.5"),
             ("GOALS_x_CORNERS", "total_goals_over_2.5", "total_corners_over_9.5"), ("GOALS_x_CARDS", "total_goals_over_2.5", "total_cards_over_4.5"),
             ("SOT_x_CORNERS", "total_sot_over_8.5", "total_corners_over_9.5"), ("SOT_x_CARDS", "total_sot_over_8.5", "total_cards_over_4.5")]
    season = np.where(d.MatchDate.dt.month >= 7, d.MatchDate.dt.year, d.MatchDate.dt.year - 1)
    div = d.Division.to_numpy()
    rng = np.random.default_rng(SEED)

    def ratio(a, b):
        pa, pb, j = a.mean(), b.mean(), (a & b).mean()
        return j / (pa * pb) if pa * pb > 0 else np.nan

    res = {"label": "DESCRIPTIVE (sporting dependency only; no prices, no SGM claims, no betting rules)", "n": int(len(d)),
           "window": f"{START}..{END}", "pairs": {}}
    for name, ka, kb in pairs:
        a, b = ev[ka].astype(bool), ev[kb].astype(bool)
        r = ratio(a, b)
        n = len(a)
        bs = []
        for _ in range(BOOT):
            i = rng.integers(0, n, n)
            bs.append(ratio(a[i], b[i]))
        side = np.sign(r - 1)
        by_s = {int(s): ratio(a[season == s], b[season == s]) for s in np.unique(season)}
        by_l = {str(x): ratio(a[div == x], b[div == x]) for x in DIVS}
        res["pairs"][name] = {
            "A": ka, "B": kb, "n": int(n), "P_A": round(float(a.mean()), 4), "P_B": round(float(b.mean()), 4),
            "P_AB": round(float((a & b).mean()), 4), "P_A_x_P_B": round(float(a.mean() * b.mean()), 4), "ratio": round(float(r), 4),
            "ratio_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "P_B_given_A": round(float(b[a].mean()), 4), "P_B_given_notA": round(float(b[~a].mean()), 4),
            "season_ratio_min_max": [round(min(by_s.values()), 3), round(max(by_s.values()), 3)],
            "season_share_same_side": round(float(np.mean([np.sign(v - 1) == side for v in by_s.values()])), 3),
            "league_ratio_min_max": [round(min(by_l.values()), 3), round(max(by_l.values()), 3)],
            "league_share_same_side": round(float(np.mean([np.sign(v - 1) == side for v in by_l.values()])), 3)}
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    for k, v in res["pairs"].items():
        print(k, v["n"], v["P_A"], v["P_B"], v["P_AB"], v["P_A_x_P_B"], v["ratio"], v["ratio_ci95"], v["P_B_given_A"], v["P_B_given_notA"],
              v["season_ratio_min_max"], v["season_share_same_side"], v["league_ratio_min_max"], v["league_share_same_side"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
