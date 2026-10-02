"""Corners Cycle 1 — Phase 1 descriptive data audit (pre-registered: research/platform_v2/props_c1/corners/PREREGISTRATION.md).

No modelling, no feature selection. Usage: python scripts/corners_c1_audit.py <Matches.csv>
Writes research/platform_v2/props_c1/corners/AUDIT.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "research/platform_v2/props_c1/corners/AUDIT.json"
DIVS = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1"]
TOTAL_LINES = [7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5]
TEAM_LINES = [3.5, 4.5, 5.5, 6.5]
IMPLAUSIBLE = 25          # a single team's corners above this is flagged as an anomaly


def season(d: pd.Timestamp) -> str:
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def run(path: str) -> dict:
    raw = pd.read_csv(path, low_memory=False, parse_dates=["MatchDate"])
    d = raw[raw.Division.isin(DIVS)].copy()
    d["season"] = d.MatchDate.map(season)
    has = d.HomeCorners.notna() & d.AwayCorners.notna()
    out: dict = {"source": Path(path).name, "divisions": DIVS, "rows_in_divisions": int(len(d)), "rows_with_corners": int(has.sum())}

    # coverage / missingness
    cov = d.groupby(["Division", "season"]).apply(lambda g: pd.Series({"n": len(g), "with_corners": int((g.HomeCorners.notna() & g.AwayCorners.notna()).sum())}),
                                                  include_groups=False)
    first = {div: (cov.loc[div][cov.loc[div].with_corners > 0].index.min() if (cov.loc[div].with_corners > 0).any() else None) for div in DIVS}
    after_first = {div: cov.loc[div].loc[first[div]:] for div in DIVS if first[div]}
    out["first_season_with_corners"] = first
    out["missing_share_after_first_season"] = {div: round(float(1 - t.with_corners.sum() / t.n.sum()), 4) for div, t in after_first.items()}
    out["seasons_with_partial_coverage"] = {div: [s for s, r in t.iterrows() if 0 < r.with_corners < r.n] for div, t in after_first.items()}
    out["n_by_league"] = {div: int(t.with_corners.sum()) for div, t in after_first.items()}
    out["n_by_season_all_leagues"] = {s: int(v) for s, v in cov.groupby(level="season").with_corners.sum().items() if v}

    c = d[has].copy()
    c["total"] = c.HomeCorners + c.AwayCorners

    # anomalies / definition consistency
    out["anomalies"] = {
        "negative": int(((c.HomeCorners < 0) | (c.AwayCorners < 0)).sum()),
        "non_integer": int(((c.HomeCorners % 1 != 0) | (c.AwayCorners % 1 != 0)).sum()),
        f"team_over_{IMPLAUSIBLE}": int(((c.HomeCorners > IMPLAUSIBLE) | (c.AwayCorners > IMPLAUSIBLE)).sum()),
        "total_zero": int((c.total == 0).sum()),
        "duplicate_division_date_teams": int(c.duplicated(["Division", "MatchDate", "HomeTeam", "AwayTeam"]).sum()),
        "league_seasons_all_zero_or_constant": [f"{k[0]} {k[1]}" for k, g in c.groupby(["Division", "season"]) if g.total.nunique() <= 1],
    }
    ls = c.groupby(["Division", "season"]).total.mean()
    z = ls.groupby(level="Division").transform(lambda s: (s - s.median()) / (s.std() or 1))
    out["anomalies"]["league_season_mean_outliers_|z|>3"] = {f"{k[0]} {k[1]}": round(float(ls[k]), 2) for k in z[z.abs() > 3].index}

    # distribution
    def desc(s: pd.Series) -> dict:
        return {"n": int(len(s)), "mean": round(float(s.mean()), 3), "var": round(float(s.var()), 3),
                "var_over_mean": round(float(s.var() / s.mean()), 3), "p05": float(s.quantile(.05)), "median": float(s.median()),
                "p95": float(s.quantile(.95)), "max": float(s.max())}
    out["distribution"] = {"total": desc(c.total), "home": desc(c.HomeCorners), "away": desc(c.AwayCorners)}
    out["home_away_structure"] = {"home_share_of_total": round(float(c.HomeCorners.sum() / c.total.sum()), 4),
                                  "corr_home_away": round(float(np.corrcoef(c.HomeCorners, c.AwayCorners)[0, 1]), 4)}
    out["by_league"] = {div: {**desc(g.total), "home_share": round(float(g.HomeCorners.sum() / g.total.sum()), 4)} for div, g in c.groupby("Division")}
    recent = c[c.MatchDate >= "2015-07-01"]
    out["temporal_drift"] = {
        "season_mean_total_all_leagues": {s: round(float(v), 3) for s, v in c.groupby("season").total.mean().items()},
        "slope_per_season_since_2015_by_league": {div: round(float(np.polyfit(np.arange(len(g)), g.values, 1)[0]), 4)
                                                  for div, g in recent.groupby(["Division", "season"]).total.mean().groupby(level="Division") if len(g) >= 3},
    }
    out["line_frequencies_total"] = {str(L): round(float((c.total > L).mean()), 4) for L in TOTAL_LINES}
    out["line_frequencies_total_by_league"] = {div: {str(L): round(float((g.total > L).mean()), 3) for L in TOTAL_LINES} for div, g in c.groupby("Division")}
    out["line_frequencies_team"] = {"home": {str(L): round(float((c.HomeCorners > L).mean()), 4) for L in TEAM_LINES},
                                    "away": {str(L): round(float((c.AwayCorners > L).mean()), 4) for L in TEAM_LINES}}
    out["shots_available_share"] = round(float((c.HomeShots.notna() & c.HomeTarget.notna()).mean()), 4)
    out["note"] = "Phase 1 is descriptive only; not used to select features (pre-registration)."
    return out


def main() -> int:
    out = run(sys.argv[1])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: out[k] for k in ("rows_with_corners", "first_season_with_corners", "missing_share_after_first_season",
                                          "seasons_with_partial_coverage", "anomalies", "distribution", "home_away_structure",
                                          "line_frequencies_total")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
