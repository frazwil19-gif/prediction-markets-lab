"""Phase 5 Section 22 -- quantify probability/price dependence when market consensus
is itself the probability engine (design evidence only; production untouched).

Uses football 1X2 CLOSING per-bookmaker prices (cycle_001_bookmaker_markets_full.csv,
per-bookmaker de-vigged fair probabilities already computed by the production
margin-removal code in Stage 3A) and actual results. Same-snapshot comparison only.

For every (match, outcome) it computes the EV of the best available price under
three reference probabilities:
  inclusive  -- mean de-vigged probability across ALL bookmakers (current V1 design)
  loo        -- same, but EXCLUDING the bookmaker offering the best price
  sharp_ref  -- Pinnacle (PS) de-vigged probability only, best price taken from the OTHER books
No thresholds are searched: the only split is EV > 0 (the minimal definition).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
BOOKS = REPO / "data/processed/football/cycle_001_bookmaker_markets_full.csv"
MATCHES = REPO / "data/processed/football/cycle_002_discovery_features.csv"
OUT = REPO / "research/btts_outcome_prediction/CONSENSUS_PRICE_INDEPENDENCE.json"
SHARP_BOOK = "PS"
SEED = 20260922
N_BOOT = 2000


def boot_ci(x: np.ndarray) -> list[float]:
    rng = np.random.default_rng(SEED)
    if len(x) == 0:
        return [float("nan"), float("nan")]
    m = x[rng.integers(0, len(x), size=(N_BOOT, len(x)))].mean(axis=1)
    return [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))]


def main() -> None:
    b = pd.read_csv(BOOKS)
    b = b[b.price_timing == "closing"]
    res = pd.read_csv(MATCHES, usecols=["match_id", "season", "outcome_full_time_result"])
    rows = []
    for outcome, oc, fc, code in (("home", "home_odds", "fair_home_probability", "H"),
                                  ("draw", "draw_odds", "fair_draw_probability", "D"),
                                  ("away", "away_odds", "fair_away_probability", "A")):
        t = b[["match_id", "bookmaker", oc, fc]].rename(columns={oc: "odds", fc: "fair"}).dropna()
        t["outcome"], t["code"] = outcome, code
        rows.append(t)
    long = pd.concat(rows).merge(res, on="match_id")
    out: dict = {"n_matches": int(long.match_id.nunique()), "snapshot": "closing", "methods": {}}
    recs = []
    for (mid, outcome), g in long.groupby(["match_id", "outcome"]):
        if len(g) < 3:
            continue
        i_best = g.odds.values.argmax()
        best = float(g.odds.values[i_best])
        won = int(g.code.values[0] == g.outcome_full_time_result.values[0])
        p_inc = float(g.fair.mean())
        p_loo = float(np.delete(g.fair.values, i_best).mean())
        r = {"match_id": mid, "season": g.season.values[0], "outcome": outcome, "best_odds": best,
             "best_book": g.bookmaker.values[i_best], "won": won, "p_inc": p_inc, "p_loo": p_loo}
        sharp = g[g.bookmaker == SHARP_BOOK]
        others = g[g.bookmaker != SHARP_BOOK]
        if len(sharp) == 1 and len(others) >= 1:
            r["p_sharp"] = float(sharp.fair.values[0])
            r["best_odds_ex_sharp"] = float(others.odds.max())
        recs.append(r)
    d = pd.DataFrame(recs)
    d["ev_inc"] = d.p_inc * d.best_odds - 1
    d["ev_loo"] = d.p_loo * d.best_odds - 1
    d["ev_sharp"] = d.p_sharp * d.best_odds_ex_sharp - 1
    d["pnl_best"] = np.where(d.won == 1, d.best_odds - 1, -1.0)
    d["pnl_ex_sharp"] = np.where(d.won == 1, d.best_odds_ex_sharp - 1, -1.0)
    out["n_candidates"] = int(len(d))
    out["mean_ev_inflation_inclusive_minus_loo"] = float((d.ev_inc - d.ev_loo).mean())
    out["share_candidates_where_inclusive_positive_but_loo_not"] = float(((d.ev_inc > 0) & (d.ev_loo <= 0)).mean())
    for name, ev, pnl in (("inclusive", "ev_inc", "pnl_best"), ("leave_one_bookmaker_out", "ev_loo", "pnl_best"),
                          ("sharp_reference_PS", "ev_sharp", "pnl_ex_sharp")):
        sel = d[d[ev] > 0].dropna(subset=[ev])
        pn = sel[pnl].to_numpy()
        out["methods"][name] = {
            "n_ev_positive": int(len(sel)), "share_ev_positive": float(len(sel) / d[ev].notna().sum()),
            "mean_claimed_ev": float(sel[ev].mean()) if len(sel) else None,
            "realised_roi": float(pn.mean()) if len(pn) else None, "realised_roi_ci95": boot_ci(pn),
            "mean_odds": float(sel.best_odds.mean()) if len(sel) else None,
            "roi_by_outcome": {o: {"n": int(len(s)), "roi": float(s[pnl].mean())} for o, s in sel.groupby("outcome")},
        }
    all_best = d.pnl_best.to_numpy()
    out["baseline_back_every_best_price"] = {"n": int(len(all_best)), "roi": float(all_best.mean()), "ci95": boot_ci(all_best)}
    out["caveats"] = [
        "Closing snapshot only: consensus and price drawn from the same instant (leakage-safe, but not a live scan-time replay).",
        "Best price among 4-6 football-data.co.uk bookmakers; live panel has ~20, so dispersion live is larger.",
        "No thresholds searched; EV>0 is the only split. This is design evidence, not a strategy backtest.",
    ]
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
