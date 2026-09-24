"""Phase V2-3 NBA Moneyline outcome prediction. Protocol: research/platform_v2/nba/NBA_MODEL_PROTOCOL.md

  --stage development : holdout seasons are dropped BEFORE any computation; Elo grid on development,
                        discovery + stability on development, fitted models reported on validation.
  --stage holdout     : requires HOLDOUT_SPEC.json matching its committed SHA-256; refuses a second run.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.models.logistic_regression import fit_logistic_regression
from prediction_markets_lab.nba.data import build_games
from prediction_markets_lab.nba.features import EloParams, elo_probabilities, team_state_features
from prediction_markets_lab.performance.binary_classification import (
    binary_auc, binary_brier_score, binary_log_loss, fit_calibration_intercept_slope)
from prediction_markets_lab.research import margin_removal_methods as mrm
from prediction_markets_lab.research import probability_reliability as rel

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data/raw/basketball"
OUT = REPO / "research/platform_v2/nba"
SPEC, SPEC_HASH, RESULTS = OUT / "HOLDOUT_SPEC.json", OUT / "HOLDOUT_SPEC.sha256", OUT / "HOLDOUT_RESULTS.json"
DEV = ("2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22")
VAL = ("2022-23", "2023-24")
HOLD = ("2024-25", "2025-26")
SEED = 20260924
Z_BONF = 2.807033768343811
L2 = 1.0
DATA_FEATURES = ["elo_logit", "rest_diff", "home_b2b", "away_b2b", "games_7d_diff", "roll10_pd_diff",
                 "roll10_win_diff", "season_pd_diff", "season_game_number", "neutral"]
DISCOVERY = ["elo_logit", "market_logit", "rest_diff", "home_rest", "away_rest", "home_b2b", "away_b2b",
             "games_7d_diff", "roll10_pd_diff", "roll10_win_diff", "season_pd_diff", "season_game_number"]
GRID = [EloParams(k=k, hca=h, mov=m) for k, h, m in itertools.product((10, 15, 20, 25), (50, 75, 100), (False, True))]


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def prepare(games: pd.DataFrame, elo: EloParams) -> pd.DataFrame:
    g = games.copy()
    g["p_elo"] = elo_probabilities(g, elo)
    g = team_state_features(g)
    g["elo_logit"] = lg(g.p_elo)
    ok = g.home_odds.notna() & g.away_odds.notna() & (g.home_odds > 1) & (g.away_odds > 1)
    g["p_market"] = np.nan
    g.loc[ok, "p_market"] = [mrm.devig([h, a], "multiplicative")[0] for h, a in zip(g.home_odds[ok], g.away_odds[ok])]
    g["market_logit"] = lg(g.p_market.fillna(0.5))
    g["neutral"] = g.neutral.astype(int)
    return g


class Std:
    def __init__(self, X, y, l2):
        X = np.asarray(X, float)
        self.m, self.s = X.mean(0), np.where(X.std(0) > 0, X.std(0), 1)
        self.fit = fit_logistic_regression((X - self.m) / self.s, list(y), [f"x{i}" for i in range(X.shape[1])], l2_penalty=l2)

    def predict(self, X):
        return self.fit.predict_proba((np.asarray(X, float) - self.m) / self.s)


def fit_models(train: pd.DataFrame) -> dict:
    y = train.home_win.values
    return {"data_logit": Std(train[DATA_FEATURES].values, y, L2),
            "stack_market_elo": Std(np.column_stack([train.market_logit, train.elo_logit]), y, 1e-6)}


def predict_all(d: pd.DataFrame, fitted: dict) -> dict[str, np.ndarray]:
    return {"market": d.p_market.values, "elo": d.p_elo.values,
            "data_logit": fitted["data_logit"].predict(d[DATA_FEATURES].values),
            "stack_market_elo": fitted["stack_market_elo"].predict(np.column_stack([d.market_logit, d.elo_logit]))}


def metrics(p, y) -> dict:
    pk, w = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
    i, s = fit_calibration_intercept_slope(list(p), list(y))
    return {"n": int(len(y)), "log_loss": binary_log_loss(list(p), list(y)), "brier": binary_brier_score(list(p), list(y)),
            "auc": binary_auc(list(p), list(y)), "cal_intercept": i, "cal_slope": s, "top_pick_accuracy": float(w.mean()),
            "mean_top_pick_p": float(pk.mean()), "expected_correct": float(pk.sum()), "actual_correct": int(w.sum()),
            "home_win_rate": float(np.mean(y))}


def slope_ci(p, y, n=1000):
    rng = np.random.default_rng(SEED)
    s = [fit_calibration_intercept_slope(list(p[i]), list(y[i]))[1] for i in (rng.integers(0, len(p), len(p)) for _ in range(n))]
    return [float(np.quantile(s, 0.025)), float(np.quantile(s, 0.975))]


def tables(tag, d, preds):
    y = d.home_win.values
    M, B, T, G = [], [], [], []
    for k, p in preds.items():
        M.append({"period": tag, "estimator": k, **metrics(p, y)})
        pk, w = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
        B += [{"period": tag, "estimator": k, **r} for r in rel.band_table(pk, w)]
        T += [{"period": tag, "estimator": k, **r} for r in rel.threshold_table(pk, w)]
        if k in ("market", "elo"):
            pick_home = p >= 0.5
            for name, mask in [(f"season={s}", d.season.values == s) for s in sorted(d.season.unique())] + \
                              [("stage=regular", d.stage.values == "regular"), ("stage=playoffs+play_in", d.stage.values != "regular"),
                               ("pick=home", pick_home), ("pick=away", ~pick_home)]:
                if mask.sum() == 0:
                    continue
                hi = pk[mask] >= 0.8
                lo_, hi_ = rel.wilson(int(w[mask][hi].sum()), int(hi.sum()))
                G.append({"period": tag, "estimator": k, "group": name, "n": int(mask.sum()),
                          "top_pick_accuracy": float(w[mask].mean()), "mean_top_pick_p": float(pk[mask].mean()),
                          "n_ge_80": int(hi.sum()), "share_ge_80": float(hi.mean()),
                          "mean_p_ge_80": float(pk[mask][hi].mean()) if hi.any() else None,
                          "win_rate_ge_80": float(w[mask][hi].mean()) if hi.any() else None, "wilson_low": lo_, "wilson_high": hi_})
    return M, B, T, G


def cohen(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else None


def development() -> None:
    games = build_games(RAW)
    games = games[~games.season.isin(HOLD)].reset_index(drop=True)  # holdout outcomes never enter this stage
    grid_rows = []
    for ep in GRID:
        p = np.array(elo_probabilities(games, ep))
        m = games.season.isin(DEV).values
        y = games.home_win.values[m]
        grid_rows.append({"k": ep.k, "hca": ep.hca, "mov": ep.mov, "dev_log_loss": binary_log_loss(list(p[m]), list(y))})
    grid = pd.DataFrame(grid_rows).sort_values("dev_log_loss")
    best = grid.iloc[0]
    elo = EloParams(k=float(best.k), hca=float(best.hca), mov=bool(best.mov))
    g = prepare(games, elo)
    dev, val = g[g.season.isin(DEV)].reset_index(drop=True), g[g.season.isin(VAL)].reset_index(drop=True)
    # discovery on development only: home-win vs home-loss
    disc = []
    for f in DISCOVERY:
        a, b = dev.loc[dev.home_win == 1, f], dev.loc[dev.home_win == 0, f]
        per = {s: cohen(dev.loc[(dev.season == s) & (dev.home_win == 1), f], dev.loc[(dev.season == s) & (dev.home_win == 0), f]) for s in DEV}
        signs = [np.sign(v) for v in per.values() if v is not None]
        disc.append({"feature": f, "mean_home_win": a.mean(), "mean_home_loss": b.mean(), "difference": a.mean() - b.mean(),
                     "cohens_d": cohen(a, b), "per_season_d": json.dumps({k: round(v, 3) if v is not None else None for k, v in per.items()}),
                     "seasons_same_sign": int(sum(1 for s_ in signs if s_ == np.sign(cohen(a, b) or 0))), "n_seasons": len(signs)})
    disc = pd.DataFrame(disc).sort_values("cohens_d", key=lambda s: -s.abs())
    fitted = fit_models(dev)
    M, B, T, G = [], [], [], []
    for tag, d in (("development_in_sample_fit", dev), ("validation_2022_24", val)):
        m, b, t, gg = tables(tag, d, predict_all(d, fitted))
        M += m; B += b; T += t; G += gg
    home_rate = {s: float(g.loc[g.season == s, "home_win"].mean()) for s in DEV + VAL}
    OUT.mkdir(parents=True, exist_ok=True)
    grid.to_csv(OUT / "NBA_ELO_GRID_DEVELOPMENT.csv", index=False)
    disc.to_csv(OUT / "NBA_OUTCOME_DISCOVERY.csv", index=False)
    pd.DataFrame(M).to_csv(OUT / "NBA_MODEL_COMPARISON_DEV_VAL.csv", index=False)
    pd.DataFrame(B).to_csv(OUT / "NBA_PROBABILITY_BANDS_DEV_VAL.csv", index=False)
    pd.DataFrame(T).to_csv(OUT / "NBA_HIGH_PROBABILITY_DEV_VAL.csv", index=False)
    pd.DataFrame(G).to_csv(OUT / "NBA_SUBGROUPS_DEV_VAL.csv", index=False)
    (OUT / "DEV_RESULTS.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
        "elo_selected": {"k": elo.k, "hca": elo.hca, "mov": elo.mov, "carry": elo.carry},
        "n_dev": len(dev), "n_val": len(val), "home_win_rate_by_season": home_rate}, indent=1))
    pd.set_option("display.width", 250)
    print(grid.head(6).round(5).to_string()); print(disc.round(4).to_string()); print(pd.DataFrame(M).round(4).to_string())
    print(json.dumps(home_rate, indent=0))


def holdout() -> None:
    if RESULTS.exists():
        sys.exit("REFUSED: NBA holdout already opened once.")
    if not SPEC.exists() or hashlib.sha256(SPEC.read_bytes()).hexdigest() != SPEC_HASH.read_text().split()[0]:
        sys.exit("REFUSED: HOLDOUT_SPEC.json missing or does not match its frozen hash.")
    spec = json.loads(SPEC.read_text())
    e = spec["elo"]
    g = prepare(build_games(RAW), EloParams(k=e["k"], hca=e["hca"], mov=e["mov"], carry=e["carry"]))
    fit_d = g[g.season.isin(DEV + VAL)].reset_index(drop=True)
    hold = g[g.season.isin(HOLD)].reset_index(drop=True)
    fitted = fit_models(fit_d)
    preds = predict_all(hold, fitted)
    M, B, T, G = tables("SEALED_HOLDOUT_2024_26", hold, preds)
    y = hold.home_win.values
    ll = {k: np.array([-math.log(max(pp if yy else 1 - pp, 1e-15)) for pp, yy in zip(v, y)]) for k, v in preds.items()}
    boot = []
    for k in preds:
        if k != spec["default_estimator"]:
            dm, lo, hi = rel.paired_bootstrap_ci(ll[k], ll[spec["default_estimator"]], seed=SEED)
            boot.append({"estimator": k, "log_loss_diff": dm, "ci95_low": lo, "ci95_high": hi, "better_and_excludes_zero": hi < 0})
    winners = [r for r in boot if r["better_and_excludes_zero"]]
    selected = min(winners, key=lambda r: r["log_loss_diff"])["estimator"] if winners else spec["default_estimator"]
    p = preds[selected]
    pk, w = np.maximum(p, 1 - p), np.where(p >= 0.5, y, 1 - y)
    checks = []
    for r in rel.band_table(pk, w):
        if r["n"] >= 200:
            lo, hi = rel.wilson(r["actual_wins"], r["n"], z=Z_BONF)
            checks.append({"band": r["band"], "n": r["n"], "mean_predicted": r["mean_predicted"], "actual_rate": r["actual_rate"],
                           "wilson995_low": lo, "wilson995_high": hi, "inside": lo <= r["mean_predicted"] <= hi})
    sci = slope_ci(p, y)
    slope_ok, bands_ok = sci[0] <= 1 <= sci[1], all(c["inside"] for c in checks)
    gate = "A" if slope_ok and bands_ok else ("B" if slope_ok or bands_ok else "C")
    for name, rows in (("NBA_MODEL_COMPARISON.csv", M), ("NBA_PROBABILITY_BANDS.csv", B),
                       ("NBA_HIGH_PROBABILITY_ANALYSIS.csv", T), ("NBA_SUBGROUPS_HOLDOUT.csv", G)):
        pd.DataFrame(rows).to_csv(OUT / name, index=False)
    res = {"opened_at": datetime.now(timezone.utc).isoformat(), "spec_sha256": SPEC_HASH.read_text().split()[0],
           "n_holdout": int(len(hold)), "selected_estimator": selected, "bootstrap_vs_default": boot,
           "selected_slope_ci95": sci, "band_checks_995": checks, "prediction_gate": gate,
           "elo_slope_ci95": slope_ci(preds["elo"], y), "home_win_rate": float(y.mean())}
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(M).round(4).to_string()); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", choices=("development", "holdout"), required=True)
    development() if ap.parse_args().stage == "development" else holdout()
