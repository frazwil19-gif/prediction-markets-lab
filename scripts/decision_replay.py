"""Historical decision replay / bet-characteristics audit (pre-registered:
research/platform_v2/decision_replay/PREREGISTRATION.md). READ-ONLY research: never writes paper selections, never
changes production config. Price-evidence classes: B SAME-TIME PROXY (football pre-closing), C CLOSING PROXY,
D NOT REPLAYABLE (no financial conclusions).

Usage: python scripts/decision_replay.py --football-dir <processed/football> --tennis-dir <tennis_data_co_uk>
         --atp-canonical <cycle_002_canonical_matches.csv> --nba-dir <wippa_nba> --xgabora <Matches.csv>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.bet_selection_v2.bankroll import simulate
from prediction_markets_lab.bet_selection_v2.evaluate import load_config as load_bs
from prediction_markets_lab.prediction_platform import stage_a as SA

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/decision_replay"
SEED, N_BOOT, N_MC = 20261001, 2000, 10000
UK_BOOKS = {"B365": 0.0, "WH": 0.0, "BW": 0.0, "BF": 0.05}          # V2-6H pre-registered UK-executable set
OUTC = {"home": "H", "draw": "D", "away": "A"}
P_BANDS = [(0, .6, "<60"), (.6, .65, "60-65"), (.65, .7, "65-70"), (.7, .75, "70-75"), (.75, .8, "75-80"), (.8, .85, "80-85"),
           (.85, .9, "85-90"), (.9, 1.01, "90+")]
ODDS_BANDS = [(1, 1.2, "<1.20"), (1.2, 1.33, "1.20-1.32"), (1.33, 1.5, "1.33-1.49"), (1.5, 1.75, "1.50-1.74"),
              (1.75, 2.0, "1.75-1.99"), (2.0, 1e9, "2.00+")]
EV_BANDS = [(-9, 0, "<0"), (0, .02, "0-2%"), (.02, .04, "2-4%"), (.04, .06, "4-6%"), (.06, .10, "6-10%"), (.10, 99, "10%+")]
GRID = {"odds": [1.20, 1.25, 1.30, 1.33, 1.40, 1.50], "ev": [0.0, 0.01, 0.02, 0.03, 0.05],
        "p": [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90], "zsig": [0.0, 0.5, 1.0, 1.645]}
XG_LEAGUES = ["N1", "D1", "F1", "SP1", "I1", "P1", "B1", "E2", "E3", "SP2", "D2", "I2", "F2"]


def band(x, bands):
    for lo, hi, lab in bands:
        if lo <= x < hi:
            return lab
    return "?"


def ev(p, odds, comm):
    return p * (odds - 1) * (1 - comm) - (1 - p)


# ------------------------------------------------------------------------------------------------ statistics
def calib(p: np.ndarray, y: np.ndarray) -> dict:
    """Logistic recalibration y ~ a + b*logit(p) by IRLS; slope CI from the Fisher information."""
    p = np.clip(p, 1e-6, 1 - 1e-6)
    X = np.column_stack([np.ones_like(p), np.log(p / (1 - p))])
    w = np.zeros(2)
    for _ in range(50):
        mu = 1 / (1 + np.exp(-X @ w))
        W = mu * (1 - mu)
        H = X.T @ (X * W[:, None])
        step = np.linalg.solve(H, X.T @ (y - mu))
        w += step
        if np.abs(step).max() < 1e-9:
            break
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return {"intercept": round(float(w[0]), 4), "slope": round(float(w[1]), 4),
            "slope_ci95": [round(float(w[1] - 1.96 * se[1]), 4), round(float(w[1] + 1.96 * se[1]), 4)]}


def prob_metrics(df: pd.DataFrame) -> dict:
    """df: p, won, date (event-level rows; p of the evaluated selection)."""
    if df.empty:
        return {"n": 0}
    p, y = df.p.to_numpy(float), df.won.to_numpy(float)
    eps = 1e-12
    out = {"n": int(len(df)), "mean_p": round(p.mean(), 4), "win_rate": round(y.mean(), 4),
           "expected_wins": round(p.sum(), 1), "actual_wins": int(y.sum()),
           "brier": round(float(((p - y) ** 2).mean()), 5),
           "log_loss": round(float(-(y * np.log(np.clip(p, eps, 1)) + (1 - y) * np.log(np.clip(1 - p, eps, 1))).mean()), 5)}
    if len(df) >= 50 and 0 < y.mean() < 1:
        out["calibration"] = calib(p, y)
    return out


def bands_table(fav: pd.DataFrame) -> dict:
    t = {}
    for lo, hi, lab in P_BANDS:
        g = fav[(fav.p >= lo) & (fav.p < hi)]
        if len(g):
            lo_w, hi_w = wilson(int(g.won.sum()), len(g))
            t[lab] = {"n": int(len(g)), "mean_p": round(g.p.mean(), 4), "win_rate": round(g.won.mean(), 4),
                      "calibration_error": round(g.won.mean() - g.p.mean(), 4), "wilson95": [lo_w, hi_w]}
    return t


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def longest_fail(df: pd.DataFrame) -> int:
    best = run = 0
    for w in df.sort_values("date").won:
        run = 0 if w else run + 1
        best = max(best, run)
    return best


def prob_replay(fav: pd.DataFrame, season_col: str = "season") -> dict:
    strong = fav[fav.p >= 0.70]
    return {"favourite_side": prob_metrics(fav), "bands": bands_table(fav),
            "by_season": {str(k): prob_metrics(g) for k, g in fav.groupby(season_col)},
            "strong_ge70": prob_metrics(strong), "strong_ge70_longest_failed_run": longest_fail(strong) if len(strong) else 0}


def boot_roi(pnl: np.ndarray, rng) -> list:
    if len(pnl) < 2:
        return [None, None]
    r = pnl[rng.integers(0, len(pnl), size=(N_BOOT, len(pnl)))].mean(1)
    return [round(float(np.percentile(r, 2.5)), 4), round(float(np.percentile(r, 97.5)), 4)]


def fin(g: pd.DataFrame, rng) -> dict:
    if g.empty:
        return {"n": 0}
    s = g.sort_values("date")
    cum = s.pnl.cumsum().to_numpy()
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    return {"n": int(len(s)), "win_rate": round(s.won.mean(), 4), "expected_win_rate": round(s.p.mean(), 4),
            "calibration_error": round(s.won.mean() - s.p.mean(), 4), "avg_odds": round(s.odds.mean(), 3),
            "mean_expected_ev": round(s.net_ev.mean(), 4), "realised_units": round(float(s.pnl.sum()), 2),
            "roi": round(float(s.pnl.mean()), 4), "roi_ci95": boot_roi(s.pnl.to_numpy(), rng),
            "max_drawdown_units": round(float((peak - cum).max()), 2), "longest_losing_streak": longest_fail(s)}


# ------------------------------------------------------------------------------------------------ football
def football_rows(d: Path, fse) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = pd.concat([pd.read_csv(d / "cycle_001_bookmaker_markets_full.csv"),
                   pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_bookmaker_markets.csv")], ignore_index=True)
    cols = ["match_id", "competition_code", "season", "match_date", "full_time_result"]
    m = pd.concat([pd.read_csv(d / "cycle_001_matches_full.csv")[cols],
                   pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_matches.csv")[cols]]).drop_duplicates("match_id")
    m["date"] = pd.to_datetime(m.match_date)
    fair = ["fair_home_probability", "fair_draw_probability", "fair_away_probability"]
    g = b.groupby(["match_id", "price_timing"])
    cons = g[fair].median()
    cons["n_books"] = g.size()
    cons = cons[cons.n_books >= 3].reset_index()
    rows = []
    for snap, cls in (("opening", "B_SAME_TIME_PROXY"), ("closing", "C_CLOSING_PROXY")):
        c = cons[cons.price_timing == snap].set_index("match_id")
        tot = c[fair].sum(1)
        for sel, fc in zip(("home", "draw", "away"), fair):
            p = c[fc] / tot                                     # normalised triplet (as Stage A / bsv2 use it)
            for book, comm in UK_BOOKS.items():
                q = b[(b.price_timing == snap) & (b.bookmaker == book)].set_index("match_id")[f"{sel}_odds"]
                j = pd.DataFrame({"p": p}).join(q.rename("odds"), how="inner").dropna()
                j = j[j.odds > 1.0]
                rows.append(j.assign(selection=sel, book=book, commission=comm, snapshot=snap, evidence_class=cls).reset_index())
    x = pd.concat(rows, ignore_index=True).merge(m, on="match_id")
    x["net_ev"] = ev(x.p, x.odds, x.commission)
    x["won"] = (x.full_time_result == x.selection.map(OUTC)).astype(int)
    x["pnl"] = np.where(x.won == 1, (x.odds - 1) * (1 - x.commission), -1.0)
    best = x.sort_values("net_ev", ascending=False).drop_duplicates(["match_id", "selection", "snapshot"])
    best = best.assign(sport="football", league=best.competition_code, market="1x2", engine="football_1x2.market_consensus (historical median-of-books)",
                       sigma=[fse("1x2", v) for v in best.p], is_exchange=best.book == "BF", event=best.match_id)
    # probability replay: closing consensus, favourite (max-P) selection per match
    pr = cons[cons.price_timing == "closing"].copy()
    trip = pr[fair].div(pr[fair].sum(1), axis=0).to_numpy()
    pr["p"], pr["sel"] = trip.max(1), np.array(["H", "D", "A"])[trip.argmax(1)]
    pr = pr.merge(m, on="match_id")
    pr["won"] = (pr.full_time_result == pr.sel).astype(int)
    return best, pr


def xgabora_prob(path: Path) -> dict:
    d = pd.read_csv(path, low_memory=False, usecols=["Division", "MatchDate", "FTResult", "OddHome", "OddDraw", "OddAway"])
    d["date"] = pd.to_datetime(d.MatchDate)
    d = d[d.Division.isin(XG_LEAGUES) & (d.date >= "2020-07-01") & d.OddHome.gt(1) & d.OddDraw.gt(1) & d.OddAway.gt(1)].copy()
    inv = 1 / d[["OddHome", "OddDraw", "OddAway"]].to_numpy()
    tri = inv / inv.sum(1, keepdims=True)
    d["p"], d["sel"] = tri.max(1), np.array(["H", "D", "A"])[tri.argmax(1)]
    d["won"] = (d.FTResult == d.sel).astype(int)
    d["season"] = np.where(d.date.dt.month >= 7, d.date.dt.year, d.date.dt.year - 1)
    return {lg: prob_replay(g) for lg, g in d.groupby("Division")}


# ------------------------------------------------------------------------------------------------ tennis
def tennis_rows(td_dir: Path, atp_canonical: Path, cal_se) -> tuple[pd.DataFrame, dict, dict]:
    spec = importlib.util.spec_from_file_location("v26d", REPO / "scripts/v2_6d_tennis_closing_diagnostic.py")
    v = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = v
    spec.loader.exec_module(v)
    atp = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv")
    atp = atp.merge(pd.read_csv(atp_canonical, usecols=["match_id", "player_a_name", "player_b_name"]), on="match_id", how="left")
    wta = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    rows, prob, link = [], {}, {}
    for tour, ours in (("ATP", atp), ("WTA", wta)):
        ours = ours.dropna(subset=["p_a_market_multiplicative", "outcome_a_won"]).copy()
        ours["date"] = pd.to_datetime(ours.scheduled_start.str[:10])
        pa = ours.p_a_market_multiplicative
        fav = pd.DataFrame({"p": np.maximum(pa, 1 - pa), "won": np.where(pa >= 0.5, ours.outcome_a_won, 1 - ours.outcome_a_won),
                            "date": ours.date, "season": ours.year})
        prob[tour] = prob_replay(fav[fav.p >= 0.5])
        named = ours.dropna(subset=["player_a_name", "player_b_name"])
        m, info = v.build(tour, v.load_td(td_dir, tour), named)
        link[tour] = info
        m = m[m.b365_valid]
        for pcol, cls, eng in (("pBFE", "C_CLOSING_PROXY", "BFE close de-vig (exchange-derived, as frozen engine)"),
                               ("pPS", "C_CLOSING_PROXY_REFERENCE", "Pinnacle close de-vig (reference estimator, NOT frozen)"),
                               ("pT30", "D_NOT_REPLAYABLE", "frozen engine T-30 LTP vs later B365 close (misaligned)")):
            for s in ("a", "b"):
                x = pd.DataFrame({"event": m.match_id, "date": m.date, "season": m.year, "p": m[f"{pcol}_{s}"],
                                  "odds": m[f"b365_{s}"], "won": m[f"won_{s}"]}).dropna()
                rows.append(x.assign(sport="tennis", league=tour, market="match_winner", book="B365", commission=0.0,
                                     evidence_class=cls, engine=eng, snapshot="closing", is_exchange=False,
                                     selection=s))
    x = pd.concat(rows, ignore_index=True)
    x = x[x.odds > 1.0]
    x["net_ev"] = ev(x.p, x.odds, 0.0)
    x["pnl"] = np.where(x.won == 1, x.odds - 1, -1.0)
    x["sigma"] = [cal_se(v) for v in x.p]
    return x, prob, link


# ------------------------------------------------------------------------------------------------ NBA
def nba_prob(d: Path) -> dict:
    fr = []
    for f in sorted(d.glob("nba_*_results_odds.csv")):
        x = pd.read_csv(f)
        x["season"] = f.stem.split("_")[1]
        fr.append(x)
    x = pd.concat(fr)
    x = x[(x["round"].astype(str) != "Pre-season") & (~x.is_allstar.astype(bool)) & (x.home_odds > 1) & (x.away_odds > 1)].copy()
    x["date"] = pd.to_datetime(x.date)
    ph = (1 / x.home_odds) / (1 / x.home_odds + 1 / x.away_odds)
    x["p"] = np.maximum(ph, 1 - ph)
    x["won"] = np.where(ph >= 0.5, x.home_win.astype(bool), ~x.home_win.astype(bool)).astype(int)
    x["margin"] = 1 / x.home_odds + 1 / x.away_odds - 1
    out = prob_replay(x)
    out["mean_overround"] = round(float(x.margin.mean()), 4)
    return out


# ------------------------------------------------------------------------------------------------ decision layer
def qualify(x: pd.DataFrame, gates: dict, z: float = 1.0) -> pd.DataFrame:
    x = x.copy()
    x["ev_minus_1sigma"] = ev((x.p - z * x.sigma).clip(lower=0), x.odds, x.commission)
    x["qualifies"] = (x.p >= gates["min_probability"]) & (x.net_ev >= gates["min_net_ev"]) & (x.odds >= gates["min_decimal_odds"])
    x["grade"] = np.where(x.qualifies, np.where(x.ev_minus_1sigma > 0, "A", "B"), "")
    x["fair_odds"] = 1 / x.p
    return x


def characteristics(q: pd.DataFrame, rng) -> dict:
    keys = {"league": q.league, "p_band": q.p.map(lambda v: band(v, P_BANDS)),
            "odds_band": q.odds.map(lambda v: band(v, ODDS_BANDS)), "ev_band": q.net_ev.map(lambda v: band(v, EV_BANDS)),
            "ev_minus_1sigma_positive": q.ev_minus_1sigma > 0, "season": q.season.astype(str), "book": q.book}
    return {k: {str(lab): fin(g, rng) for lab, g in q.groupby(s.values)} for k, s in keys.items()}


def grid(fav: pd.DataFrame, rng) -> list:
    out = []
    for o in GRID["odds"]:
        for e in GRID["ev"]:
            for p in GRID["p"]:
                for z in GRID["zsig"]:
                    evz = ev((fav.p - z * fav.sigma).clip(lower=0), fav.odds, fav.commission)
                    g = fav[(fav.odds >= o) & (fav.net_ev >= e) & (fav.p >= p) & ((evz > 0) if z > 0 else True)]
                    seasons = g.groupby("season").pnl.mean()
                    out.append({"min_odds": o, "min_ev": e, "min_p": p, "z_sigma": z, "n": int(len(g)),
                                "roi": round(float(g.pnl.mean()), 4) if len(g) else None,
                                "roi_ci95": boot_roi(g.pnl.to_numpy(), rng) if len(g) >= 10 else [None, None],
                                "seasons_positive": int((seasons > 0).sum()), "seasons_with_bets": int(len(seasons)),
                                "frozen_cell": (o, e, z) == (1.33, 0.02, 1.0)})
    return out


def counterfactual(fav: pd.DataFrame, gates: dict, rng) -> dict:
    ev_ok, odds_ok = fav.net_ev >= gates["min_net_ev"], fav.odds >= gates["min_decimal_odds"]
    return {"accepted_grade_A": fin(fav[fav.qualifies & (fav.grade == "A")], rng),
            "accepted_grade_B_uncertainty": fin(fav[fav.qualifies & (fav.grade == "B")], rng),
            "rejected_only_by_odds_floor": fin(fav[ev_ok & ~odds_ok], rng),
            "rejected_only_by_ev_floor_but_positive_ev": fin(fav[odds_ok & (fav.net_ev > 0) & ~ev_ok], rng),
            "no_value_ev_le_0": fin(fav[fav.net_ev <= 0], rng),
            "all_favourites_best_price": fin(fav, rng)}


# ------------------------------------------------------------------------------------------------ bankroll
def sim_cfg(min_bk: float = 0.10, min_ex: float = 1.00) -> dict:
    bs = load_bs()["bankroll_simulation"]
    return {**bs, "practical_min_stake_gbp": {"exchange": min_ex, "bookmaker": min_bk}}


POLICIES = {"flat_0.5pct": {"kind": "fraction", "fraction": 0.005}, "flat_1pct": {"kind": "fraction", "fraction": 0.01},
            "flat_2pct": {"kind": "fraction", "fraction": 0.02}, "kelly_1_8": {"kind": "kelly", "multiplier": 0.125, "cap_fraction": 0.02}}


def to_settled(q: pd.DataFrame) -> list[dict]:
    return [{"event_start": f"{r.date:%Y-%m-%d}T12:00:00", "selection_id": f"{r.event}|{r.selection}", "probability": r.p,
             "decimal_odds": r.odds, "commission": r.commission, "is_exchange": str(bool(r.is_exchange)),
             "status": "WON" if r.won else "LOST"} for r in q.sort_values("date").itertuples()]


def bankroll(q: pd.DataFrame, rng) -> dict:
    cfg = sim_cfg()
    settled = to_settled(q)
    res = {}
    for start in (30, 50, 100):
        for name, pol in POLICIES.items():
            s = simulate(settled, float(start), name, pol, cfg)
            res[f"{start}_{name}"] = {"final": s.final, "return_pct": round(100 * (s.final / start - 1), 2), "bets": s.bets,
                                      "turnover": s.turnover, "max_drawdown_pct": round(100 * s.max_drawdown_pct, 2),
                                      "longest_losing_streak": s.longest_losing_streak, "skipped": s.skipped,
                                      "drawdown_stop_fired": s.drawdown_stop_fired}
    # stress: flat GBP stakes with no caps (NOT a policy)
    stress = {}
    for start in (30, 50):
        for flat in (3.0, 5.0):
            bank, peak, dd, ruined = start, start, 0.0, False
            for r in q.sort_values("date").itertuples():
                if bank < flat:
                    ruined = True
                    break
                bank += flat * (r.odds - 1) * (1 - r.commission) if r.won else -flat
                peak, dd = max(peak, bank), max(dd, (peak - bank) / peak)
            stress[f"{start}_flat_{flat:g}"] = {"stake_pct_of_start": round(100 * flat / start, 1), "final": round(bank, 2),
                                               "max_drawdown_pct": round(100 * dd, 1), "ruined": ruined}
    # Monte Carlo (outcomes ~ Bernoulli(P), i.e. 'if the probabilities are calibrated') and bootstrap of realised P&L,
    # fraction policies with min-stake rounding and the 5% cap; ruin = bankroll below the minimum stake.
    mc = {}
    o = q.sort_values("date")
    p, odds, comm = o.p.to_numpy(), o.odds.to_numpy(), o.commission.to_numpy()
    minst = np.where(o.is_exchange.to_numpy(bool), 1.0, 0.10)
    n = len(o)
    for start in (30, 50, 100):
        for f in (0.005, 0.01, 0.02):
            for mode in ("model_P", "bootstrap_realised"):
                if n == 0:
                    continue
                if mode == "model_P":
                    won = rng.random((N_MC, n)) < p
                    idx = np.broadcast_to(np.arange(n), (N_MC, n))
                else:
                    idx = rng.integers(0, n, size=(N_MC, n))
                    won = o.won.to_numpy(bool)[idx]
                bank = np.full(N_MC, float(start))
                peak = bank.copy()
                mdd = np.zeros(N_MC)
                ruin = np.zeros(N_MC, bool)
                for t in range(n):
                    i = idx[:, t]
                    st = np.minimum(np.maximum(bank * f, minst[i]), bank * 0.05)
                    ok = (bank * 0.05 >= minst[i]) & ~ruin
                    ruin |= bank < minst[i]
                    pnl = np.where(won[:, t], st * (odds[i] - 1) * (1 - comm[i]), -st)
                    bank = bank + np.where(ok, pnl, 0.0)
                    peak = np.maximum(peak, bank)
                    mdd = np.maximum(mdd, (peak - bank) / peak)
                mc[f"{start}_{f * 100:g}pct_{mode}"] = {
                    "median_final": round(float(np.median(bank)), 2), "p05_final": round(float(np.percentile(bank, 5)), 2),
                    "p95_final": round(float(np.percentile(bank, 95)), 2), "prob_loss": round(float((bank < start).mean()), 3),
                    "prob_drawdown_ge_20pct": round(float((mdd >= 0.20).mean()), 4), "prob_ruin": round(float(ruin.mean()), 4)}
    return {"chronological": res, "stress_flat_stakes_NOT_A_POLICY": stress, "resampling": mc, "n_bets": n}


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("football-dir", "tennis-dir", "atp-canonical", "nba-dir", "xgabora"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    gates = load_bs()["decision_gates"]["paper_bet"]
    cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    fse, cal = SA.football_sigma(cfg.football_sigma_evidence), SA.calibration_se(cfg.calibration_results)

    fb, fb_prob = football_rows(a.football_dir, fse)
    tn, tn_prob, tn_link = tennis_rows(a.tennis_dir, a.atp_canonical, cal)
    res: dict = {"label": "HISTORICAL DECISION REPLAY -- research only; no production change; class D never used financially",
                 "preregistration": "research/platform_v2/decision_replay/PREREGISTRATION.md",
                 "frozen_rules": {"bsv2": load_bs()["rule_version"], **gates, "grade_A": "EV(P - 1*sigma) > 0"},
                 "not_evaluable_gates": ["max_hours_to_event (no timestamps)", "max_price_age_minutes", "exchange spread width"]}
    res["probability_replay"] = {"football_E0_E1_SC0_closing_consensus": {lg: prob_replay(g) for lg, g in fb_prob.groupby("competition_code")},
                                 "football_E0_E1_SC0_all": prob_replay(fb_prob),
                                 "football_other_leagues_bet365_close": xgabora_prob(a.xgabora),
                                 "tennis_frozen_engine": tn_prob, "nba_average_close": nba_prob(a.nba_dir)}
    res["tennis_linkage"] = tn_link

    all_rows = pd.concat([fb, tn], ignore_index=True)
    all_rows["season"] = all_rows.season.astype(str)
    all_rows = qualify(all_rows, gates)
    replayable = all_rows[~all_rows.evidence_class.str.startswith("D")]
    fav = replayable[replayable.p >= gates["min_probability"]]
    cols = ["sport", "league", "date", "event", "market", "selection", "engine", "p", "sigma", "fair_odds", "odds", "book",
            "snapshot", "evidence_class", "net_ev", "ev_minus_1sigma", "qualifies", "grade", "won", "pnl"]
    OUT.mkdir(parents=True, exist_ok=True)
    fav[cols].sort_values(["evidence_class", "date"]).to_csv(OUT / "reconstructed_candidates.csv", index=False)
    fav[fav.qualifies][cols].sort_values(["evidence_class", "date"]).to_csv(OUT / "reconstructed_qualifiers.csv", index=False)
    res["class_D_rows_excluded_from_finance"] = int((all_rows.evidence_class.str.startswith("D") & (all_rows.p >= 0.5)).sum())

    dec = {}
    for cls, g in fav.groupby("evidence_class"):
        q = g[g.qualifies]
        dec[cls] = {"favourites_considered": int(len(g)), "events": int(g.event.nunique()),
                    "qualifiers": int(len(q)), "qualifiers_per_100_events": round(100 * len(q) / max(1, g.event.nunique()), 3),
                    "grade_counts": {k: int(v) for k, v in q.grade.value_counts().items()},
                    "qualifiers_summary": fin(q, rng), "characteristics": characteristics(q, rng),
                    "all_favourites_characteristics": characteristics(g, rng),
                    "counterfactual": counterfactual(g, gates, rng), "bankroll": bankroll(q, rng)}
        pd.DataFrame(grid(g, rng)).to_csv(OUT / f"threshold_grid_{cls}.csv", index=False)
    res["decision_replay"] = dec
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("favourites_considered", "qualifiers", "grade_counts", "qualifiers_summary")}
                      for k, v in dec.items()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
