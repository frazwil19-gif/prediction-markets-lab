"""Props Cycle 1 bounded predictability probe (pre-registered: research/platform_v2/props_c1/PREREGISTRATION.md).

Research only. Usage: python scripts/props_c1_probe.py <path/to/xgabora/Matches.csv>
Writes research/platform_v2/props_c1/PROBE_RESULTS.json and PROBE_TABLE.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

OUT = Path(__file__).resolve().parents[1] / "research/platform_v2/props_c1"
DIVS = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1"]
SPLIT = pd.Timestamp("2022-07-01")
WIN, MINP, LEAGUE_WIN = 10, 5, 380
BOOT, SEED = 1000, 7
NB_THRESHOLD = 1.15

TARGETS = {  # name: (home stat col, away stat col, how target built, lines)
    "total_corners": ("HomeCorners", "AwayCorners", "sum", (9.5, 10.5)),
    "total_cards": (("HomeYellow", "HomeRed"), ("AwayYellow", "AwayRed"), "sum", (3.5, 4.5)),
    "home_sot": ("HomeTarget", "AwayTarget", "home", (4.5,)),
    "away_sot": ("HomeTarget", "AwayTarget", "away", (4.5,)),
}


def load(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, low_memory=False, parse_dates=["MatchDate"])
    d = d[d.Division.isin(DIVS)].sort_values(["MatchDate", "Division", "HomeTeam"]).reset_index(drop=True)
    d["mid"] = np.arange(len(d))
    d["h_cards"] = d.HomeYellow + d.HomeRed.fillna(0)
    d["a_cards"] = d.AwayYellow + d.AwayRed.fillna(0)
    return d


def team_rolling(d: pd.DataFrame, hcol: str, acol: str) -> pd.DataFrame:
    """Per team, rolling mean of stat-for / stat-against over its previous WIN league matches (shifted: prior only)."""
    long = pd.concat([
        pd.DataFrame({"mid": d.mid, "date": d.MatchDate, "div": d.Division, "team": d.HomeTeam, "side": "h", "f": d[hcol], "a": d[acol]}),
        pd.DataFrame({"mid": d.mid, "date": d.MatchDate, "div": d.Division, "team": d.AwayTeam, "side": "a", "f": d[acol], "a": d[hcol]}),
    ]).sort_values(["date", "mid"])
    g = long.groupby(["div", "team"])
    for c in ("f", "a"):
        long[f"r_{c}"] = g[c].transform(lambda s: s.shift(1).rolling(WIN, min_periods=MINP).mean())
    h = long[long.side == "h"].set_index("mid")[["r_f", "r_a"]].add_prefix("h_")
    a = long[long.side == "a"].set_index("mid")[["r_f", "r_a"]].add_prefix("a_")
    return h.join(a)


def frame(d: pd.DataFrame, name: str) -> pd.DataFrame:
    hc, ac, how, _ = TARGETS[name]
    if name == "total_cards":
        hcol, acol = "h_cards", "a_cards"
    else:
        hcol, acol = hc, ac
    x = d[d[hcol].notna() & d[acol].notna()].copy()
    x["y"] = {"sum": x[hcol] + x[acol], "home": x[hcol], "away": x[acol]}[how]
    x = x.join(team_rolling(x, hcol, acol), on="mid")
    x["league_mean"] = x.groupby("Division").y.transform(lambda s: s.shift(1).rolling(LEAGUE_WIN, min_periods=100).mean())
    x["elo_diff"] = (x.HomeElo - x.AwayElo) / 100
    inv = 1 / x[["OddHome", "OddDraw", "OddAway"]]
    x["mk_home"] = inv.OddHome / inv.sum(axis=1)
    x["mk_o25"] = (1 / x.Over25) / (1 / x.Over25 + 1 / x.Under25)
    if how == "sum":
        x["f1"], x["f2"] = x.h_r_f + x.a_r_f, x.h_r_a + x.a_r_a
    elif how == "home":
        x["f1"], x["f2"] = x.h_r_f, x.a_r_a
    else:
        x["f1"], x["f2"] = x.a_r_f, x.h_r_a
    x["mk_fav"] = (x.mk_home - 0.45).abs()
    return x


def poisson_glm(X: np.ndarray, y: np.ndarray, iters: int = 50) -> np.ndarray:
    """Log-link Poisson GLM by IRLS (no extra dependency). X includes the constant column."""
    beta = np.zeros(X.shape[1])
    beta[0] = np.log(y.mean())
    for _ in range(iters):
        mu = np.exp(X @ beta)
        z = X @ beta + (y - mu) / mu
        w = mu
        new = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (w * z))
        if np.max(np.abs(new - beta)) < 1e-10:
            return new
        beta = new
    return beta


def design(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return np.column_stack([np.ones(len(df)), df[cols].to_numpy(float)])


def p_over(mu: np.ndarray, line: float, alpha: float | None = None) -> np.ndarray:
    k = int(np.floor(line))
    if alpha is None:
        return 1 - stats.poisson.cdf(k, mu)
    n = 1 / alpha
    return 1 - stats.nbinom.cdf(k, n, n / (n + mu))


def ll(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def boot_ci(diff: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    n = len(diff)
    m = [diff[rng.integers(0, n, n)].mean() for _ in range(BOOT)]
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def calib_gap(y: np.ndarray, p: np.ndarray) -> float:
    q = pd.qcut(p, 10, duplicates="drop")
    t = pd.DataFrame({"y": y, "p": p, "q": q}).groupby("q", observed=True).mean()
    return float((t.y - t.p).abs().max())


def run(path: str) -> dict:
    d = load(path)
    rng = np.random.default_rng(SEED)
    res, table = {}, []
    for name, (_, _, _, lines) in TARGETS.items():
        x = frame(d, name)
        base = ["f1", "f2", "league_mean", "elo_diff"]
        mkt = base + ["mk_home", "mk_fav", "mk_o25"]
        x = x.dropna(subset=mkt + ["y"])
        tr, te = x[x.MatchDate < SPLIT], x[x.MatchDate >= SPLIT]
        mus, disp = {"M0": te.league_mean.to_numpy()}, {}
        alphas = {}
        for m, cols in (("M1", base), ("M2", mkt)):
            Xtr, ytr = design(tr, cols), tr.y.to_numpy(float)
            beta = poisson_glm(Xtr, ytr)
            mtr = np.exp(Xtr @ beta)
            mus[m] = np.exp(design(te, cols) @ beta)
            disp[m] = float((((ytr - mtr) ** 2) / mtr).sum() / (len(ytr) - Xtr.shape[1]))
            if disp[m] > NB_THRESHOLD:   # NB2 with the same (quasi-likelihood) mean; alpha by moments on train
                a = max(float((((ytr - mtr) ** 2 - mtr) / mtr ** 2).mean()), 1e-4)
                mus[m + "nb"] = mus[m]
                alphas[m + "nb"] = a
        y = te.y.to_numpy()
        r = {"n_train": int(len(tr)), "n_test": int(len(te)), "test_mean": round(float(y.mean()), 3),
             "test_var_over_mean": round(float(y.var() / y.mean()), 3), "pearson_dispersion": {k: round(v, 3) for k, v in disp.items()},
             "corr_mu_y": {m: round(float(np.corrcoef(mu, y)[0, 1]), 4) for m, mu in mus.items()}, "lines": {}}
        for line in lines:
            yb = (y > line).astype(float)
            ps = {m: p_over(mu, line, alphas.get(m)) for m, mu in mus.items()}
            l0 = ll(yb, ps["M0"])
            lr = {"base_rate": round(float(yb.mean()), 4)}
            for m, p in ps.items():
                lm = ll(yb, p)
                row = {"logloss": round(float(lm.mean()), 5), "brier": round(float(((p - yb) ** 2).mean()), 5),
                       "calib_max_gap": round(calib_gap(yb, p), 4), "mean_p": round(float(p.mean()), 4)}
                if m != "M0":
                    lo, hi = boot_ci(lm - l0, rng)
                    row.update({"d_logloss_vs_M0": round(float((lm - l0).mean()), 5), "ci95": [round(lo, 5), round(hi, 5)]})
                lr[m] = row
                table.append({"target": name, "line": line, "model": m, **{k: v for k, v in row.items() if k != "ci95"},
                              "ci_lo": row.get("ci95", [None, None])[0], "ci_hi": row.get("ci95", [None, None])[1]})
            ref = "M1nb" if "M1nb" in lr else "M1"
            lr["predictable_beyond_baseline_M1"] = bool(lr["M1"]["ci95"][1] < 0)
            lr["note_secondary_nb"] = ref == "M1nb"
            r["lines"][str(line)] = lr
        res[name] = r
    return {"preregistration": "research/platform_v2/props_c1/PREREGISTRATION.md", "divisions": DIVS,
            "split": str(SPLIT.date()), "results": res, "_table": table}


def main() -> int:
    out = run(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out.pop("_table")).to_csv(OUT / "PROBE_TABLE.csv", index=False)
    (OUT / "PROBE_RESULTS.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
