"""V2-6H historical bet-selection backtest (pre-registered: research/platform_v2/historical_v2_6h/PREREGISTRATION.md).

Retrospective research simulation only: never writes paper selections, never touches engines/holdouts/ledgers.
Usage: python scripts/v2_6h_historical_backtest.py --football-dir <dir with cycle_001_*_full.csv and h_fb2_002 files>
                                                   --nba-dir <wippa dir> [--out research/platform_v2/historical_v2_6h]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.bet_selection_v2.evaluate import load_config

REPO = Path(__file__).resolve().parents[1]
SEED = 20260929
N_BOOT = 2000
PRIMARY = {"B365": 0.0, "WH": 0.0, "BW": 0.0, "BF": 0.05}          # pre-registered UK-executable set
SENS_EXTRA = {"PS": 0.0, "1XB": 0.0, "BFD": 0.0, "BMGM": 0.0, "BV": 0.0, "CL": 0.0, "LB": 0.0}
OUTC = {"home": "H", "draw": "D", "away": "A"}
P_BANDS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
ODDS_BANDS = [1.0, 1.33, 1.5, 2.0, 3.0, 1e9]


def boot_ci(pnl: np.ndarray, stake: np.ndarray, rng: np.random.Generator) -> tuple[float | None, float | None]:
    n = len(pnl)
    if n < 2:
        return None, None
    idx = rng.integers(0, n, size=(N_BOOT, n))
    roi = pnl[idx].sum(1) / stake[idx].sum(1)
    return float(np.percentile(roi, 2.5)), float(np.percentile(roi, 97.5))


def dd_streak(pnl_sorted: np.ndarray, won_sorted: np.ndarray) -> tuple[float, int]:
    cum = np.cumsum(pnl_sorted)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    dd = float((peak - cum).max()) if len(cum) else 0.0
    streak = best = 0
    for w in won_sorted:
        streak = 0 if w else streak + 1
        best = max(best, streak)
    return round(dd, 3), best


# ---------------------------------------------------------------- football
def load_football(d: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    b1 = pd.read_csv(d / "cycle_001_bookmaker_markets_full.csv")
    m1 = pd.read_csv(d / "cycle_001_matches_full.csv")
    b2 = pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_bookmaker_markets.csv")
    m2 = pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_matches.csv")
    cols = ["match_id", "competition_code", "season", "match_date", "full_time_result"]
    m = pd.concat([m1[cols], m2[cols]], ignore_index=True).drop_duplicates("match_id")
    b = pd.concat([b1, b2], ignore_index=True)
    return b, m


def consensus(b: pd.DataFrame, exclude_book: str | None = None) -> pd.DataFrame:
    """Frozen engine: median across books of per-book proportional fair probabilities, same snapshot, >=3 books."""
    x = b if exclude_book is None else b[b.bookmaker != exclude_book]
    g = x.groupby(["match_id", "price_timing"])
    c = g[["fair_home_probability", "fair_draw_probability", "fair_away_probability"]].median()
    c["n_books"] = g.size()
    c = c[c.n_books >= 3]
    return c.rename(columns={"fair_home_probability": "home", "fair_draw_probability": "draw",
                             "fair_away_probability": "away"}).reset_index()


def football_candidates(b: pd.DataFrame, m: pd.DataFrame, books: dict[str, float], snapshot: str,
                        loo: bool = False) -> pd.DataFrame:
    """One row per (match, outcome, executable book) at one snapshot, with P from the (inclusive or LOO) consensus."""
    rows = []
    bs = b[b.price_timing == snapshot]
    cons_all = consensus(bs).set_index("match_id")
    for book, comm in books.items():
        q = bs[bs.bookmaker == book].set_index("match_id")
        if q.empty:
            continue
        cons = consensus(bs, exclude_book=book).set_index("match_id") if loo else cons_all
        j = q.join(cons, how="inner", rsuffix="_c")
        for sel, col in (("home", "home_odds"), ("draw", "draw_odds"), ("away", "away_odds")):
            p = j[sel].astype(float)
            o = j[col].astype(float)
            ok = o > 1.0
            rows.append(pd.DataFrame({"match_id": j.index[ok], "snapshot": snapshot, "selection": sel, "book": book,
                                      "commission": comm, "p": p[ok].values, "odds": o[ok].values,
                                      "n_books": j["n_books"][ok].values}))
    c = pd.concat(rows, ignore_index=True)
    c["net_ev"] = c.p * (c.odds - 1) * (1 - c.commission) - (1 - c.p)
    c = c.merge(m, on="match_id", how="inner")
    c["won"] = (c.full_time_result == c.selection.map(OUTC)).astype(int)
    c["pnl"] = np.where(c.won == 1, (c.odds - 1) * (1 - c.commission), -1.0)
    return c


def decide(c: pd.DataFrame, gates: dict, ev_floor: float | None = None) -> pd.DataFrame:
    """Best net-EV executable book per (match, selection); bsv2-1 PAPER_BET gates (EV floor overridable ONLY for
    labelled descriptive sensitivities)."""
    best = c.sort_values("net_ev", ascending=False).drop_duplicates(["match_id", "selection"])
    floor = gates["min_net_ev"] if ev_floor is None else ev_floor
    best = best.assign(qualifies=(best.p >= gates["min_probability"]) & (best.net_ev >= floor)
                       & (best.odds >= gates["min_decimal_odds"]))
    return best


def summarise(sel: pd.DataFrame, rng: np.random.Generator) -> dict:
    n = len(sel)
    if n == 0:
        return {"n": 0}
    s = sel.sort_values(["match_date", "match_id"])
    lo, hi = boot_ci(s.pnl.values, np.ones(n), rng)
    dd, streak = dd_streak(s.pnl.values, s.won.values)
    days = s.match_date.nunique()
    return {"n": n, "win_rate": round(s.won.mean(), 4), "avg_p": round(s.p.mean(), 4), "avg_odds": round(s.odds.mean(), 3),
            "mean_est_net_ev": round(s.net_ev.mean(), 4), "expected_units": round(s.net_ev.sum(), 2),
            "realised_units": round(s.pnl.sum(), 2), "roi": round(s.pnl.sum() / n, 4),
            "roi_ci95": [None if lo is None else round(lo, 4), None if hi is None else round(hi, 4)],
            "max_drawdown_units": dd, "longest_losing_streak": streak, "match_days_with_selection": days}


def period(season: str) -> str:
    return {"2024_25": "2024/25 (Cycle-1 sealed holdout, opened)", "2025_26": "2025/26 (H-FB2-002 OOS, opened)"}.get(
        season, "2020/21-2023/24 (development era)")


def football_study(d: Path, gates: dict) -> dict:
    rng = np.random.default_rng(SEED)
    b, m = load_football(d)
    out: dict = {"matches": int(m.match_id.nunique()), "seasons": sorted(m.season.unique().tolist())}
    for snap, label in (("closing", "A_closing_primary"), ("opening", "B_opening_secondary_horizon_not_evaluable")):
        c = football_candidates(b, m, PRIMARY, snap)
        best = decide(c, gates)
        q = best[best.qualifies]
        res = {"candidates_match_selection": int(len(best)), "p_ge_0_5": int((best.p >= 0.5).sum()),
               "priced_positive_ev": int(((best.p >= 0.5) & (best.net_ev > 0)).sum()),
               "qualifying": int(len(q)), "qualifying_rate_of_p_ge_0_5": round(len(q) / max(1, (best.p >= 0.5).sum()), 4),
               "per_match_day": round(len(q) / max(1, best.match_date.nunique()), 3),
               "overall": summarise(q, rng),
               "by_period": {k: summarise(g, rng) for k, g in q.groupby(q.season.map(period))},
               "by_season": {k: summarise(g, rng) for k, g in q.groupby("season")},
               "by_league": {k: summarise(g, rng) for k, g in q.groupby("competition_code")},
               "by_book": {k: summarise(g, rng) for k, g in q.groupby("book")},
               "by_p_band": {str(k): summarise(g, rng) for k, g in q.groupby(pd.cut(q.p, P_BANDS, right=False), observed=True)},
               "by_odds_band": {str(k): summarise(g, rng) for k, g in q.groupby(pd.cut(q.odds, ODDS_BANDS, right=False), observed=True)},
               # all P>=0.5 favourites at the best primary price, no value filter: the "accurate prediction" baseline
               "all_p_ge_0_5_no_value_filter": summarise(best[best.p >= 0.5], rng)}
        # descriptive sensitivities (never used to choose rules)
        sens = {}
        for f in (0.0, 0.05):
            qq = decide(c, gates, ev_floor=f)
            sens[f"ev_floor_{f}"] = summarise(qq[qq.qualifies], rng)
        cl = football_candidates(b, m, PRIMARY, snap, loo=True)
        ql = decide(cl, gates)
        sens["leave_one_out_consensus"] = summarise(ql[ql.qualifies], rng)
        ce = football_candidates(b, m, {**PRIMARY, **SENS_EXTRA}, snap)
        qe = decide(ce, gates)
        sens["primary_plus_PS_1XB_and_2025_26_UK_books"] = summarise(qe[qe.qualifies], rng)
        res["sensitivities_descriptive_only"] = sens
        if snap == "opening":   # CLV of opening selections vs closing consensus fair odds (same match/selection)
            cc = consensus(b[b.price_timing == "closing"]).melt(id_vars=["match_id"], value_vars=["home", "draw", "away"],
                                                                var_name="selection", value_name="p_close")
            j = q.merge(cc, on=["match_id", "selection"], how="inner")
            clv = j.odds * j.p_close - 1
            res["clv_vs_closing_fair"] = {"n": int(len(j)), "mean": round(float(clv.mean()), 4) if len(j) else None,
                                          "share_positive": round(float((clv > 0).mean()), 4) if len(j) else None}
        out[label] = res
    return out


def ou25_study(d: Path, gates: dict) -> dict:
    """O/U 2.5: frozen >=3-book median consensus; UK-executable books in this panel: B365, BFE (5%)."""
    f = d / "cycle_002_bookmaker_markets_ou25.csv"
    if not f.exists():
        return {"status": "panel not supplied"}
    b = pd.read_csv(f)
    out = {}
    for snap in ("closing", "opening"):
        x = b[b.price_timing == snap]
        g = x.groupby("match_id")
        c = g[["fair_over_2_5_probability", "fair_under_2_5_probability"]].median()
        c["n_books"] = g.size()
        c = c[c.n_books >= 3]
        q = x[x.bookmaker.isin(["B365", "BFE"])].join(c, on="match_id", how="inner", rsuffix="_c")
        rows = []
        for sel, oc, pc in (("over", "over_2_5_odds", "fair_over_2_5_probability_c"),
                            ("under", "under_2_5_odds", "fair_under_2_5_probability_c")):
            comm = np.where(q.bookmaker == "BFE", 0.05, 0.0)
            rows.append(pd.DataFrame({"match_id": q.match_id, "sel": sel, "p": q[pc], "odds": q[oc],
                                      "net_ev": q[pc] * (q[oc] - 1) * (1 - comm) - (1 - q[pc])}))
        dd = pd.concat(rows).sort_values("net_ev", ascending=False).drop_duplicates(["match_id", "sel"])
        fav = dd[dd.p >= gates["min_probability"]]
        out[snap] = {"matches_with_3_books": int(len(c)), "p_ge_0_5": int(len(fav)),
                     "positive_ev": int((fav.net_ev > 0).sum()),
                     "qualifying": int(((fav.net_ev >= gates["min_net_ev"]) & (fav.odds >= gates["min_decimal_odds"])).sum()),
                     "note": "only 2024/25 has 3 books (B365, Pinnacle, Betfair Exchange); earlier seasons fail the frozen >=3-book rule"}
    return out


# ---------------------------------------------------------------- tennis (self-source structure + calibration repro)
def calib(p: np.ndarray, y: np.ndarray) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    n = len(p)
    bands = {}
    for lo in (0.5, 0.6, 0.7, 0.8, 0.9):
        k = (p >= lo) & (p < lo + 0.1 if lo < 0.9 else p <= 1)
        if k.sum():
            bands[f"{int(lo*100)}-{int(lo*100)+9}%"] = {"n": int(k.sum()), "pred": round(float(p[k].mean()), 4),
                                                       "actual": round(float(y[k].mean()), 4)}
    x = np.log(p / (1 - p))
    slope = float(np.polyfit(x, y, 1)[0]) if n > 50 else None  # rough; the committed holdout reports use logistic slope
    return {"n": n, "brier": round(float(((p - y) ** 2).mean()), 5),
            "log_loss": round(float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()), 5), "bands_fav_side": bands}


def tennis_study(path: Path, holdout_years: tuple[int, ...]) -> dict:
    t = pd.read_csv(path)
    t = t.dropna(subset=["ltp_a", "ltp_b", "outcome_a_won", "p_a_market_multiplicative"])
    pa = t.p_a_market_multiplicative.values
    y = t.outcome_a_won.values.astype(int)
    fav_p = np.where(pa >= 0.5, pa, 1 - pa)
    fav_y = np.where(pa >= 0.5, y, 1 - y)
    fav_ltp = np.where(pa >= 0.5, t.ltp_a.values, t.ltp_b.values)
    hold = t.year.isin(holdout_years).values
    ev = fav_p * (fav_ltp - 1) * 0.95 - (1 - fav_p)
    pnl = np.where(fav_y == 1, (fav_ltp - 1) * 0.95, -1.0)
    out = {"rows": int(len(t)), "years": sorted(t.year.unique().tolist()),
           "calibration_favourite_side": {"development": calib(fav_p[~hold], fav_y[~hold]),
                                          "holdout": calib(fav_p[hold], fav_y[hold])},
           "self_source_at_ltp_with_5pct_commission": {
               "share_net_ev_positive": round(float((ev > 0).mean()), 4), "mean_net_ev": round(float(ev.mean()), 4),
               "level_stake_roi_all_favourites": round(float(pnl.mean()), 4),
               "note": "LTP is the probability source itself; with a ~1.00 book sum EV is ~ -commission share: structurally negative"}}
    return out


# ---------------------------------------------------------------- NBA
def nba_study(d: Path) -> dict:
    frames = []
    for f in sorted(d.glob("nba_*_results_odds.csv")):
        x = pd.read_csv(f)
        x["season"] = f.stem.split("_")[1]
        frames.append(x)
    n = pd.concat(frames, ignore_index=True)
    n = n[(n.is_allstar.astype(str) != "True") & (n["round"].astype(str) != "Pre-season")]
    n = n.dropna(subset=["home_odds", "away_odds"])
    ih, ia = 1 / n.home_odds, 1 / n.away_odds
    ph = ih / (ih + ia)
    y = n.home_win.astype(str).eq("True").astype(int).values
    fav_p = np.where(ph >= 0.5, ph, 1 - ph)
    fav_y = np.where(ph >= 0.5, y, 1 - y)
    fav_o = np.where(ph >= 0.5, n.home_odds, n.away_odds)
    ev = fav_p * (fav_o - 1) - (1 - fav_p)
    return {"games": int(len(n)), "seasons": sorted(n.season.unique().tolist()),
            "median_book_sum": round(float((ih + ia).median()), 4),
            "calibration_favourite_side": calib(fav_p, fav_y),
            "self_source_at_average_price": {"mean_net_ev": round(float(ev.mean()), 4),
                                             "share_positive": round(float((ev > 0).mean()), 4),
                                             "note": "the only price is an OddsPortal average: not executable, and EV = -margin by construction"}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--football-dir", type=Path, required=True)
    ap.add_argument("--nba-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=REPO / "research/platform_v2/historical_v2_6h")
    a = ap.parse_args()
    cfg = load_config()
    gates = cfg["decision_gates"]["paper_bet"]
    res = {"rule_version": cfg["rule_version"], "preregistration": "research/platform_v2/historical_v2_6h/PREREGISTRATION.md",
           "label": "RETROSPECTIVE RESEARCH SIMULATION -- not paper bets, not prospective evidence",
           "football_1x2": football_study(a.football_dir, gates),
           "football_ou25": ou25_study(a.football_dir, gates),
           "tennis_atp": tennis_study(REPO / "data/interim/v2_tennis_market_dataset.csv", (2024, 2025)),
           "tennis_wta": tennis_study(REPO / "data/interim/v2_wta_market_dataset.csv", (2024, 2025)),
           "nba": nba_study(a.nba_dir)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "V2_6H_RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: (v if k != "football_1x2" else {kk: vv.get("overall") if isinstance(vv, dict) else vv
                                                           for kk, vv in v.items()}) for k, v in res.items()}, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
