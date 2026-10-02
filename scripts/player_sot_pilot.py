"""Player SOT pilot signal test (pre-registered: research/platform_v2/player_sot/pilot/PREREGISTRATION.md).

Usage: python scripts/player_sot_pilot.py develop|holdout   (reads data/open/wyscout/player_match.csv.gz)
No odds are used. The holdout opens once, after FROZEN_SPEC.json is committed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from prediction_markets_lab.research_shadow import player_sot as PS

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data/open/wyscout/player_match.csv.gz"
OUT = REPO / "research/platform_v2/player_sot/pilot"
DEV_START, HOLDOUT_START = "2018-01-01", "2018-03-01"
MIN_PRIOR_APPS = 3
MATERIAL = -0.002
FAMILY_TOL = 0.0005
BOOT, SEED = 1000, 7
RIDGE = 1e-6
COMPS = ["EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1"]


def load() -> pd.DataFrame:
    d = PS.add_targets(PS.prior_features(pd.read_csv(DATA)))
    d["date"] = pd.to_datetime(d.date)
    return d


def population(d: pd.DataFrame) -> pd.DataFrame:
    return d[d.starter & (d.role != "GK") & (d.p_apps_prior >= MIN_PRIOR_APPS)].copy()


def rates(train: pd.DataFrame) -> dict:
    g = train.groupby(["competition", "role"])
    return {"sot90": (g.sot.sum() / g.minutes.sum() * PS.FULL_MATCH).to_dict(), "shots90": (g.shots.sum() / g.minutes.sum() * PS.FULL_MATCH).to_dict(),
            "team_sot": float(train.groupby(["match_id", "team_id"]).sot.sum().mean())}


def design(d: pd.DataFrame, r: dict) -> np.ndarray:
    key = list(zip(d.competition, d.role))
    w = PS.SHRINK_MINUTES / PS.FULL_MATCH
    mins90 = d.p_minutes_prior.fillna(0).to_numpy() / PS.FULL_MATCH
    sot90 = (d.p_sot_prior.fillna(0).to_numpy() + np.array([r["sot90"].get(k, 0.3) for k in key]) * w) / (mins90 + w)
    sh90 = (d.p_shots_prior.fillna(0).to_numpy() + np.array([r["shots90"].get(k, 1.0) for k in key]) * w) / (mins90 + w)
    cols = [np.ones(len(d)), np.log1p(sot90), np.log1p(sh90), (d.p_starts_prior / d.p_apps_prior.clip(lower=1)).to_numpy(),
            (d.role == "MD").astype(float).to_numpy(), (d.role == "FW").astype(float).to_numpy(),
            np.log(d.team_sot_for_prior.fillna(r["team_sot"]).clip(lower=0.5).to_numpy()),
            np.log(d.opp_sot_conceded_prior.fillna(r["team_sot"]).clip(lower=0.5).to_numpy()), d.home.astype(float).to_numpy()]
    cols += [(d.competition == c).astype(float).to_numpy() for c in COMPS[1:]]
    return np.column_stack(cols)


def irls(X: np.ndarray, y: np.ndarray, family: str) -> np.ndarray:
    b = np.zeros(X.shape[1])
    b[0] = np.log(max(y.mean(), 1e-3)) if family == "poisson" else np.log(y.mean() / (1 - y.mean()))
    for _ in range(100):
        eta = np.clip(X @ b, -15, 15)
        if family == "poisson":
            mu = np.exp(eta)
            w, z = mu, eta + (y - mu) / mu
        else:
            mu = 1 / (1 + np.exp(-eta))
            w = np.clip(mu * (1 - mu), 1e-9, None)
            z = eta + (y - mu) / w
        new = np.linalg.solve(X.T @ (X * w[:, None]) + RIDGE * np.eye(X.shape[1]), X.T @ (w * z))
        if np.max(np.abs(new - b)) < 1e-9:
            return new
        b = new
    return b


def predict(train: pd.DataFrame, test: pd.DataFrame, fam: str) -> dict[str, np.ndarray]:
    r = rates(train)
    Xtr, Xte = design(train, r), design(test, r)
    if fam == "A1":
        return {t: 1 / (1 + np.exp(-(Xte @ irls(Xtr, train[t].to_numpy(float), "logit")))) for t in PS.TARGETS}
    lam = np.exp(np.clip(Xte @ irls(Xtr, train.sot.to_numpy(float), "poisson"), -15, 15))
    return {t: 1 - stats.poisson.cdf(k - 1, lam) for t, k in PS.TARGETS.items()}


def baselines(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    return {"B0": {t: PS.baseline_role_rate(train, test, t) for t in PS.TARGETS},
            "B1": {t: PS.baseline_player_rate(train, test, t) for t in PS.TARGETS}}


def ll(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def boot_ci(diff: np.ndarray, groups: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    ug = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in ug}
    m = []
    for _ in range(BOOT):
        pick = rng.choice(ug, len(ug))
        m.append(np.concatenate([diff[idx[g]] for g in pick]).mean())
    return [round(float(np.percentile(m, 2.5)), 6), round(float(np.percentile(m, 97.5)), 6)]


def develop() -> dict:
    d = load()
    pop = population(d)
    train = pop[pop.date < DEV_START]
    dev = pop[(pop.date >= DEV_START) & (pop.date < HOLDOUT_START)]
    res = {"n_train": int(len(train)), "n_dev": int(len(dev)), "families": {}, "baselines": {}}
    for fam in ("A1", "A2"):
        p = predict(train, dev, fam)
        res["families"][fam] = {t: PS.evaluate(dev[t].to_numpy(float), p[t]) for t in PS.TARGETS}
    for b, pb in baselines(train, dev).items():
        res["baselines"][b] = {t: PS.evaluate(dev[t].to_numpy(float), pb[t]) for t in PS.TARGETS}
    mean = {f: np.mean([res["families"][f][t]["logloss"] for t in PS.TARGETS]) for f in ("A1", "A2")}
    fam = "A1" if mean["A1"] <= mean["A2"] + FAMILY_TOL else "A2"
    comp = min(("B0", "B1"), key=lambda b: res["baselines"][b]["sot_1plus"]["logloss"])
    delta = res["families"][fam]["sot_1plus"]["logloss"] - res["baselines"][comp]["sot_1plus"]["logloss"]
    res.update({"family_selected": fam, "comparator": comp, "delta_dev_sot_1plus": round(float(delta), 6), "proceed_to_holdout": bool(delta <= MATERIAL)})
    return res


def committed(p: Path) -> bool:
    rel = p.relative_to(REPO).as_posix()
    return (subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True).returncode == 0
            and subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode == 0)


def holdout() -> dict:
    spec = PS.HoldoutGuard(OUT / "FROZEN_SPEC.json", OUT / "HOLDOUT_OPENED.marker").open(committed)
    d = load()
    pop = population(d)
    train, test = pop[pop.date < HOLDOUT_START], pop[pop.date >= HOLDOUT_START]
    pa = predict(train, test, spec["family_selected"])
    pb = baselines(train, test)[spec["comparator"]]
    res = {"spec": spec, "n_train": int(len(train)), "n_holdout": int(len(test)), "targets": {}}
    for t in PS.TARGETS:
        y = test[t].to_numpy(float)
        diff = ll(y, pa[t]) - ll(y, pb[t])
        res["targets"][t] = {"model_a": PS.evaluate(y, pa[t]), "comparator": PS.evaluate(y, pb[t]), "delta": round(float(diff.mean()), 6),
                             "ci95_match_bootstrap": boot_ci(diff, test.match_id.to_numpy()),
                             "by_league": {c: round(float(diff[(test.competition == c).to_numpy()].mean()), 6) for c in COMPS},
                             "by_role": {r: {"n": int((test.role == r).sum()), "delta": round(float(diff[(test.role == r).to_numpy()].mean()), 6)} for r in ("DF", "MD", "FW")}}
    p1 = res["targets"]["sot_1plus"]
    c1 = p1["delta"] <= MATERIAL and p1["ci95_match_bootstrap"][1] < 0
    c2 = 0.85 <= p1["model_a"]["cal_slope"] <= 1.15 and abs(p1["model_a"]["cal_intercept"]) <= 0.10
    c3 = sum(v < 0 for v in p1["by_league"].values()) >= 4
    res["criteria"] = {"1_material_ci": bool(c1), "2_calibration": bool(c2), "3_leagues": bool(c3)}
    res["verdict"] = "PILOT_SIGNAL" if (c1 and c2 and c3) else "NO_SIGNAL"
    return res


def main() -> int:
    mode = sys.argv[1]
    res = develop() if mode == "develop" else holdout()
    (OUT / ("DEVELOPMENT.json" if mode == "develop" else "HOLDOUT.json")).write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(res, indent=1, default=str)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
