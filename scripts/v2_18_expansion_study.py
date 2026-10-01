"""V2-18 existing-sport expansion study (pre-registered: research/platform_v2/v2_18_expansion/PREREGISTRATION.md).

Historical, exposed data, zero fitting: market-implied probabilities from Bet365 odds per match (multiplicative de-vig)
for football leagues and markets; per league x period metrics and the pre-registered grade. Reads the MIT dataset
(xgabora/Club-Football-Match-Data-2000-2025 data/Matches.csv) from --data and verifies its sha256.
Output: research/platform_v2/v2_18_expansion/RESULTS.json (+ CSV tables)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.research import probability_reliability as rel
from prediction_markets_lab.research.btts_outcome_prediction import DEFAULT_CONFIG, fit_market_implied_lambdas

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/v2_18_expansion"
SHA = "ef224cf2c252f07a842b3bcfd4ba5c718c25cedd8937ffa174a74b86b5ba4221"
REFERENCE = ("E0", "E1", "SC0")
CANDIDATES = ("E2", "E3", "SP1", "D1", "I1", "F1", "SP2", "D2", "I2", "F2", "N1", "P1", "B1", "T1", "G1", "SC1")
PERIODS = {"development": tuple(range(2017, 2022)), "validation": (2022, 2023, 2024), "confirmation": (2025,)}
SEED, N_BOOT, Z995 = 20261001, 1000, 2.807033768343811
LOW_N = 200
NAMES = {"E0": "Premier League", "E1": "Championship", "SC0": "Scottish Premiership", "E2": "League One", "E3": "League Two",
         "SP1": "La Liga", "D1": "Bundesliga", "I1": "Serie A", "F1": "Ligue 1", "SP2": "Segunda", "D2": "2. Bundesliga",
         "I2": "Serie B", "F2": "Ligue 2", "N1": "Eredivisie", "P1": "Primeira Liga", "B1": "Belgian Pro League",
         "T1": "Super Lig", "G1": "Greek Super League", "SC1": "Scottish Championship"}


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def irls(x: np.ndarray, y: np.ndarray, iters: int = 50) -> tuple[float, float]:
    """Calibration intercept/slope: y ~ sigmoid(a + b*logit(p)) (same model as performance.fit_calibration_intercept_slope)."""
    b = np.array([0.0, 1.0])
    X = np.column_stack([np.ones_like(x), x])
    for _ in range(iters):
        mu = 1 / (1 + np.exp(-(X @ b)))
        w = np.clip(mu * (1 - mu), 1e-10, None)
        step = np.linalg.solve((X.T * w) @ X, X.T @ (y - mu))
        b = b + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return float(b[0]), float(b[1])


def calib(p: np.ndarray, y: np.ndarray, g: np.ndarray, rng: np.random.Generator) -> dict:
    x = logit(p)
    a, s = irls(x, y)
    groups = pd.Series(np.arange(len(g))).groupby(g).apply(lambda s_: s_.to_numpy()).to_list()
    n = len(groups)
    slopes = []
    for _ in range(N_BOOT):
        take = np.concatenate([groups[i] for i in rng.integers(0, n, n)])
        try:
            slopes.append(irls(x[take], y[take])[1])
        except np.linalg.LinAlgError:
            continue
    lo, hi = np.percentile(slopes, [2.5, 97.5])
    return {"intercept": a, "slope": s, "slope_ci95": [float(lo), float(hi)], "slope_ci_includes_1": bool(lo <= 1 <= hi)}


def bands_ok(p: np.ndarray, y: np.ndarray) -> tuple[list[dict], bool]:
    rows, ok = [], True
    for r in rel.band_table(p, y):
        if r["n"] >= LOW_N:
            lo, hi = rel.wilson(r["actual_wins"], r["n"], Z995)
            inside = bool(lo <= r["mean_predicted"] <= hi)
            ok &= inside
            rows.append({"band": r["band"], "n": r["n"], "mean_pred": r["mean_predicted"], "actual": r["actual_rate"],
                         "w995": [lo, hi], "inside": inside})
    return rows, ok


def binary_block(p: np.ndarray, y: np.ndarray, g: np.ndarray, rng) -> dict:
    """Binary-market metrics (events may be several per match; g = match id for clustering)."""
    if len(p) == 0:
        return {"n_events": 0}
    pc = np.clip(p, 1e-12, 1 - 1e-12)
    bands, ok = bands_ok(p, y)
    out = {"n_events": int(len(p)), "matches": int(len(np.unique(g))), "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))),
           "brier": float(np.mean((p - y) ** 2)), "calibration": calib(p, y, g, rng), "bands_n200": bands, "bands_ok": ok,
           "thresholds": {}}
    for t in (0.6, 0.7, 0.8):
        m = p >= t
        k, n = int(y[m].sum()), int(m.sum())
        out["thresholds"][str(t)] = {"n": n, "mean_pred": float(p[m].mean()) if n else None, "actual": k / n if n else None,
                                     "w995": list(rel.wilson(k, n, Z995)) if n else None}
    return out


def season_of(d: pd.Series) -> pd.Series:
    return np.where(d.dt.month >= 7, d.dt.year, d.dt.year - 1)


def load(path: Path) -> pd.DataFrame:
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA:
        sys.exit(f"REFUSED: {path} does not match the pre-registered sha256")
    d = pd.read_csv(path, low_memory=False)
    d["date"] = pd.to_datetime(d.MatchDate)
    d["season"] = season_of(d.date)
    return d[d.Division.isin(REFERENCE + CANDIDATES) & d.season.between(2017, 2025)].copy()


def one_x_two(d: pd.DataFrame) -> pd.DataFrame:
    ok = d.FTResult.isin(["H", "D", "A"]) & (d[["OddHome", "OddDraw", "OddAway"]] > 1.0).all(axis=1)
    f = d[ok].copy()
    inv = 1 / f[["OddHome", "OddDraw", "OddAway"]].to_numpy()
    q = inv / inv.sum(1, keepdims=True)
    f["pH"], f["pD"], f["pA"] = q[:, 0], q[:, 1], q[:, 2]
    f["out"] = f.FTResult.map({"H": 0, "D": 1, "A": 2})
    f["mid"] = np.arange(len(f))
    return f


def league_1x2(f: pd.DataFrame, rng) -> dict:
    q = f[["pH", "pD", "pA"]].to_numpy()
    o = f.out.to_numpy()
    yy = np.eye(3)[o]
    p, y, g = q.ravel(), yy.ravel().astype(int), np.repeat(f.mid.to_numpy(), 3)
    res = binary_block(p, y, g, rng)
    res["matches"] = int(len(f))
    res["multiclass_log_loss"] = float(rel.multiclass_log_loss(q, o).mean())
    res["multiclass_brier"] = float(rel.multiclass_brier(q, o).mean())
    res["per_outcome_slope"] = {lab: irls(logit(q[:, j]), yy[:, j])[1] for j, lab in enumerate("HDA")}
    top = q.max(1)
    won = (q.argmax(1) == o).astype(int)
    res["top_pick"] = {str(t): {"n": int((top >= t).sum()), "share": float((top >= t).mean()),
                                "mean_pred": float(top[top >= t].mean()) if (top >= t).any() else None,
                                "actual": float(won[top >= t].mean()) if (top >= t).any() else None} for t in (0.6, 0.7, 0.8)}
    dc = np.column_stack([q[:, 0] + q[:, 1], q[:, 1] + q[:, 2], q[:, 0] + q[:, 2]])
    dcw = np.column_stack([o != 2, o != 0, o != 1]).astype(int)
    b = dc.max(1)
    bw = dcw[np.arange(len(dc)), dc.argmax(1)]
    res["dc_best"] = {"ge80_n": int((b >= 0.8).sum()), "ge80_share": float((b >= 0.8).mean()),
                      "ge80_mean_pred": float(b[b >= 0.8].mean()) if (b >= 0.8).any() else None,
                      "ge80_actual": float(bw[b >= 0.8].mean()) if (b >= 0.8).any() else None}
    res["dc_all_events"] = binary_block(dc.ravel(), dcw.ravel(), np.repeat(f.mid.to_numpy(), 3), rng)
    return res


def markets(f: pd.DataFrame, rng) -> dict:
    out = {}
    o = f.out.to_numpy()
    # O/U 2.5
    ou = f[(f.Over25 > 1) & (f.Under25 > 1) & f.FTHome.notna()]
    if len(ou):
        iv = 1 / ou[["Over25", "Under25"]].to_numpy()
        po = iv[:, 0] / iv.sum(1)
        yo = ((ou.FTHome + ou.FTAway) >= 3).astype(int).to_numpy()
        fav = np.maximum(po, 1 - po)
        favy = np.where(po >= 0.5, yo, 1 - yo)
        out["ou25"] = {"over_events": binary_block(po, yo, ou.mid.to_numpy(), rng),
                       "favoured_side": binary_block(fav, favy, ou.mid.to_numpy(), rng), "coverage": float(len(ou) / len(f))}
        # BTTS (market-implied independent Poisson from 1X2 + O/U; the frozen research engine's method)
        lam = fit_market_implied_lambdas(ou.pH.tolist(), ou.pA.tolist(), po.tolist(), DEFAULT_CONFIG)
        lh, la = np.array([x[0] for x in lam]), np.array([x[1] for x in lam])
        pb = (1 - np.exp(-lh)) * (1 - np.exp(-la))
        yb = ((ou.FTHome >= 1) & (ou.FTAway >= 1)).astype(int).to_numpy()
        favb = np.maximum(pb, 1 - pb)
        favby = np.where(pb >= 0.5, yb, 1 - yb)
        out["btts"] = {"yes_events": binary_block(pb, yb, ou.mid.to_numpy(), rng),
                       "favoured_side": binary_block(favb, favby, ou.mid.to_numpy(), rng)}
    # Draw No Bet (void on draw): P(home | not draw)
    nd = o != 1
    pdnb = (f.pH / (f.pH + f.pA)).to_numpy()[nd]
    ydnb = (o[nd] == 0).astype(int)
    fav = np.maximum(pdnb, 1 - pdnb)
    favy = np.where(pdnb >= 0.5, ydnb, 1 - ydnb)
    out["dnb"] = {"home_events": binary_block(pdnb, ydnb, f.mid.to_numpy()[nd], rng),
                  "favoured_side": binary_block(fav, favy, f.mid.to_numpy()[nd], rng), "draws_void": int((~nd).sum())}
    # Asian handicap: half-ball lines only (binary)
    ah = f[(f.HandiHome > 1) & (f.HandiAway > 1) & f.HandiSize.notna()]
    half = ah[np.isclose((ah.HandiSize.abs() * 2) % 2, 1)]
    if len(half):
        iv = 1 / half[["HandiHome", "HandiAway"]].to_numpy()
        ph = iv[:, 0] / iv.sum(1)
        yh = ((half.FTHome + half.HandiSize - half.FTAway) > 0).astype(int).to_numpy()
        fav = np.maximum(ph, 1 - ph)
        favy = np.where(ph >= 0.5, yh, 1 - yh)
        out["ah_half_lines"] = {"home_cover": binary_block(ph, yh, half.mid.to_numpy(), rng),
                                "favoured_side": binary_block(fav, favy, half.mid.to_numpy(), rng),
                                "excluded_whole_or_quarter_lines": int(len(ah) - len(half)), "with_ah_odds": int(len(ah))}
    return out


def grade(val: dict, conf: dict, key: str = "calibration") -> dict:
    periods = [x for x in (val, conf) if x and x.get("n_events", 0)]
    low = conf is None or conf.get("matches", conf.get("n_events", 0)) < LOW_N
    use = [val] if low else periods
    c1 = all(x[key]["slope_ci_includes_1"] for x in use)
    c2 = all(x["bands_ok"] for x in use)
    return {"C1_slope_ci_includes_1": c1, "C2_bands_ok": c2, "grade": "A" if c1 and c2 else ("B" if c1 or c2 else "C"),
            "confirmation_low_n": bool(low)}


def volume(d_league: pd.DataFrame, f_league: pd.DataFrame) -> dict:
    """Matches/week and paying-days/month under the Plan A 48h gate (2023/24-2025/26 fixture dates)."""
    recent = f_league[f_league.season.isin((2023, 2024, 2025))]
    if recent.empty:
        return {}
    days = pd.to_datetime(sorted(recent.date.dt.normalize().unique()))
    span_days = (recent.date.max() - recent.date.min()).days + 1
    seasons = recent.season.nunique()
    # a daily scan on day t pays if any fixture falls in (t, t+48h]: count calendar days with a fixture on t+1 or t+2
    pay = set()
    for x in days:
        pay.add(x - pd.Timedelta(days=1))
        pay.add(x - pd.Timedelta(days=2))
    del span_days
    weeks_in_season = float(np.mean([((g.date.max() - g.date.min()).days + 1) / 7 for _, g in recent.groupby("season")]))
    top = recent[["pH", "pD", "pA"]].max(axis=1)
    dcb = np.maximum.reduce([recent.pH + recent.pD, recent.pD + recent.pA, recent.pH + recent.pA])
    per_season = len(recent) / seasons
    return {"matches_per_season": per_season, "fixture_days_per_season": len(days) / seasons,
            "paying_days_per_season": len(pay) / seasons, "season_weeks": round(weeks_in_season, 1),
            "matches_per_week": per_season / max(weeks_in_season, 1),
            "credits_per_in_season_month_h2h_totals": 2 * len(pay) / seasons / (weeks_in_season / 4.345),
            "top1x2_ge70_per_season": float((top >= 0.7).sum() / seasons), "top1x2_ge80_per_season": float((top >= 0.8).sum() / seasons),
            "dc_best_ge80_per_season": float((dcb >= 0.8).sum() / seasons),
            "credits_per_season_h2h_totals": 2 * len(pay) / seasons}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    a = ap.parse_args(argv)
    d = load(a.data)
    f = one_x_two(d)
    rng = np.random.default_rng(SEED)
    res: dict = {"source": "xgabora/Club-Football-Match-Data-2000-2025@25882a58 data/Matches.csv", "sha256": SHA,
                 "estimator": "Bet365 single-book multiplicative de-vig (no fitting)", "leagues": {}}
    rows = []
    for lg in REFERENCE + CANDIDATES:
        dl, fl = d[d.Division == lg], f[f.Division == lg]
        L: dict = {"name": NAMES[lg], "role": "reference" if lg in REFERENCE else "candidate",
                   "matches_with_result": int(dl.FTResult.isin(["H", "D", "A"]).sum()), "matches_used": int(len(fl)), "periods": {}}
        for per, seas in PERIODS.items():
            fp = fl[fl.season.isin(seas)]
            dp = dl[dl.season.isin(seas) & dl.FTResult.isin(["H", "D", "A"])]
            if fp.empty:
                L["periods"][per] = {"matches": 0}
                continue
            r = league_1x2(fp, rng)
            r["odds_coverage"] = float(len(fp) / max(len(dp), 1))
            r["markets"] = markets(fp, rng)
            r["season_slopes"] = {int(s): irls(logit(g[["pH", "pD", "pA"]].to_numpy().ravel()), np.eye(3)[g.out.to_numpy()].ravel())[1]
                                  for s, g in fp.groupby("season") if len(g) >= LOW_N}
            L["periods"][per] = r
        val, conf = L["periods"].get("validation"), L["periods"].get("confirmation")
        L["grade_1x2"] = grade(val, conf)
        L["grade_dc"] = grade(val and val["dc_all_events"], conf and conf["dc_all_events"])
        for mk, sub in (("ou25", "over_events"), ("btts", "yes_events"), ("dnb", "home_events"), ("ah_half_lines", "home_cover")):
            v = val and val["markets"].get(mk, {}).get(sub)
            c = conf and conf["markets"].get(mk, {}).get(sub)
            L[f"grade_{mk}"] = grade(v, c) if v and v.get("n_events") else {"grade": "NO_DATA"}
        vc = pd.concat([fl[fl.season.isin(PERIODS["validation"])], fl[fl.season.isin(PERIODS["confirmation"])]])
        L["val_conf_matches"] = int(len(vc))
        cov_den = int(dl[dl.season.isin(PERIODS["validation"] + PERIODS["confirmation"]) & dl.FTResult.isin(["H", "D", "A"])].shape[0])
        L["val_conf_odds_coverage"] = float(len(vc) / max(cov_den, 1))
        L["volume"] = volume(dl, fl)
        res["leagues"][lg] = L
        v = L["periods"].get("validation", {})
        rows.append({"league": lg, "name": NAMES[lg], "role": L["role"], "val_conf_matches": L["val_conf_matches"],
                     "coverage": round(L["val_conf_odds_coverage"], 4), "grade_1x2": L["grade_1x2"]["grade"],
                     "grade_dc": L["grade_dc"]["grade"], "grade_ou25": L["grade_ou25"]["grade"], "grade_btts": L["grade_btts"]["grade"],
                     "grade_dnb": L["grade_dnb"]["grade"], "grade_ah": L["grade_ah_half_lines"]["grade"],
                     "val_logloss": round(v.get("multiclass_log_loss", float("nan")), 4),
                     "val_slope": round(v.get("calibration", {}).get("slope", float("nan")), 3),
                     "conf_slope": round(L["periods"].get("confirmation", {}).get("calibration", {}).get("slope", float("nan")), 3),
                     **{k: round(x, 2) for k, x in L["volume"].items()}})
        print(lg, rows[-1])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1, default=float))
    with (OUT / "LEAGUE_SUMMARY.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
