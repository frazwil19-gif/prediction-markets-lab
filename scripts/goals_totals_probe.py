"""EXPLORATORY goals / team-totals predictability probe (plan: research/platform_v2/goals_totals/EXPLORATORY_PLAN.md).

Usage: python scripts/goals_totals_probe.py <Matches.csv>  -> research/platform_v2/goals_totals/PROBE.json
Development window only (2019-20 .. 2023-24); nothing from 2024-07 onward is evaluated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

OUT = Path(__file__).resolve().parents[1] / "research/platform_v2/goals_totals/PROBE.json"
DIVS = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1"]
SEASONS = [2019, 2020, 2021, 2022, 2023]
TRAIN_START = pd.Timestamp("2005-07-01")
WIN, MINP, LWIN, LMIN = 10, 3, 380, 50
BOOT, SEED = 1000, 7
NEAR = 0.002
TARGETS = {"home_over_0.5": ("H", 0.5), "home_over_1.5": ("H", 1.5), "away_over_0.5": ("A", 0.5), "away_over_1.5": ("A", 1.5),
           "total_over_1.5": ("T", 1.5), "total_over_3.5": ("T", 3.5)}
MAXG = 15


def build(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, low_memory=False, parse_dates=["MatchDate"],
                    usecols=["Division", "MatchDate", "HomeTeam", "AwayTeam", "HomeElo", "AwayElo", "FTHome", "FTAway", "HomeShots", "AwayShots",
                             "HomeTarget", "AwayTarget", "OddHome", "OddDraw", "OddAway", "Over25", "Under25"])
    d = d.dropna(subset=["FTHome", "FTAway"]).sort_values(["MatchDate", "Division", "HomeTeam"]).reset_index(drop=True)
    d["mid"] = np.arange(len(d))
    cols = {"g": ("FTHome", "FTAway"), "s": ("HomeShots", "AwayShots"), "t": ("HomeTarget", "AwayTarget")}
    h = pd.DataFrame({"mid": d.mid, "date": d.MatchDate, "team": d.HomeTeam, "v": "h"})
    a = pd.DataFrame({"mid": d.mid, "date": d.MatchDate, "team": d.AwayTeam, "v": "a"})
    for k, (hc, ac) in cols.items():
        h[k + "f"], h[k + "a"], a[k + "f"], a[k + "a"] = d[hc].values, d[ac].values, d[ac].values, d[hc].values
    L = pd.concat([h, a]).sort_values(["date", "mid", "v"])
    g = L.groupby("team", sort=False)
    for c in ("gf", "ga", "sf", "sa", "tf", "ta"):
        L["r" + c] = g[c].transform(lambda s: s.shift(1).rolling(WIN, min_periods=MINP).mean())
        L["r" + c] = L["r" + c].fillna(L[c].shift(1).expanding().mean())
    H, A = L[L.v == "h"].set_index("mid").sort_index(), L[L.v == "a"].set_index("mid").sort_index()
    for c in ("gf", "ga", "sf", "sa", "tf", "ta"):
        d["h_" + c], d["a_" + c] = H["r" + c].values, A["r" + c].values
    d["elo_diff"] = (d.HomeElo - d.AwayElo) / 100
    d["lm_H"] = d.groupby("Division").FTHome.transform(lambda s: s.shift(1).rolling(LWIN, min_periods=LMIN).mean())
    d["lm_A"] = d.groupby("Division").FTAway.transform(lambda s: s.shift(1).rolling(LWIN, min_periods=LMIN).mean())
    d["season"] = np.where(d.MatchDate.dt.month >= 7, d.MatchDate.dt.year, d.MatchDate.dt.year - 1)
    ev = d[d.Division.isin(DIVS) & (d.MatchDate >= TRAIN_START)].dropna(subset=["lm_H", "lm_A", "elo_diff", "h_sf", "h_tf"]).copy()
    return ev.reset_index(drop=True)


def X(df: pd.DataFrame, side: str) -> np.ndarray:
    o = "a" if side == "h" else "h"
    cols = [np.ones(len(df)), np.log(df[f"lm_{side.upper()}"])]
    for c in (f"{side}_gf", f"{o}_ga", f"{side}_sf", f"{o}_sa", f"{side}_tf", f"{o}_ta", f"{side}_ga", f"{o}_gf"):
        cols.append(np.log(np.clip(df[c].to_numpy(float), 0.05, None)))
    cols.append(df.elo_diff.to_numpy(float) * (1 if side == "h" else -1))
    return np.column_stack(cols)


def pois_fit(Xm: np.ndarray, y: np.ndarray) -> np.ndarray:
    b = np.zeros(Xm.shape[1])
    b[0] = np.log(y.mean())
    for _ in range(100):
        mu = np.exp(np.clip(Xm @ b, -10, 10))
        new = np.linalg.solve(Xm.T @ (Xm * mu[:, None]) + 1e-8 * np.eye(Xm.shape[1]), Xm.T @ (mu * (Xm @ b + (y - mu) / mu)))
        if np.max(np.abs(new - b)) < 1e-9:
            return new
        b = new
    return b


def market_lambdas(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    i = 1 / df[["OddHome", "OddDraw", "OddAway"]].to_numpy(float)
    p = i / i.sum(axis=1, keepdims=True)
    o = 1 / df[["Over25", "Under25"]].to_numpy(float)
    po = o[:, 0] / o.sum(axis=1)
    k = np.arange(MAXG)
    lh, la = np.full(len(df), np.nan), np.full(len(df), np.nan)
    for j in range(len(df)):
        if not np.isfinite(p[j]).all() or not np.isfinite(po[j]):
            continue
        def loss(x):
            a_, b_ = np.exp(x)
            ph, pa = stats.poisson.pmf(k, a_), stats.poisson.pmf(k, b_)
            m = np.outer(ph, pa)
            hw, dr, aw = np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum()
            tot = np.add.outer(k, k)
            ov = m[tot > 2.5].sum()
            return (hw - p[j, 0]) ** 2 + (dr - p[j, 1]) ** 2 + (aw - p[j, 2]) ** 2 + (ov - po[j]) ** 2
        r = optimize.minimize(loss, np.log([1.4, 1.1]), method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-10})
        lh[j], la[j] = np.exp(r.x)
    return lh, la


def probs(lh: np.ndarray, la: np.ndarray) -> dict[str, np.ndarray]:
    out = {"home_over_0.5": 1 - np.exp(-lh), "home_over_1.5": 1 - np.exp(-lh) * (1 + lh),
           "away_over_0.5": 1 - np.exp(-la), "away_over_1.5": 1 - np.exp(-la) * (1 + la)}
    lt = lh + la
    out["total_over_1.5"] = 1 - stats.poisson.cdf(1, lt)
    out["total_over_3.5"] = 1 - stats.poisson.cdf(3, lt)
    return {k: np.clip(v, 1e-9, 1 - 1e-9) for k, v in out.items()}


def ll(y, p):
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def slope(y, p):
    x = np.log(p / (1 - p))
    Xm = np.column_stack([np.ones_like(x), x])
    b = np.array([0.0, 1.0])
    for _ in range(50):
        q = 1 / (1 + np.exp(-(Xm @ b)))
        b = b + np.linalg.solve(Xm.T @ (Xm * (q * (1 - q))[:, None]), Xm.T @ (y - q))
    return round(float(b[1]), 3)


def ci(diff, rng):
    n = len(diff)
    m = [diff[rng.integers(0, n, n)].mean() for _ in range(BOOT)]
    return [round(float(np.percentile(m, 2.5)), 5), round(float(np.percentile(m, 97.5)), 5)]


def main(path: str) -> int:
    ev = build(path)
    P = {m: {t: [] for t in TARGETS} for m in ("N0", "D1", "M1")}
    Y = {t: [] for t in TARGETS}
    for s in SEASONS:
        tr = ev[ev.MatchDate < pd.Timestamp(f"{s}-07-01")]
        te = ev[ev.season == s].dropna(subset=["OddHome", "OddDraw", "OddAway", "Over25", "Under25"])
        bh, ba = pois_fit(X(tr, "h"), tr.FTHome.to_numpy(float)), pois_fit(X(tr, "a"), tr.FTAway.to_numpy(float))
        lhD, laD = np.exp(X(te, "h") @ bh), np.exp(X(te, "a") @ ba)
        lhM, laM = market_lambdas(te)
        ok = np.isfinite(lhM)
        te, lhD, laD, lhM, laM = te[ok], lhD[ok], laD[ok], lhM[ok], laM[ok]
        for m, (a_, b_) in {"N0": (te.lm_H.to_numpy(), te.lm_A.to_numpy()), "D1": (lhD, laD), "M1": (lhM, laM)}.items():
            for t, v in probs(a_, b_).items():
                P[m][t].append(v)
        yv = {"H": te.FTHome.to_numpy(), "A": te.FTAway.to_numpy(), "T": (te.FTHome + te.FTAway).to_numpy()}
        for t, (side, line) in TARGETS.items():
            Y[t].append((yv[side] > line).astype(float))
    rng = np.random.default_rng(SEED)
    res = {"label": "EXPLORATORY", "window": "walk-forward seasons 2019-20..2023-24", "targets": {}}
    for t in TARGETS:
        y = np.concatenate(Y[t])
        p = {m: np.concatenate(P[m][t]) for m in P}
        L = {m: ll(y, p[m]) for m in p}
        dn, dm = L["D1"] - L["N0"], L["D1"] - L["M1"]
        just = bool(ci(dn, rng)[1] < 0 and dm.mean() <= NEAR)
        res["targets"][t] = {"n": int(len(y)), "base_rate": round(float(y.mean()), 4),
                             **{f"logloss_{m}": round(float(v.mean()), 5) for m, v in L.items()},
                             **{f"brier_{m}": round(float(((p[m] - y) ** 2).mean()), 5) for m in p},
                             **{f"slope_{m}": slope(y, p[m]) for m in p},
                             "d_D1_minus_N0": round(float(dn.mean()), 5), "ci_D1_minus_N0": ci(dn, rng),
                             "d_D1_minus_M1": round(float(dm.mean()), 5), "ci_D1_minus_M1": ci(dm, rng),
                             "full_cycle_justified_by_rule": just}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
