"""Corners Model A — sports-only probability model (pre-registered: research/platform_v2/props_c1/corners/MODEL_A_PREREGISTRATION.md).

Research only; no bookmaker prices of any kind are used. Modes:
  python scripts/corners_model_a.py discovery <Matches.csv>   -> DISCOVERY.json (exploratory, 2005-07..2019-06 only)
  python scripts/corners_model_a.py develop   <Matches.csv>   -> DEVELOPMENT.json (walk-forward folds 2019-20..2023-24)
  python scripts/corners_model_a.py holdout   <Matches.csv>   -> HOLDOUT.json (once; needs committed FROZEN_SPEC.json)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, special, stats

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/props_c1/corners/model_a"
DIVS = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1"]
EVAL_START = pd.Timestamp("2005-07-01")
DISCOVERY_END = pd.Timestamp("2019-07-01")
DEV_SEASONS = [2019, 2020, 2021, 2022, 2023]          # season start years
HOLDOUT_START = pd.Timestamp("2024-07-01")
LINES = [7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5]
PRIMARY_LINES = [8.5, 9.5, 10.5, 11.5]
TEAM_LINES = [3.5, 4.5, 5.5, 6.5]
MINP, LEAGUE_WIN, LEAGUE_MINP, REST_CAP = 3, 380, 50, 14
SEL_GAIN, SEL_FOLDS, SEL_MAX = 0.0005, 4, 6
FAMILY_TOL = 0.0005
MC_DRAWS, MC_SEED, MC_MIX = 20000, 11, 1e-3            # MC_MIX: weight of the independent pmf to avoid zero mass
BOOT, BOOT_SEED = 1000, 7
MATERIAL = -0.001
GRID = np.arange(0, 41)
GROUPS = {
    "G1_corners5": ["h_cf5", "h_ca5", "a_cf5", "a_ca5"],
    "G2_corners10": ["h_cf10", "h_ca10", "a_cf10", "a_ca10"],
    "G3_corners20": ["h_cf20", "h_ca20", "a_cf20", "a_ca20"],
    "G4_venue10": ["h_hcf10", "h_hca10", "a_acf10", "a_aca10"],
    "G5_shots10": ["h_sf10", "h_sa10", "a_sf10", "a_sa10"],
    "G6_sot10": ["h_tf10", "h_ta10", "a_tf10", "a_ta10"],
    "G7_goals10": ["h_gf10", "h_ga10", "a_gf10", "a_ga10"],
    "G8_elo": ["elo_diff", "elo_level"],
    "G9_rest": ["h_rest", "a_rest"],
    "G10_stage": ["stage"],
    "G11_league": [f"div_{d}" for d in DIVS[1:]],
}
LOG_COLS = {c for g in ("G1_corners5", "G2_corners10", "G3_corners20", "G4_venue10", "G5_shots10", "G6_sot10", "G7_goals10") for c in GROUPS[g]}


# ------------------------------------------------------------------ data
def season_start(d: pd.Series) -> pd.Series:
    return np.where(d.dt.month >= 7, d.dt.year, d.dt.year - 1)


def build(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, low_memory=False, parse_dates=["MatchDate"],
                      usecols=["Division", "MatchDate", "HomeTeam", "AwayTeam", "HomeElo", "AwayElo", "FTHome", "FTAway",
                               "HomeShots", "AwayShots", "HomeTarget", "AwayTarget", "HomeCorners", "AwayCorners"])
    d = raw[raw.HomeCorners.notna() & raw.AwayCorners.notna()].sort_values(["MatchDate", "Division", "HomeTeam"]).reset_index(drop=True)
    d["mid"] = np.arange(len(d))
    d["T"] = d.HomeCorners + d.AwayCorners
    stats_ = {"c": ("HomeCorners", "AwayCorners"), "s": ("HomeShots", "AwayShots"), "t": ("HomeTarget", "AwayTarget"), "g": ("FTHome", "FTAway")}
    h = pd.DataFrame({"mid": d.mid, "date": d.MatchDate, "div": d.Division, "team": d.HomeTeam, "venue": "h", "elo": d.HomeElo})
    a = pd.DataFrame({"mid": d.mid, "date": d.MatchDate, "div": d.Division, "team": d.AwayTeam, "venue": "a", "elo": d.AwayElo})
    for k, (hc, ac) in stats_.items():
        h[k + "f"], h[k + "a"], a[k + "f"], a[k + "a"] = d[hc].values, d[ac].values, d[ac].values, d[hc].values
    L = pd.concat([h, a]).sort_values(["date", "mid", "venue"]).reset_index(drop=True)
    g = L.groupby("team", sort=False)
    roll = lambda col, w: g[col].transform(lambda s: s.shift(1).rolling(w, min_periods=MINP).mean())
    for w in (5, 10, 20):
        L[f"cf{w}"], L[f"ca{w}"] = roll("cf", w), roll("ca", w)
    for k in ("s", "t", "g"):
        L[f"{k}f10"], L[f"{k}a10"] = roll(k + "f", 10), roll(k + "a", 10)
    gv = L.groupby(["team", "venue"], sort=False)
    L["vcf10"] = gv["cf"].transform(lambda s: s.shift(1).rolling(10, min_periods=MINP).mean())
    L["vca10"] = gv["ca"].transform(lambda s: s.shift(1).rolling(10, min_periods=MINP).mean())
    L["rest"] = np.log1p(g["date"].diff().dt.days.clip(upper=REST_CAP).fillna(REST_CAP))
    L["elo"] = g["elo"].transform(lambda s: s.ffill())
    # division prior means for filling (per-team-match level)
    for k in ("c", "s", "t", "g"):
        L[f"div_{k}"] = L.groupby("div")[k + "f"].transform(lambda s: s.shift(1).rolling(2 * LEAGUE_WIN, min_periods=LEAGUE_MINP).mean())
        for col in [c for c in L.columns if c.startswith(k) and c[-1].isdigit()] + ([f"v{k}f10", f"v{k}a10"] if k == "c" else []):
            L[col] = L[col].fillna(L[f"div_{k}"])
            # last resort (stat missing in the division's recent rows): global prior mean of that stat
            L[col] = L[col].fillna(L[k + "f"].shift(1).expanding().mean())
    H = L[L.venue == "h"].set_index("mid")
    A = L[L.venue == "a"].set_index("mid")
    for w in (5, 10, 20):
        d[f"h_cf{w}"], d[f"h_ca{w}"], d[f"a_cf{w}"], d[f"a_ca{w}"] = H[f"cf{w}"].values, H[f"ca{w}"].values, A[f"cf{w}"].values, A[f"ca{w}"].values
    d["h_hcf10"], d["h_hca10"], d["a_acf10"], d["a_aca10"] = H.vcf10.values, H.vca10.values, A.vcf10.values, A.vca10.values
    for k in ("s", "t", "g"):
        d[f"h_{k}f10"], d[f"h_{k}a10"], d[f"a_{k}f10"], d[f"a_{k}a10"] = H[f"{k}f10"].values, H[f"{k}a10"].values, A[f"{k}f10"].values, A[f"{k}a10"].values
    d["h_rest"], d["a_rest"] = H.rest.values, A.rest.values
    eh, ea = H.elo.values, A.elo.values
    d["elo_h"], d["elo_a"] = eh, ea
    for c in ("elo_h", "elo_a"):
        d[c] = d[c].fillna(d.groupby("Division")[c].transform("median"))
    d["elo_diff"] = (d.elo_h - d.elo_a) / 100
    d["elo_level"] = ((d.elo_h + d.elo_a) / 2 - 1500) / 100
    d["stage"] = ((d.MatchDate.dt.month - 7) % 12) / 11
    for div in DIVS[1:]:
        d[f"div_{div}"] = (d.Division == div).astype(float)
    for tgt, col in (("T", "T"), ("H", "HomeCorners"), ("A", "AwayCorners")):
        d[f"lm_{tgt}"] = d.groupby("Division")[col].transform(lambda s: s.shift(1).rolling(LEAGUE_WIN, min_periods=LEAGUE_MINP).mean())
    d["season"] = season_start(d.MatchDate)
    ev = d[d.Division.isin(DIVS) & (d.MatchDate >= EVAL_START)].dropna(subset=["lm_T", "lm_H", "lm_A"]).copy()
    feats = [c for g_ in GROUPS.values() for c in g_]
    assert not ev[feats].isna().any().any(), ev[feats].isna().sum()[lambda s: s > 0]
    return ev.reset_index(drop=True)


# ------------------------------------------------------------------ models
def design(df: pd.DataFrame, groups: list[str], base: str) -> np.ndarray:
    cols = [np.ones(len(df)), np.log(df[base].to_numpy(float))]
    for gname in groups:
        for c in GROUPS[gname]:
            v = df[c].to_numpy(float)
            cols.append(np.log(np.clip(v, 0.05, None)) if c in LOG_COLS else v)
    return np.column_stack(cols)


def poisson_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    b = np.zeros(X.shape[1])
    b[0] = np.log(y.mean())
    for _ in range(100):
        eta = np.clip(X @ b, -10, 10)
        mu = np.exp(eta)
        z = eta + (y - mu) / mu
        new = np.linalg.solve(X.T @ (X * mu[:, None]) + 1e-8 * np.eye(X.shape[1]), X.T @ (mu * z))
        if np.max(np.abs(new - b)) < 1e-9:
            return new
        b = new
    return b


def nb_logpmf(y: np.ndarray, mu: np.ndarray, alpha: float) -> np.ndarray:
    r = 1 / alpha
    return (special.gammaln(y + r) - special.gammaln(r) - special.gammaln(y + 1)
            + r * np.log(r / (r + mu)) + y * np.log(mu / (r + mu)))


def nb_alpha(y: np.ndarray, mu: np.ndarray) -> float:
    f = lambda la: -nb_logpmf(y, mu, np.exp(la)).sum()
    return float(np.exp(optimize.minimize_scalar(f, bounds=(np.log(1e-4), np.log(3)), method="bounded").x))


def nb_pmf_grid(mu: np.ndarray, alpha: float | None) -> np.ndarray:
    if alpha is None:
        return stats.poisson.pmf(GRID[None, :], mu[:, None])
    return np.exp(nb_logpmf(GRID[None, :].astype(float), mu[:, None], alpha))


def convolve_rows(ph: np.ndarray, pa: np.ndarray) -> np.ndarray:
    n = len(GRID)
    out = np.zeros((ph.shape[0], 2 * n - 1))
    for k in range(n):
        out[:, k:k + n] += ph[:, [k]] * pa
    return out[:, :n] / out[:, :n].sum(axis=1, keepdims=True)


def pit_normal(y: np.ndarray, mu: np.ndarray, alpha: float, rng: np.random.Generator) -> np.ndarray:
    r = 1 / alpha
    p = r / (r + mu)
    lo = np.where(y > 0, stats.nbinom.cdf(y - 1, r, p), 0.0)
    hi = stats.nbinom.cdf(y, r, p)
    u = lo + rng.random(len(y)) * (hi - lo)
    return stats.norm.ppf(np.clip(u, 1e-9, 1 - 1e-9))


def copula_total_pmf(ph: np.ndarray, pa: np.ndarray, rho: float) -> np.ndarray:
    rng = np.random.default_rng(MC_SEED)
    z = rng.standard_normal((MC_DRAWS, 2))
    z[:, 1] = rho * z[:, 0] + np.sqrt(1 - rho ** 2) * z[:, 1]
    u = stats.norm.cdf(z)
    ch, ca = np.cumsum(ph, axis=1), np.cumsum(pa, axis=1)
    out = np.zeros((ph.shape[0], len(GRID)))
    for i in range(ph.shape[0]):
        hh = np.minimum(np.searchsorted(ch[i], u[:, 0]), len(GRID) - 1)
        aa = np.minimum(np.searchsorted(ca[i], u[:, 1]), len(GRID) - 1)
        t = np.minimum(hh + aa, len(GRID) - 1)
        out[i] = np.bincount(t, minlength=len(GRID))[:len(GRID)] / MC_DRAWS
    indep = convolve_rows(ph, pa)
    return (1 - MC_MIX) * out + MC_MIX * indep


def fit_predict(tr: pd.DataFrame, te: pd.DataFrame, groups: list[str], family: str) -> dict:
    """Returns pmf of T on the test rows plus team-corner pmfs (NB marginals)."""
    out: dict = {}
    if family in ("MA1", "MA2"):
        Xtr, Xte = design(tr, groups, "lm_T"), design(te, groups, "lm_T")
        b = poisson_fit(Xtr, tr["T"].to_numpy(float))
        mu_tr, mu_te = np.exp(Xtr @ b), np.exp(Xte @ b)
        alpha = None if family == "MA1" else nb_alpha(tr["T"].to_numpy(float), mu_tr)
        out.update(pmf=nb_pmf_grid(mu_te, alpha), alpha=alpha, n_params=Xtr.shape[1] + (alpha is not None))
        return out
    marg = {}
    for side, col, base in (("H", "HomeCorners", "lm_H"), ("A", "AwayCorners", "lm_A")):
        Xtr, Xte = design(tr, groups, base), design(te, groups, base)
        y = tr[col].to_numpy(float)
        b = poisson_fit(Xtr, y)
        mu_tr, mu_te = np.exp(Xtr @ b), np.exp(Xte @ b)
        al = nb_alpha(y, mu_tr)
        marg[side] = dict(mu_tr=mu_tr, mu_te=mu_te, alpha=al, k=Xtr.shape[1] + 1, pmf=nb_pmf_grid(mu_te, al))
    out.update(pmf_H=marg["H"]["pmf"], pmf_A=marg["A"]["pmf"], alpha_H=marg["H"]["alpha"], alpha_A=marg["A"]["alpha"])
    if family == "MA3":
        out.update(pmf=convolve_rows(marg["H"]["pmf"], marg["A"]["pmf"]), n_params=marg["H"]["k"] + marg["A"]["k"])
        return out
    rng = np.random.default_rng(MC_SEED)
    zh = pit_normal(tr.HomeCorners.to_numpy(float), marg["H"]["mu_tr"], marg["H"]["alpha"], rng)
    za = pit_normal(tr.AwayCorners.to_numpy(float), marg["A"]["mu_tr"], marg["A"]["alpha"], rng)
    rho = float(np.corrcoef(zh, za)[0, 1])
    out.update(pmf=copula_total_pmf(marg["H"]["pmf"], marg["A"]["pmf"], rho), rho=rho, n_params=marg["H"]["k"] + marg["A"]["k"] + 1)
    return out


def baseline(tr: pd.DataFrame, te: pd.DataFrame, which: str) -> np.ndarray:
    if which == "B0":
        return nb_pmf_grid(te.lm_T.to_numpy(float), None)
    if which == "B1":
        mu = 0.5 * (te.h_cf10 + te.a_ca10) + 0.5 * (te.a_cf10 + te.h_ca10)
        return nb_pmf_grid(mu.to_numpy(float), None)
    al = nb_alpha(tr["T"].to_numpy(float), tr.lm_T.to_numpy(float))
    return nb_pmf_grid(te.lm_T.to_numpy(float), al)


# ------------------------------------------------------------------ metrics
def p_over(pmf: np.ndarray, line: float) -> np.ndarray:
    return np.clip(1 - pmf[:, : int(np.floor(line)) + 1].sum(axis=1), 1e-9, 1 - 1e-9)


def logscore(pmf: np.ndarray, y: np.ndarray) -> np.ndarray:
    yy = np.minimum(y.astype(int), len(GRID) - 1)
    return -np.log(np.clip(pmf[np.arange(len(y)), yy], 1e-12, None))


def bll(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def primary_vec(pmf: np.ndarray, T: np.ndarray) -> np.ndarray:
    return np.mean([bll((T > L).astype(float), p_over(pmf, L)) for L in PRIMARY_LINES], axis=0)


def calib(y: np.ndarray, p: np.ndarray) -> dict:
    x = special.logit(p)
    X = np.column_stack([np.ones_like(x), x])
    b = np.array([0.0, 1.0])
    for _ in range(50):
        q = special.expit(X @ b)
        w = np.clip(q * (1 - q), 1e-9, None)
        new = b + np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (y - q))
        if np.max(np.abs(new - b)) < 1e-10:
            b = new
            break
        b = new
    # calibration-in-the-large (slope fixed at 1)
    a = 0.0
    for _ in range(50):
        q = special.expit(a + x)
        a += (y - q).sum() / max((q * (1 - q)).sum(), 1e-9)
    return {"intercept": round(float(b[0]), 4), "slope": round(float(b[1]), 4), "citl": round(float(a), 4)}


def auc(y: np.ndarray, p: np.ndarray) -> float:
    r = stats.rankdata(p)
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def line_metrics(pmf: np.ndarray, T: np.ndarray) -> dict:
    out = {}
    for L in LINES:
        y, p = (T > L).astype(float), p_over(pmf, L)
        dec = pd.qcut(p, 10, duplicates="drop")
        rel = pd.DataFrame({"y": y, "p": p, "q": dec}).groupby("q", observed=True).agg(p=("p", "mean"), y=("y", "mean"), n=("y", "size"))
        out[str(L)] = {"n": int(len(y)), "base_rate": round(float(y.mean()), 4), "mean_p": round(float(p.mean()), 4),
                       "logloss": round(float(bll(y, p).mean()), 5), "brier": round(float(((p - y) ** 2).mean()), 5),
                       "auc": round(auc(y, p), 4), **calib(y, p),
                       "reliability": [[round(float(r.p), 3), round(float(r.y), 3), int(r.n)] for r in rel.itertuples()],
                       "low_p_region": _region(y, p, p < 0.25), "high_p_region": _region(y, p, p > 0.75)}
    return out


def _region(y: np.ndarray, p: np.ndarray, m: np.ndarray) -> dict:
    return {"n": int(m.sum()), "mean_p": round(float(p[m].mean()), 4) if m.any() else None, "rate": round(float(y[m].mean()), 4) if m.any() else None}


def boot_ci(diff: np.ndarray, seed: int = BOOT_SEED) -> list[float]:
    rng = np.random.default_rng(seed)
    n = len(diff)
    m = [diff[rng.integers(0, n, n)].mean() for _ in range(BOOT)]
    return [round(float(np.percentile(m, 2.5)), 6), round(float(np.percentile(m, 97.5)), 6)]


# ------------------------------------------------------------------ modes
def folds(ev: pd.DataFrame):
    for s in DEV_SEASONS:
        tr = ev[(ev.MatchDate < pd.Timestamp(f"{s}-07-01"))]
        te = ev[ev.season == s]
        yield s, tr, te


def mode_discovery(ev: pd.DataFrame) -> dict:
    disc = ev[ev.MatchDate < DISCOVERY_END]
    feats = [c for g in GROUPS.values() for c in g if not c.startswith("div_")] + ["lm_T"]
    res: dict = {"label": "EXPLORATORY (discovery set 2005-07..2019-06 only)", "n": int(len(disc)), "features": {}}
    for f in feats:
        row = {}
        for tgt, col in (("T", "T"), ("H", "HomeCorners"), ("A", "AwayCorners")):
            row[f"rho_{tgt}"] = round(float(stats.spearmanr(disc[f], disc[col]).statistic), 4)
        per_season = disc.groupby("season").apply(lambda g: stats.spearmanr(g[f], g["T"]).statistic, include_groups=False)
        per_league = disc.groupby("Division").apply(lambda g: stats.spearmanr(g[f], g["T"]).statistic, include_groups=False)
        sign = np.sign(row["rho_T"]) or 1
        row.update({"season_sign_consistency": round(float((np.sign(per_season) == sign).mean()), 3), "season_sd": round(float(per_season.std()), 4),
                    "league_sign_consistency": round(float((np.sign(per_league) == sign).mean()), 3),
                    "league_range": [round(float(per_league.min()), 3), round(float(per_league.max()), 3)]})
        res["features"][f] = row
    num = disc[[f for f in feats]]
    cm = num.corr(method="spearman")
    res["redundant_pairs_|rho|>=0.8"] = sorted([[a, b, round(float(cm.loc[a, b]), 3)] for i, a in enumerate(feats) for b in feats[i + 1:]
                                                if abs(cm.loc[a, b]) >= 0.8], key=lambda t: -abs(t[2]))
    # raw home/away dependence on discovery set (conditional on nothing / on league-season)
    rel = disc.assign(rh=disc.HomeCorners - disc.groupby(["Division", "season"]).HomeCorners.transform("mean"),
                      ra=disc.AwayCorners - disc.groupby(["Division", "season"]).AwayCorners.transform("mean"))
    res["home_away_corr_raw"] = round(float(np.corrcoef(disc.HomeCorners, disc.AwayCorners)[0, 1]), 4)
    res["home_away_corr_within_league_season"] = round(float(np.corrcoef(rel.rh, rel.ra)[0, 1]), 4)
    res["total_var_over_mean_discovery"] = round(float(disc["T"].var() / disc["T"].mean()), 4)
    return res


def mode_develop(ev: pd.DataFrame) -> dict:
    F = list(folds(ev))
    log: list = []

    def dev_score(groups: list[str], family: str = "MA2") -> list[float]:
        return [float(logscore(fit_predict(tr, te, groups, family)["pmf"], te["T"].to_numpy()).mean()) for _, tr, te in F]

    selected: list[str] = []
    cur = dev_score(selected)
    log.append({"step": 0, "groups": [], "fold_scores": [round(x, 6) for x in cur], "mean": round(float(np.mean(cur)), 6)})
    while len(selected) < SEL_MAX:
        cands = {}
        for gname in GROUPS:
            if gname in selected:
                continue
            sc = dev_score(selected + [gname])
            gain = np.array(cur) - np.array(sc)
            cands[gname] = {"mean_gain": round(float(gain.mean()), 6), "folds_improved": int((gain > 0).sum()), "scores": sc}
        ok = {k: v for k, v in cands.items() if v["mean_gain"] >= SEL_GAIN and v["folds_improved"] >= SEL_FOLDS}
        log.append({"step": len(selected) + 1, "candidates": {k: {kk: vv for kk, vv in v.items() if kk != "scores"} for k, v in cands.items()},
                    "added": max(ok, key=lambda k: ok[k]["mean_gain"]) if ok else None})
        if not ok:
            break
        best = max(ok, key=lambda k: ok[k]["mean_gain"])
        selected.append(best)
        cur = cands[best]["scores"]
    # families
    fam = {}
    for f in ("MA1", "MA2", "MA3", "MA4"):
        per = []
        extra = []
        for s, tr, te in F:
            r = fit_predict(tr, te, selected, f)
            per.append(float(logscore(r["pmf"], te["T"].to_numpy()).mean()))
            extra.append({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items() if k in ("alpha", "alpha_H", "alpha_A", "rho")})
        fam[f] = {"fold_logscore": [round(x, 6) for x in per], "mean_logscore": round(float(np.mean(per)), 6), "fold_params": extra}
    order = ["MA1", "MA2", "MA3", "MA4"]
    best_score = min(fam[f]["mean_logscore"] for f in order)
    family = next(f for f in order if fam[f]["mean_logscore"] <= best_score + FAMILY_TOL)
    # baselines and primary metric per fold
    comp = {}
    pmfs: dict = {}
    for s, tr, te in F:
        T = te["T"].to_numpy()
        pmfs[s] = {"A": fit_predict(tr, te, selected, family)["pmf"], **{b: baseline(tr, te, b) for b in ("B0", "B1", "B2")}}
        comp[s] = {k: round(float(primary_vec(v, T).mean()), 6) for k, v in pmfs[s].items()}
        comp[s]["n"] = int(len(te))
    mean_primary = {k: round(float(np.mean([comp[s][k] for s in comp])), 6) for k in ("A", "B0", "B1", "B2")}
    comparator = min(("B0", "B1", "B2"), key=lambda b: mean_primary[b])
    deltas = [comp[s]["A"] - comp[s][comparator] for s in comp]
    proceed = bool(np.mean(deltas) <= MATERIAL and sum(d < 0 for d in deltas) >= 4)
    # development diagnostics on pooled folds
    Tall = np.concatenate([te["T"].to_numpy() for _, _, te in F])
    pA = np.vstack([pmfs[s]["A"] for s in pmfs])
    pC = np.vstack([pmfs[s][comparator] for s in pmfs])
    dvec = primary_vec(pA, Tall) - primary_vec(pC, Tall)
    return {"selection_log": log, "selected_groups": selected, "families": fam, "family_selected": family,
            "primary_by_fold": comp, "mean_primary": mean_primary, "primary_comparator": comparator,
            "delta_primary_by_fold": [round(x, 6) for x in deltas], "delta_primary_mean": round(float(np.mean(deltas)), 6),
            "delta_primary_pooled_ci95": boot_ci(dvec), "proceed_to_holdout": proceed,
            "dev_line_metrics_modelA": line_metrics(pA, Tall), "dev_line_metrics_comparator": line_metrics(pC, Tall)}


def committed(path: Path) -> bool:
    rel = path.relative_to(REPO).as_posix()
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode == 0
    return tracked and clean


def mode_holdout(ev: pd.DataFrame) -> dict:
    spec_p, marker = OUT / "FROZEN_SPEC.json", OUT / "HOLDOUT_OPENED.marker"
    if not spec_p.exists() or not committed(spec_p):
        raise SystemExit("FROZEN_SPEC.json missing or not committed -- holdout stays sealed")
    if marker.exists():
        raise SystemExit("holdout already opened once -- refusing a second opening")
    spec = json.loads(spec_p.read_text())
    marker.write_text(json.dumps({"opened_with_spec_commit": subprocess.run(["git", "log", "-1", "--format=%H", "--", str(spec_p)], cwd=REPO,
                                                                           capture_output=True, text=True).stdout.strip()}) + "\n")
    tr, te = ev[ev.MatchDate < HOLDOUT_START], ev[ev.MatchDate >= HOLDOUT_START]
    T = te["T"].to_numpy()
    rA = fit_predict(tr, te, spec["selected_groups"], spec["family"])
    pA, pC = rA["pmf"], baseline(tr, te, spec["primary_comparator"])
    pAll = {b: baseline(tr, te, b) for b in ("B0", "B1", "B2")}
    d = primary_vec(pA, T) - primary_vec(pC, T)
    by_league = {}
    for div in DIVS:
        m = (te.Division == div).to_numpy()
        if m.any():
            by_league[div] = {"n": int(m.sum()), "delta_primary": round(float(d[m].mean()), 6), "primary_A": round(float(primary_vec(pA[m], T[m]).mean()), 6)}
    by_season = {}
    for s in sorted(te.season.unique()):
        m = (te.season == s).to_numpy()
        by_season[str(s)] = {"n": int(m.sum()), "delta_primary": round(float(d[m].mean()), 6), "ci95": boot_ci(d[m])}
    lm = line_metrics(pA, T)
    team = {}
    if "pmf_H" in rA:
        for side, pm, col in (("home", rA["pmf_H"], "HomeCorners"), ("away", rA["pmf_A"], "AwayCorners")):
            y_ = te[col].to_numpy()
            team[side] = {str(L): {"base_rate": round(float((y_ > L).mean()), 4), "mean_p": round(float(p_over(pm, L).mean()), 4),
                                   "logloss": round(float(bll((y_ > L).astype(float), p_over(pm, L)).mean()), 5),
                                   **calib((y_ > L).astype(float), p_over(pm, L))} for L in TEAM_LINES}
    exp_vs_act = {"mean_pred_T": round(float((pA * GRID).sum(axis=1).mean()), 3), "mean_actual_T": round(float(T.mean()), 3)}
    crit1 = bool(d.mean() <= MATERIAL and boot_ci(d)[1] < 0)
    crit2 = all(0.85 <= lm[str(L)]["slope"] <= 1.15 and abs(lm[str(L)]["intercept"]) <= 0.10 for L in (9.5, 10.5))
    crit3 = bool(sum(v["delta_primary"] < 0 for v in by_league.values()) >= 7 and all(v["delta_primary"] < 0 for v in by_season.values() if v["n"] >= 1000))
    return {"n_train": int(len(tr)), "n_holdout": int(len(te)), "spec": spec, "expected_vs_actual": exp_vs_act,
            "primary": {"A": round(float(primary_vec(pA, T).mean()), 6), **{b: round(float(primary_vec(v, T).mean()), 6) for b, v in pAll.items()}},
            "delta_primary_vs_comparator": round(float(d.mean()), 6), "ci95": boot_ci(d), "logscore_T": {"A": round(float(logscore(pA, T).mean()), 6),
            "comparator": round(float(logscore(pC, T).mean()), 6)}, "line_metrics_A": lm, "line_metrics_comparator": line_metrics(pC, T),
            "team_lines_A": team, "by_league": by_league, "by_season": by_season, "params": {k: v for k, v in rA.items() if k in ("alpha", "alpha_H", "alpha_A", "rho")},
            "criteria": {"1_material_and_ci": crit1, "2_calibration_9.5_10.5": crit2, "3_league_and_season_stability": crit3},
            "verdict": "PROBABILITY_VALIDATED / PRICE_GATE_PENDING" if (crit1 and crit2 and crit3) else "NULL"}


def main() -> int:
    mode, path = sys.argv[1], sys.argv[2]
    ev = build(path)
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"discovery": mode_discovery, "develop": mode_develop, "holdout": mode_holdout}[mode](ev)
    name = {"discovery": "DISCOVERY.json", "develop": "DEVELOPMENT.json", "holdout": "HOLDOUT.json"}[mode]
    (OUT / name).write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in res.items() if not k.startswith(("dev_line", "line_metrics", "features", "selection_log"))}, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
