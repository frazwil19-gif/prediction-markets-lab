"""Final football coverage: monthly Odds API credit model (reproducible; exposed fixture dates only, no outcomes).

Usage: python scripts/football_coverage_credit_model.py --data <xgabora Matches.csv>
Source pin: research/platform_v2/v2_18_expansion/RESULTS.json (xgabora/Club-Football-Match-Data@25882a58, sha256 ef224cf2...).
A 07:00 UTC daily scan pays for a league when a fixture kicks off within the 48h gate: fixtures on day t (after 07:00),
t+1 or t+2. (V2-18 counted only t+1/t+2 and therefore UNDER-counted paying days by ~25%; corrected here.)
Credits per paying day = number of paid markets (config/football_coverage.yaml). Seasons 2023/24-2025/26.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/football_coverage"
OTHER_EXPECTED = {"tennis": 95, "nba": 60, "legacy_settlement": 10}   # observed 3.1/day; NBA plan; Plan A midpoint
OTHER_HIGH = {"tennis": 150, "nba": 60, "legacy_settlement": 20}      # consumer caps
SCENARIOS = {"A_current_as_merged": (["E0", "E1", "SC0", "N1", "D1"], {"N1": 2, "D1": 2}),
             "A_core_recommended": (["E0", "E1", "SC0", "N1", "D1"], {}),
             "A_core_plus_F1_recommended_tier1": (["E0", "E1", "SC0", "N1", "D1", "F1"], {}),
             "B_top5_plus_core": (["E0", "E1", "SC0", "N1", "D1", "SP1", "I1", "F1"], {}),
             "C_major_europe": (["E0", "E1", "SC0", "N1", "D1", "SP1", "I1", "F1", "P1", "B1"], {}),
             "D_full_target": (["E0", "E1", "SC0", "N1", "D1", "SP1", "I1", "F1", "P1", "B1", "E2", "E3", "SP2", "D2", "I2", "F2"], {})}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    a = ap.parse_args()
    cov = {r["code"]: r for r in yaml.safe_load((REPO / "config/football_coverage.yaml").read_text())["leagues"]}
    summ = pd.read_csv(REPO / "research/platform_v2/v2_18_expansion/LEAGUE_SUMMARY.csv").set_index("league")
    d = pd.read_csv(a.data, low_memory=False, usecols=["Division", "MatchDate"])
    d["date"] = pd.to_datetime(d.MatchDate)
    d = d[d.Division.isin(list(cov)) & (d.date >= "2023-07-01") & (d.date < "2026-07-01")]
    months = pd.period_range("2023-07", "2026-06", freq="M")
    pay = {}
    for lg in cov:
        days = pd.to_datetime(sorted(d[d.Division == lg].date.dt.normalize().unique()))
        s = {x - pd.Timedelta(days=k) for x in days for k in (0, 1, 2)}
        ser = pd.Series(1, index=pd.DatetimeIndex(sorted(s)))
        pay[lg] = ser.groupby(ser.index.to_period("M")).sum().reindex(months, fill_value=0)
    P = pd.DataFrame(pay)
    ins = [m.month not in (6, 7) for m in P.index]
    cr = lambda lg, ov: ov.get(lg, max(len(cov[lg]["markets"]), 1))
    out = {"per_league": {}, "scenarios": {}, "assumptions": {"other_expected": OTHER_EXPECTED, "other_high": OTHER_HIGH,
           "hard_limit": 500, "in_season_months": "Aug-May", "seasons": "2023/24-2025/26"}}
    for lg in cov:
        c = cr(lg, {})
        out["per_league"][lg] = {"credits_per_paying_day": c, "expected_month": round(float(P[lg][ins].mean() * c), 1),
                                 "high_month": int(P[lg].max() * c), "strong_ge70_per_season": float(summ.loc[lg, "top1x2_ge70_per_season"])}
    for k, (lgs, ov) in SCENARIOS.items():
        m = sum(P[lg] * cr(lg, ov) for lg in lgs)
        fe, fh = float(m[ins].mean()), int(m.max())
        te, th = fe + sum(OTHER_EXPECTED.values()), fh + sum(OTHER_HIGH.values())
        strong = float(summ.loc[lgs, "top1x2_ge70_per_season"].sum())
        out["scenarios"][k] = {"leagues": lgs, "football_expected": round(fe, 1), "football_high": fh,
                               "total_expected": round(te), "total_high": th, "reserve_expected": round(500 - te),
                               "reserve_high": 500 - th, "strong_1x2_per_season": round(strong, 1)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "CREDIT_MODEL.json").write_text(json.dumps(out, indent=1))
    P.to_csv(OUT / "paying_days_by_month.csv")
    print(json.dumps(out["scenarios"], indent=1))


if __name__ == "__main__":
    main()
