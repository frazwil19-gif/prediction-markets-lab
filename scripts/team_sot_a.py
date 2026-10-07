"""team-SOT-A (pre-registered: research/platform_v2/team_sot/PREREGISTRATION.md, commit 22213f8).

  python scripts/team_sot_a.py holdout <Matches.csv>  -> HOLDOUT.json   (TRAIN < 2025-07-01, scored once on 2025/26)
  python scripts/team_sot_a.py fit     <Matches.csv>  -> team_sot_A_v1_params.json (only after HISTORICALLY_CONFIRMED)
Features come from the frozen corners-A builder (scripts/corners_model_a.py::build; prior matches only).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, special, stats

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/team_sot"
HOLDOUT_START, HOLDOUT_END = pd.Timestamp("2025-07-01"), pd.Timestamp("2026-07-01")
LINES = [2.5, 3.5, 4.5, 5.5]
PRIMARY = {"H": 4.5, "A": 3.5}
COLS = ["h_tf10", "h_ta10", "a_tf10", "a_ta10"]
LEAGUE_WIN, LEAGUE_MINP, LOG_FLOOR = 380, 50, 0.05
BOOT, SEED = 1000, 7
MATERIAL, SLOPE, INTERCEPT, MIN_DIVS = -0.005, (0.85, 1.15), 0.10, 8
VERSION = "team-SOT-A-1.0"
SIDE = {"H": "HomeTarget", "A": "AwayTarget"}


def corners_builder():
    spec = importlib.util.spec_from_file_location("cma_frozen", REPO / "scripts/corners_model_a.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load(path: str) -> pd.DataFrame:
    d = corners_builder().build(path)
    d = d.dropna(subset=["HomeTarget", "AwayTarget"]).copy()
    for s, col in SIDE.items():   # league rolling side mean of SOT, prior matches of the division only
        d[f"lm_S{s}"] = d.groupby("Division")[col].transform(lambda x: x.shift(1).rolling(LEAGUE_WIN, min_periods=LEAGUE_MINP).mean())
    return d.dropna(subset=["lm_SH", "lm_SA"]).reset_index(drop=True)


def design(df: pd.DataFrame, side: str) -> np.ndarray:
    cols = [np.ones(len(df)), np.log(df[f"lm_S{side}"].to_numpy(float))]
    cols += [np.log(np.clip(df[c].to_numpy(float), LOG_FLOOR, None)) for c in COLS]
    return np.column_stack(cols)


def nb_ll(y, mu, alpha):
    r = 1 / alpha
    return special.gammaln(y + r) - special.gammaln(r) - special.gammaln(y + 1) + r * np.log(r / (r + mu)) + y * np.log(mu / (r + mu))


def nb_fit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """NB2 maximum likelihood (start: Poisson IRLS)."""
    b = np.zeros(X.shape[1]); b[0] = np.log(y.mean())
    for _ in range(100):
        eta = np.clip(X @ b, -10, 10); mu = np.exp(eta)
        new = np.linalg.solve(X.T @ (X * mu[:, None]) + 1e-8 * np.eye(X.shape[1]), X.T @ (mu * (eta + (y - mu) / mu)))
        if np.max(np.abs(new - b)) < 1e-10:
            break
        b = new
    f = lambda th: -nb_ll(y, np.exp(np.clip(X @ th[:-1], -10, 10)), np.exp(th[-1])).sum()
    res = optimize.minimize(f, np.append(b, np.log(0.05)), method="L-BFGS-B")
    return res.x[:-1], float(np.exp(res.x[-1]))


def p_over(mu: np.ndarray, alpha: float | None, line: float) -> np.ndarray:
    k = int(np.floor(line))
    if alpha is None:
        cdf = stats.poisson.cdf(k, mu)
    else:
        r = 1 / alpha
        cdf = stats.nbinom.cdf(k, r, r / (r + mu))
    return np.clip(1 - cdf, 1e-9, 1 - 1e-9)


def ll(y, p):
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def calib(y, p):
    x = np.log(p / (1 - p)); X = np.column_stack([np.ones_like(x), x]); b = np.array([0.0, 1.0])
    for _ in range(50):
        q = 1 / (1 + np.exp(-(X @ b)))
        b = b + np.linalg.solve(X.T @ (X * (q * (1 - q))[:, None]) + 1e-9 * np.eye(2), X.T @ (y - q))
    return float(b[0]), float(b[1])


def boot_ci(diff: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    m = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(BOOT)]   # one row per match
    return [round(float(np.percentile(m, 2.5)), 6), round(float(np.percentile(m, 97.5)), 6)]


def holdout(path: str) -> dict:
    d = load(path)
    tr, te = d[d.MatchDate < HOLDOUT_START], d[(d.MatchDate >= HOLDOUT_START) & (d.MatchDate < HOLDOUT_END)]
    res = {"spec_commit": "22213f8", "n_train": int(len(tr)), "n_holdout": int(len(te)), "sides": {}}
    ok = True
    for s, col in SIDE.items():
        b, a = nb_fit(design(tr, s), tr[col].to_numpy(float))
        mu = np.exp(design(te, s) @ b)
        mu0 = te[f"lm_S{s}"].to_numpy(float)
        y_cnt = te[col].to_numpy(float)
        side = {"coef": [round(float(x), 6) for x in b], "alpha": round(a, 6), "lines": {}}
        for L in LINES:
            y = (y_cnt > L).astype(float)
            pa, p0 = p_over(mu, a, L), p_over(mu0, None, L)
            diff = ll(y, pa) - ll(y, p0)
            ci_, sl = calib(y, pa)
            by_div = {dv: round(float(diff[(te.Division == dv).to_numpy()].mean()), 6) for dv in sorted(te.Division.unique())}
            dec = np.minimum((pa * 10).astype(int), 9)
            side["lines"][str(L)] = {"base_rate": round(float(y.mean()), 4), "mean_p": round(float(pa.mean()), 4),
                                     "logloss_A": round(float(ll(y, pa).mean()), 5), "logloss_M0": round(float(ll(y, p0).mean()), 5),
                                     "delta": round(float(diff.mean()), 6), "ci95": boot_ci(diff),
                                     "brier_A": round(float(((pa - y) ** 2).mean()), 5), "cal_intercept": round(ci_, 4), "cal_slope": round(sl, 4),
                                     "by_division": by_div, "divisions_negative": sum(v < 0 for v in by_div.values()),
                                     "reliability_deciles": {f"{k/10:.1f}": [int((dec == k).sum()), round(float(pa[dec == k].mean()), 3),
                                                                            round(float(y[dec == k].mean()), 3)] for k in range(10) if (dec == k).any()}}
            if L == PRIMARY[s]:
                r = side["lines"][str(L)]
                crit = {"1_material_ci": r["delta"] <= MATERIAL and r["ci95"][1] < 0,
                        "2_calibration": SLOPE[0] <= r["cal_slope"] <= SLOPE[1] and abs(r["cal_intercept"]) <= INTERCEPT,
                        "3_divisions": r["divisions_negative"] >= MIN_DIVS}
                side["primary_line"], side["criteria"] = L, crit
                ok &= all(crit.values())
        res["sides"][s] = side
    res["verdict"] = "HISTORICALLY_CONFIRMED" if ok else "NOT_CONFIRMED"
    return res


def fit(path: str) -> dict:
    h = json.loads((OUT / "HOLDOUT.json").read_text())
    assert h["verdict"] == "HISTORICALLY_CONFIRMED", "pre-registration: production fit only after HISTORICALLY_CONFIRMED"
    d = load(path)
    tr = d[d.MatchDate < HOLDOUT_END]
    out = {"version": VERSION, "train_end": str(HOLDOUT_END.date()), "n_train": int(len(tr)), "columns": COLS,
           "constants": {"WINDOW": 10, "MINP": 3, "LEAGUE_WIN": LEAGUE_WIN, "LEAGUE_MINP": LEAGUE_MINP, "LOG_FLOOR": LOG_FLOOR},
           "lines": LINES, "sides": {}}
    for s, col in SIDE.items():
        b, a = nb_fit(design(tr, s), tr[col].to_numpy(float))
        out["sides"][s] = {"coef": [float(x) for x in b], "alpha": a,
                           "design": ["intercept", f"log(lm_S{s})"] + [f"log({c})" for c in COLS]}
    return out


def main() -> int:
    mode, path = sys.argv[1], sys.argv[2]
    if mode == "holdout":
        marker = OUT / "HOLDOUT.json"
        assert not marker.exists(), "holdout already scored once"
        res = holdout(path)
        marker.write_text(json.dumps(res, indent=1) + "\n")
    else:
        res = fit(path)
        (OUT / "team_sot_A_v1_params.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "sides"}, indent=1))
    for s, v in res.get("sides", {}).items():
        print(s, v.get("criteria"), {L: (x["delta"], x["ci95"], x["cal_slope"], x["cal_intercept"], x["divisions_negative"]) for L, x in v.get("lines", {}).items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
