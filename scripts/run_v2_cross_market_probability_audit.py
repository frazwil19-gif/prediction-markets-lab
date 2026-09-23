"""Platform V2 audit -- cross-market probability-band / high-probability coverage and
empirical multi-dependency evidence, computed ONLY from existing frozen outputs.
No model is fitted, no threshold chosen, nothing in production touched.

Sources (all already in the repo):
  football 1X2     backtests/money-strategy-v1-frozen/2026-09-22-phase1-primary-closing/predictions.csv (de-vigged closing consensus)
  football OU2.5   research/ou25_discovery/predictions_market.csv (walk-forward OOS, thin-panel market)
  football BTTS    research/btts_outcome_prediction/predictions_{development,holdout}.csv (market_implied_poisson)
  tennis Elo       data/interim/cycle_002_tennis_2025_holdout_predictions.csv (sealed 2025 holdout, Global Elo)
  tennis market    data/interim/workstream_b_2021_2023_discovery_dataset.csv (Betfair price 30 min pre-start; descriptive only)
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research" / "platform_v2"
BANDS = [(0.0, 0.5, "<50%"), (0.5, 0.55, "50-54.9%"), (0.55, 0.6, "55-59.9%"), (0.6, 0.65, "60-64.9%"),
         (0.65, 0.7, "65-69.9%"), (0.7, 0.75, "70-74.9%"), (0.75, 0.8, "75-79.9%"), (0.8, 0.9, "80-89.9%"),
         (0.9, 1.0000001, "90%+")]
THRESHOLDS = (0.60, 0.65, 0.70, 0.75, 0.80, 0.90)
Z = 1.959963984540054


def wilson(k: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def picks(engine: str, p: np.ndarray, won: np.ndarray) -> pd.DataFrame:
    """Top pick per event: for binary engines the more likely side."""
    return pd.DataFrame({"engine": engine, "p": p, "won": won.astype(int)})


def load_engines() -> dict[str, pd.DataFrame]:
    e: dict[str, pd.DataFrame] = {}
    x = pd.read_csv(REPO / "backtests/money-strategy-v1-frozen/2026-09-22-phase1-primary-closing/predictions.csv",
                    usecols=["match_id", "selection", "consensus_probability", "actual_won", "event_date"])
    x = x.dropna(subset=["consensus_probability"])
    top = x.loc[x.groupby("match_id").consensus_probability.idxmax()]
    e["football_1x2_market_consensus"] = picks("football_1x2_market_consensus", top.consensus_probability.to_numpy(),
                                               top.actual_won.astype(bool).to_numpy())
    o = pd.read_csv(REPO / "research/ou25_discovery/predictions_market.csv")
    po = o.predicted_probability.to_numpy()
    e["football_ou25_market"] = picks("football_ou25_market", np.maximum(po, 1 - po),
                                      np.where(po > 0.5, o.actual == 1, o.actual == 0))
    b = pd.concat([pd.read_csv(REPO / f"research/btts_outcome_prediction/predictions_{s}.csv") for s in ("development", "holdout")])
    b = b[b.model == "market_implied_poisson"]
    pb = b.p_yes.to_numpy()
    e["football_btts_market_implied"] = picks("football_btts_market_implied", np.maximum(pb, 1 - pb),
                                              np.where(pb > 0.5, b.actual == 1, b.actual == 0))
    t = pd.read_csv(REPO / "data/interim/cycle_002_tennis_2025_holdout_predictions.csv")
    pt = t.global_elo_p_a_win.to_numpy()
    e["tennis_winner_global_elo_2025_holdout"] = picks("tennis_winner_global_elo_2025_holdout", np.maximum(pt, 1 - pt),
                                                       np.where(pt > 0.5, t.outcome_a_won == 1, t.outcome_a_won == 0))
    m = pd.read_csv(REPO / "data/interim/workstream_b_2021_2023_discovery_dataset.csv",
                    usecols=["market_prob_a_30min", "outcome_a_won"]).dropna()
    pm = m.market_prob_a_30min.to_numpy()
    e["tennis_winner_betfair_market_30min"] = picks("tennis_winner_betfair_market_30min", np.maximum(pm, 1 - pm),
                                                    np.where(pm > 0.5, m.outcome_a_won == 1, m.outcome_a_won == 0))
    return e


def band_table(name: str, d: pd.DataFrame) -> list[dict]:
    rows = []
    for lo, hi, lab in BANDS:
        s = d[(d.p >= lo) & (d.p < hi)]
        n, k = len(s), int(s.won.sum())
        wl, wh = wilson(k, n)
        rows.append({"engine": name, "band": lab, "n": n, "mean_p": s.p.mean() if n else None, "occurred": k,
                     "actual_rate": k / n if n else None,
                     "calibration_error_pp": (k / n - s.p.mean()) * 100 if n else None, "wilson_low": wl, "wilson_high": wh})
    return rows


def threshold_table(name: str, d: pd.DataFrame) -> list[dict]:
    rows = []
    for t in THRESHOLDS:
        s = d[d.p >= t]
        n, k = len(s), int(s.won.sum())
        wl, wh = wilson(k, n)
        rows.append({"engine": name, "threshold": t, "n": n, "share_of_events": n / len(d), "mean_p": s.p.mean() if n else None,
                     "actual_rate": k / n if n else None, "wilson_low": wl, "wilson_high": wh})
    return rows


def summary(name: str, d: pd.DataFrame) -> dict:
    p = d.p.clip(1e-12, 1 - 1e-12)
    return {"engine": name, "n_events": len(d), "top_pick_accuracy": d.won.mean(), "mean_top_pick_p": d.p.mean(),
            "top_pick_log_loss": float(-(d.won * np.log(p) + (1 - d.won) * np.log(1 - p)).mean()),
            "top_pick_brier": float(((d.p - d.won) ** 2).mean()), "max_p": d.p.max()}


def cross_event_dependency() -> dict:
    """Same-date, DIFFERENT-match pairs of 1X2 favourites with consensus >= 0.70:
    realised joint win rate vs mean product of probabilities (independence check)."""
    x = pd.read_csv(REPO / "backtests/money-strategy-v1-frozen/2026-09-22-phase1-primary-closing/predictions.csv",
                    usecols=["match_id", "consensus_probability", "actual_won", "event_date", "competition_code"]).dropna()
    fav = x.loc[x.groupby("match_id").consensus_probability.idxmax()]
    fav = fav[fav.consensus_probability >= 0.70]
    pairs = []
    for _, g in fav.groupby("event_date"):
        for a, b in itertools.combinations(g.itertuples(), 2):
            pairs.append((a.consensus_probability * b.consensus_probability, int(a.actual_won and b.actual_won),
                          a.competition_code == b.competition_code))
    arr = np.array([(p, w) for p, w, _ in pairs]) if pairs else np.zeros((0, 2))
    same = np.array([s for *_, s in pairs])
    out = {"favourite_threshold": 0.70, "n_favourites": int(len(fav)),
           "favourite_single_rate": float(fav.actual_won.mean()), "favourite_mean_p": float(fav.consensus_probability.mean())}
    for lab, mask in (("all_pairs", np.ones(len(arr), bool)), ("same_competition", same), ("different_competition", ~same)):
        s = arr[mask]
        n, k = len(s), int(s[:, 1].sum()) if len(s) else 0
        wl, wh = wilson(k, n)
        out[lab] = {"n_pairs": n, "mean_product_p": float(s[:, 0].mean()) if n else None,
                    "realised_joint_rate": k / n if n else None, "wilson_low": wl, "wilson_high": wh,
                    "note": "pairs share dates, so they are not independent observations; CI is optimistic"}
    return out


def same_game_dependency() -> dict:
    """Same-match: home win AND over 2.5 -- empirical joint vs product of marginals and vs product of market probs."""
    f = pd.read_csv(REPO / "data/processed/football/cycle_002_discovery_features.csv",
                    usecols=["outcome_full_time_home_goals", "outcome_full_time_away_goals", "market_1x2_closing_home_probability",
                             "market_ou25_closing_source_avg_over_probability"]).dropna()
    hg, ag = f.outcome_full_time_home_goals, f.outcome_full_time_away_goals
    home, over, btts = (hg > ag), (hg + ag > 2.5), (hg > 0) & (ag > 0)
    res = {"n": int(len(f))}
    for lab, a, b in (("home_win_and_over25", home, over), ("home_win_and_btts", home, btts), ("over25_and_btts", over, btts)):
        joint = float((a & b).mean())
        prod = float(a.mean() * b.mean())
        res[lab] = {"p_a": float(a.mean()), "p_b": float(b.mean()), "realised_joint": joint, "independence_product": prod,
                    "ratio_joint_to_product": joint / prod}
    fav = f.market_1x2_closing_home_probability >= 0.60
    s = f[fav]
    hs, as_ = s.outcome_full_time_home_goals, s.outcome_full_time_away_goals
    j = float(((hs > as_) & (hs + as_ > 2.5)).mean())
    pp = float((s.market_1x2_closing_home_probability * s.market_ou25_closing_source_avg_over_probability).mean())
    res["strong_home_favourites_home_win_and_over25"] = {"n": int(len(s)), "realised_joint": j, "market_product": pp,
                                                         "ratio": j / pp}
    return res


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    engines = load_engines()
    bands, thr, summ = [], [], []
    for k, d in engines.items():
        bands += band_table(k, d)
        thr += threshold_table(k, d)
        summ.append(summary(k, d))
    pd.DataFrame(bands).to_csv(OUT / "CROSS_MARKET_PROBABILITY_BANDS.csv", index=False)
    pd.DataFrame(thr).to_csv(OUT / "CROSS_MARKET_HIGH_PROBABILITY.csv", index=False)
    dep = {"engine_summaries": summ, "cross_event_1x2_favourite_pairs": cross_event_dependency(),
           "same_game_football": same_game_dependency()}
    (OUT / "CROSS_MARKET_AND_DEPENDENCY_EVIDENCE.json").write_text(json.dumps(dep, indent=1, default=float))
    print(pd.DataFrame(summ).round(4).to_string())
    print(pd.DataFrame(thr).round(4).to_string())
    print(json.dumps({k: v for k, v in dep.items() if k != "engine_summaries"}, indent=1, default=float))


if __name__ == "__main__":
    main()
