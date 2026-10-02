"""Props C1 / Track D: descriptive winner+team-prop dependency on held data (no prices, no betting claim).

Post-match result is used ONLY to characterise historical joint behaviour, never as a predictor.
Usage: python scripts/props_c1_dependency.py <Matches.csv>  ->  research/platform_v2/props_c1/DEPENDENCY.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "research/platform_v2/props_c1/DEPENDENCY.json"
DIVS = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1"]
START = "2022-07-01"


def main(path: str) -> int:
    d = pd.read_csv(path, low_memory=False, parse_dates=["MatchDate"])
    d = d[d.Division.isin(DIVS) & (d.MatchDate >= START)].dropna(
        subset=["HomeCorners", "AwayCorners", "HomeYellow", "AwayYellow", "HomeTarget", "AwayTarget", "OddHome", "OddDraw", "OddAway"])
    inv = 1 / d[["OddHome", "OddDraw", "OddAway"]]
    fav_home = (inv.OddHome >= inv.OddAway).to_numpy()
    fav_win = np.where(fav_home, d.FTResult == "H", d.FTResult == "A")
    cards = d.HomeYellow + d.AwayYellow + d.HomeRed.fillna(0) + d.AwayRed.fillna(0)
    events = {"total_corners_over_9.5": (d.HomeCorners + d.AwayCorners > 9.5).to_numpy(),
              "total_cards_over_4.5": (cards > 4.5).to_numpy(),
              "favourite_team_sot_over_4.5": np.where(fav_home, d.HomeTarget, d.AwayTarget) > 4.5}
    out = {"n_matches": int(len(d)), "window": f">= {START}", "divisions": DIVS, "p_favourite_win": round(float(fav_win.mean()), 4), "events": {}}
    for k, ev in events.items():
        p, pf, j = ev.mean(), fav_win.mean(), (ev & fav_win).mean()
        out["events"][k] = {"p": round(float(p), 4), "p_given_fav_win": round(float(ev[fav_win].mean()), 4),
                            "p_given_not_fav_win": round(float(ev[~fav_win].mean()), 4), "p_joint": round(float(j), 4),
                            "p_if_independent": round(float(p * pf), 4), "joint_over_independent": round(float(j / (p * pf)), 4)}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
