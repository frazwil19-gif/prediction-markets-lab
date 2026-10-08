"""Edge Source Discovery Cycle 1 (pre-registered plan: research/platform_v2/edge_discovery_c1/PREREGISTRATION.md).
DISCOVERY research only: descriptive behaviour + residual-information tests. Never touches production or ledgers.

Usage: python scripts/edge_discovery_c1.py --football-dir <processed/football> --tennis-dir <tennis_data_co_uk>
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
from sklearn.linear_model import LogisticRegression

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/edge_discovery_c1"
SEED, N_BOOT = 20261003, 2000
RNG = np.random.default_rng(SEED)
EVB = [(-9, -.10, "<-10%"), (-.10, -.05, "-10..-5%"), (-.05, 0, "-5..0%"), (0, .01, "0-1%"), (.01, .02, "1-2%"),
       (.02, .04, "2-4%"), (.04, .06, "4-6%"), (.06, .10, "6-10%"), (.10, 99, "10%+")]
PB = [(0, .1, "<10"), (.1, .2, "10-20"), (.2, .3, "20-30"), (.3, .4, "30-40"), (.4, .5, "40-50"), (.5, .6, "50-60"),
      (.6, .7, "60-70"), (.7, .8, "70-80"), (.8, .9, "80-90"), (.9, 1.01, "90+")]
UK = {"B365": 0.0, "WH": 0.0, "BW": 0.0, "BF": 0.05, "1XB": 0.0}
ATLAS: list[dict] = []


def band(x, bands):
    for lo, hi, lab in bands:
        if lo <= x < hi:
            return lab
    return "?"


def boot_mean(v: np.ndarray) -> tuple[list, float]:
    """95% CI and two-sided bootstrap p-value for mean != 0."""
    v = np.asarray(v, float)
    if len(v) < 10:
        return [None, None], 1.0
    m = v[RNG.integers(0, len(v), size=(N_BOOT, len(v)))].mean(1)
    p = 2 * min((m <= 0).mean(), (m >= 0).mean())
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)], float(max(p, 1 / N_BOOT))


def summ(g: pd.DataFrame) -> dict:
    """g: p, won, (odds, ret, ev optional)."""
    if g.empty:
        return {"n": 0}
    out = {"n": int(len(g)), "mean_p": round(float(g.p.mean()), 4), "win": round(float(g.won.mean()), 4),
           "bias_pp": round(100 * float(g.won.mean() - g.p.mean()), 2)}
    if "ret" in g:
        ci, pv = boot_mean(g.ret.to_numpy())
        out.update(avg_odds=round(float(g.odds.mean()), 3), mean_ev=round(float(g.ev.mean()), 4), roi=round(float(g.ret.mean()), 4),
                   roi_ci=ci, p_value=round(pv, 4))
    return out


def atlas(bid, desc, sport, league, market, dataset, disc: dict, conf: dict, mech, effect_kind, evidence, leak, mining, p_value=None):
    stable = None
    key = "roi" if effect_kind == "return" else "bias_pp"
    if disc.get("n") and conf.get("n") and disc.get(key) is not None and conf.get(key) is not None:
        stable = bool(np.sign(disc[key]) == np.sign(conf[key]))
    ATLAS.append({"behaviour_id": bid, "description": desc, "sport": sport, "league": league, "market": market, "dataset": dataset,
                  "n_discovery": disc.get("n"), "n_confirmation": conf.get("n"), "effect_kind": effect_kind,
                  "discovery_effect": disc.get(key), "confirmation_effect": conf.get(key),
                  "confirmation_ci": conf.get("roi_ci") if effect_kind == "return" else None,
                  "temporal_sign_stable": stable, "mechanism": mech, "evidence_class": evidence, "leakage_risk": leak,
                  "data_mining_risk": mining, "p_value_full": p_value})


# ------------------------------------------------------------------------------------------------ football per-book
def football(d: Path) -> dict:
    b = pd.concat([pd.read_csv(d / "cycle_001_bookmaker_markets_full.csv"),
                   pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_bookmaker_markets.csv")], ignore_index=True)
    m = pd.concat([pd.read_csv(d / f, usecols=["match_id", "competition_code", "season", "match_date", "full_time_result"])
                   for f in ("cycle_001_matches_full.csv", "h_fb2_002_sealed_oos_2025_26_matches.csv")]).drop_duplicates("match_id")
    m["period"] = np.where(m.season.isin(["2020_21", "2021_22", "2022_23"]), "discovery", "confirmation")
    b = b.assign(margin=1 / b.home_odds + 1 / b.draw_odds + 1 / b.away_odds - 1)
    rows = []
    for sel, oc, fc in (("H", "home_odds", "fair_home_probability"), ("D", "draw_odds", "fair_draw_probability"), ("A", "away_odds", "fair_away_probability")):
        rows.append(b[["match_id", "bookmaker", "price_timing", oc, fc, "margin"]]
                    .rename(columns={oc: "odds", fc: "fair_book"}).assign(sel=sel))
    x = pd.concat(rows, ignore_index=True)
    x = x.merge(m, on="match_id")
    x["won"] = (x.full_time_result == x.sel).astype(int)
    res: dict = {}
    # F1 margins
    res["F1_margin_by_book_snapshot"] = x.drop_duplicates(["match_id", "bookmaker", "price_timing"]).groupby(["bookmaker", "price_timing"]).margin.mean().round(4).unstack().to_dict()
    # references per (match, timing, sel)
    ps = x[x.bookmaker == "PS"][["match_id", "price_timing", "sel", "fair_book", "odds"]].rename(columns={"fair_book": "p_ps", "odds": "odds_ps"})
    cons = x.groupby(["match_id", "price_timing", "sel"]).fair_book.median().rename("p_cons").reset_index()
    nb = x.groupby(["match_id", "price_timing"]).bookmaker.nunique().rename("n_books").reset_index()
    ref = ps.merge(cons, on=["match_id", "price_timing", "sel"]).merge(nb, on=["match_id", "price_timing"])
    uk = x[x.bookmaker.isin(UK)].merge(ref, on=["match_id", "price_timing", "sel"])
    uk = uk[(uk.n_books >= 3) & (uk.odds > 1)]
    uk["comm"] = uk.bookmaker.map(UK)
    uk["ev_ps"] = uk.p_ps * (uk.odds - 1) * (1 - uk.comm) - (1 - uk.p_ps)
    uk["ret"] = np.where(uk.won == 1, (uk.odds - 1) * (1 - uk.comm), -1.0)
    # F2 dispersion of UK prices per outcome
    disp = uk.groupby(["match_id", "price_timing", "sel"]).odds.agg(["max", "median", "min", "count"])
    disp = disp[disp["count"] >= 3]
    res["F2_dispersion"] = {t: {"best_over_median_pct": round(float(100 * (g["max"] / g["median"] - 1).mean()), 2),
                                "best_over_worst_pct": round(float(100 * (g["max"] / g["min"] - 1).mean()), 2)}
                            for t, g in disp.groupby(level=1)}
    # F4 calibration of references by outcome type, P band, snapshot, period
    r = ref.merge(m, on="match_id")
    r["won"] = (r.full_time_result == r.sel).astype(int)
    cal = {}
    for refcol in ("p_ps", "p_cons"):
        for (t, sel, per), g in r.groupby(["price_timing", "sel", "period"]):
            g = g.assign(p=g[refcol])
            cal[f"{refcol}|{t}|{sel}|{per}"] = {bb: summ(gg) for bb, gg in g.groupby(g.p.map(lambda v: band(v, PB)))}
    res["F4_calibration"] = cal
    # F7 sides: ROI at best UK price (opening, class B) by sel and P band (PS-fair as P)
    op = uk[uk.price_timing == "opening"]
    best = op.sort_values("odds", ascending=False).drop_duplicates(["match_id", "sel"])
    best = best.assign(p=best.p_ps, ev=best.ev_ps)
    res["F7_best_uk_by_side_pband"] = {f"{s}|{bb}|{per}": summ(gg) for (s, bb, per), gg in
                                       best.groupby([best.sel, best.p.map(lambda v: band(v, PB)), best.period])}
    # PS itself (the sharp book) by side & band: does a 'bet at Pinnacle' return what margin predicts?
    psb = x[(x.bookmaker == "PS") & (x.price_timing == "opening")].merge(ref[["match_id", "price_timing", "sel", "p_ps"]], on=["match_id", "price_timing", "sel"])
    psb = psb.assign(p=psb.p_ps, ev=psb.p_ps * (psb.odds - 1) - (1 - psb.p_ps), ret=np.where(psb.won == 1, psb.odds - 1, -1.0))
    res["F7_pinnacle_by_side_pband"] = {f"{s}|{bb}": summ(gg) for (s, bb), gg in psb.groupby([psb.sel, psb.p.map(lambda v: band(v, PB))])}
    # F5 EV continuum: every UK book quote (opening, class B), EV vs PS-fair
    op = op.assign(p=op.p_ps, ev=op.ev_ps)
    res["F5_ev_continuum_opening_all_quotes"] = {f"{bb}|{per}": summ(gg) for (bb, per), gg in op.groupby([op.ev.map(lambda v: band(v, EVB)), op.period])}
    res["F5_ev_continuum_by_book"] = {f"{bk}|{bb}": summ(gg) for (bk, bb), gg in op.groupby([op.bookmaker, op.ev.map(lambda v: band(v, EVB))]) if bb in ("0-1%", "1-2%", "2-4%", "4-6%", "6-10%", "10%+")}
    fit = np.polyfit(op.ev.clip(-0.3, 0.3), op.ret, 1)
    res["F5_linear_return_on_ev"] = {"slope": round(float(fit[0]), 3), "intercept": round(float(fit[1]), 4), "note": "slope 1 = EV fully realised"}
    # best UK quote per (match, sel) at EV>0 vs PS — the 'sharp-vs-soft' mechanism
    pos = best[best.ev_ps > 0]
    for per in ("discovery", "confirmation"):
        res[f"F5_best_uk_ev_gt0_vs_ps_{per}"] = summ(pos[pos.period == per])
    # F6 timing: PS-fair movement opening->closing; does opening soft price beat closing PS fair (CLV) and what does that return?
    pc = ref[ref.price_timing == "closing"][["match_id", "sel", "p_ps"]].rename(columns={"p_ps": "p_ps_close"})
    clv = best.merge(pc, on=["match_id", "sel"])
    clv["clv"] = clv.odds * clv.p_ps_close - 1                 # opening price vs closing PS fair
    clv["ps_move"] = clv.p_ps_close - clv.p_ps
    res["F6_ps_fair_move_open_to_close_abs_mean_pp"] = round(100 * float(clv.ps_move.abs().mean()), 2)
    res["F6_clv_distribution"] = {k: round(float(v), 4) for k, v in clv.clv.describe(percentiles=[.1, .5, .9]).items()}
    res["F6_return_by_clv_band"] = {bb: summ(gg.assign(p=gg.p_ps, ev=gg.ev_ps)) for bb, gg in clv.groupby(clv.clv.map(lambda v: band(v, EVB)))}
    res["F6_opening_ev_gt0_then_clv_positive_share"] = round(float((clv[clv.ev_ps > 0].clv > 0).mean()), 4) if (clv.ev_ps > 0).any() else None
    # F8 disagreement: book vs consensus (dispersion) and PS vs consensus
    opx = op.assign(book_vs_cons=1 / op.odds / (1 + op.margin) - op.p_cons, ps_vs_cons=op.p_ps - op.p_cons)
    res["F8_ps_minus_consensus_bins"] = {bb: summ(gg.assign(p=gg.p_cons)) for bb, gg in opx.drop_duplicates(["match_id", "sel"]).groupby(
        pd.cut(opx.drop_duplicates(["match_id", "sel"]).ps_vs_cons, [-1, -.03, -.01, .01, .03, 1]), observed=True)}
    res["F8_ps_minus_consensus_bins"] = {str(k): v for k, v in res["F8_ps_minus_consensus_bins"].items()}
    # Atlas entries (football)
    for side in ("H", "D", "A"):
        for lo, hi, lab in ((0, .35, "P<0.35"), (.35, .5, "0.35-0.5"), (.5, .7, "0.5-0.7"), (.7, 1.01, "P>=0.7")):
            g = best[(best.sel == side) & (best.p >= lo) & (best.p < hi)]
            if len(g) < 50:
                continue
            ci, pv = boot_mean(g.ret.to_numpy())
            atlas(f"FB-SIDE-{side}-{lab}", f"Best UK pre-close price, side {side}, PS-fair {lab}", "football", "E0/E1/SC0", "1x2",
                  "football-data per-book", summ(g[g.period == "discovery"]), summ(g[g.period == "confirmation"]),
                  "margin vs favourite-longshot structure", "return", "B", "low (same snapshot)", "medium (12 cells)", pv)
            atlas(f"FB-CAL-{side}-{lab}", f"PS-fair calibration, side {side}, {lab}", "football", "E0/E1/SC0", "1x2", "football-data per-book",
                  summ(g[g.period == "discovery"].assign(p=g.p)), summ(g[g.period == "confirmation"]), "favourite-longshot bias",
                  "calibration", "D(prob)", "low", "medium", None)
    ci, pv = boot_mean(pos.ret.to_numpy())
    atlas("FB-SOFT-ABOVE-SHARP", "Best UK book above Pinnacle-fair (EV>0), pre-close, all sides", "football", "E0/E1/SC0", "1x2",
          "football-data per-book", summ(pos[pos.period == "discovery"]), summ(pos[pos.period == "confirmation"]),
          "soft book slower/different than sharp book (price dispersion)", "return", "B", "low", "low (one pre-stated rule)", pv)
    res["n_quotes_uk"] = int(len(uk))
    return res


# ------------------------------------------------------------------------------------------------ xgabora (16 leagues)
def xgabora(path: Path) -> dict:
    lg = ["E0", "E1", "SC0", "N1", "D1", "F1", "SP1", "I1", "P1", "B1", "E2", "E3", "SP2", "D2", "I2", "F2"]
    d = pd.read_csv(path, low_memory=False, usecols=["Division", "MatchDate", "FTResult", "OddHome", "OddDraw", "OddAway",
                                                      "HomeElo", "AwayElo", "Form5Home", "Form5Away"])
    d["date"] = pd.to_datetime(d.MatchDate)
    d = d[d.Division.isin(lg) & (d.date >= "2020-07-01") & (d.date < "2026-07-01") & (d.OddHome > 1) & (d.OddDraw > 1) & (d.OddAway > 1)].copy()
    d["season"] = np.where(d.date.dt.month >= 7, d.date.dt.year, d.date.dt.year - 1)
    d["period"] = np.where(d.season <= 2022, "discovery", "confirmation")
    inv = 1 / d[["OddHome", "OddDraw", "OddAway"]].to_numpy()
    tri = inv / inv.sum(1, keepdims=True)
    long = []
    for i, s in enumerate("HDA"):
        long.append(pd.DataFrame({"lg": d.Division.values, "season": d.season.values, "period": d.period.values, "sel": s,
                                  "p": tri[:, i], "won": (d.FTResult == s).astype(int).values}))
    L = pd.concat(long)
    res = {"X1_calibration_side_band_period": {f"{s}|{bb}|{per}": summ(g) for (s, bb, per), g in
                                               L.groupby([L.sel, L.p.map(lambda v: band(v, PB)), L.period])}}
    # favourite-longshot slope per league: logistic slope of won ~ logit(p), per period
    slopes = {}
    for (l, per), g in L.groupby(["lg", "period"]):
        x = np.log(g.p.clip(1e-4, 1 - 1e-4) / (1 - g.p.clip(1e-4, 1 - 1e-4))).to_numpy().reshape(-1, 1)
        mdl = LogisticRegression(C=1e6, max_iter=1000).fit(x, g.won)
        slopes[f"{l}|{per}"] = round(float(mdl.coef_[0][0]), 3)
    res["X1_logit_slope_by_league_period"] = slopes
    for lab, (lo, hi) in {"heavy-fav P>=0.70": (.7, 1.01), "longshot P<0.20": (0, .2), "draw": (None, None)}.items():
        g = L[L.sel == "D"] if lab == "draw" else L[(L.p >= lo) & (L.p < hi)]
        atlas(f"XG-CAL-{lab}", f"B365-close de-vig calibration, {lab}, 16 leagues", "football", "16 leagues", "1x2", "xgabora",
              summ(g[g.period == "discovery"]), summ(g[g.period == "confirmation"]), "favourite-longshot bias", "calibration",
              "D(prob)", "low", "low (3 pre-stated cells)")
    # X2 residual information: per outcome-home binary, logit(pH) + feature, fit discovery, eval confirmation
    d = d.dropna(subset=["HomeElo", "AwayElo", "Form5Home", "Form5Away"]).copy()
    inv = 1 / d[["OddHome", "OddDraw", "OddAway"]].to_numpy()
    tri = inv / inv.sum(1, keepdims=True)
    d["lpH"] = np.log(tri[:, 0] / (1 - tri[:, 0]))
    d["lpA"] = np.log(tri[:, 2] / (1 - tri[:, 2]))
    d["elo"] = (d.HomeElo - d.AwayElo) / 100
    d["form"] = (d.Form5Home - d.Form5Away) / 15
    resid = {}
    for target, base in (("H", "lpH"), ("A", "lpA")):
        y = (d.FTResult == target).astype(int).to_numpy()
        tr, te = (d.period == "discovery").to_numpy(), (d.period == "confirmation").to_numpy()
        out = {}
        b0 = LogisticRegression(C=1e6, max_iter=1000).fit(d[[base]][tr], y[tr])
        p0 = b0.predict_proba(d[[base]][te])[:, 1]
        for feat in ("elo", "form", "elo+form"):
            cols = [base] + feat.split("+")
            mdl = LogisticRegression(C=1e6, max_iter=1000).fit(d[cols][tr], y[tr])
            p1 = mdl.predict_proba(d[cols][te])[:, 1]
            ll0 = -(y[te] * np.log(p0) + (1 - y[te]) * np.log(1 - p0))
            ll1 = -(y[te] * np.log(p1) + (1 - y[te]) * np.log(1 - p1))
            ci, pv = boot_mean(ll1 - ll0)
            out[feat] = {"n_test": int(te.sum()), "delta_ll": round(float((ll1 - ll0).mean()), 5), "ci": ci, "p": round(pv, 4),
                         "coefs": [round(float(c), 4) for c in mdl.coef_[0]]}
            atlas(f"XG-RESID-{target}-{feat}", f"Residual info of {feat} beyond B365 market, {target} win, 16 leagues", "football",
                  "16 leagues", "1x2", "xgabora", {"n": int(tr.sum())}, {"n": int(te.sum())}, "public information already priced?",
                  "residual", "D(prob)", "low (ClubElo as-of; Form5 pre-match)", "low", pv)
            ATLAS[-1]["confirmation_effect"] = out[feat]["delta_ll"]
            ATLAS[-1]["confirmation_ci"] = ci
        resid[target] = out
    res["X2_residual_information"] = resid
    return res


# ------------------------------------------------------------------------------------------------ tennis
def tennis(td_dir: Path, atp_canonical: Path) -> dict:
    res = {}
    fr = []
    for tour, f in (("ATP", "v2_tennis_market_dataset.csv"), ("WTA", "v2_wta_market_dataset.csv")):
        x = pd.read_csv(REPO / "data/interim" / f).dropna(subset=["p_a_market_multiplicative", "outcome_a_won"])
        x["tour"] = tour
        fr.append(x)
    t = pd.concat(fr, ignore_index=True)
    t["period"] = np.where(t.year <= 2023, "discovery", "confirmation")
    pa = t.p_a_market_multiplicative
    t["p_fav"] = np.maximum(pa, 1 - pa)
    t["fav_won"] = np.where(pa >= .5, t.outcome_a_won, 1 - t.outcome_a_won)
    T1 = {}
    for key in ("surface", "best_of", "tourney_level", "tour"):
        for (k, per), g in t.groupby([key, "period"]):
            T1[f"{key}={k}|{per}"] = summ(pd.DataFrame({"p": g.p_fav, "won": g.fav_won}))
    res["T1_frozen_engine_calibration_strata"] = T1
    # T3 residual info: ranking and elo probabilities beyond frozen market P (side a)
    t = t.dropna(subset=["p_a_ranking", "p_a_elo_global"]).copy()
    lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    t["lm"], t["lr"], t["le"] = lg(t.p_a_market_multiplicative), lg(t.p_a_ranking), lg(t.p_a_elo_global)
    t["bo5"] = (t.best_of == 5).astype(int)
    y = t.outcome_a_won.astype(int).to_numpy()
    tr, te = (t.period == "discovery").to_numpy(), (t.period == "confirmation").to_numpy()
    b0 = LogisticRegression(C=1e6, max_iter=1000).fit(t[["lm"]][tr], y[tr])
    p0 = b0.predict_proba(t[["lm"]][te])[:, 1]
    resid = {}
    for feat in ("lr", "le", "lr+le", "lr+le+bo5"):
        cols = ["lm"] + feat.split("+")
        mdl = LogisticRegression(C=1e6, max_iter=1000).fit(t[cols][tr], y[tr])
        p1 = mdl.predict_proba(t[cols][te])[:, 1]
        dl = -(y[te] * np.log(p1) + (1 - y[te]) * np.log(1 - p1)) + (y[te] * np.log(p0) + (1 - y[te]) * np.log(1 - p0))
        ci, pv = boot_mean(dl)
        resid[feat] = {"n_test": int(te.sum()), "delta_ll": round(float(dl.mean()), 5), "ci": ci, "p": round(pv, 4),
                       "coefs": [round(float(c), 4) for c in mdl.coef_[0]]}
        atlas(f"TN-RESID-{feat}", f"Residual info of {feat} beyond frozen Betfair P", "tennis", "ATP+WTA", "match_winner",
              "Betfair BASIC + rankings/Elo", {"n": int(tr.sum())}, {"n": int(te.sum())}, "public information already priced?",
              "residual", "D(prob)", "low (pre-match)", "low", pv)
        ATLAS[-1]["confirmation_effect"] = resid[feat]["delta_ll"]
        ATLAS[-1]["confirmation_ci"] = ci
    res["T3_residual_information"] = resid
    # T2 tennis-data close: PS-fair vs B365, both sides, all P (class C reference)
    v = importlib.util.spec_from_file_location("v26d_ed", REPO / "scripts/v2_6d_tennis_closing_diagnostic.py")
    mod = importlib.util.module_from_spec(v)
    sys.modules[v.name] = mod
    v.loader.exec_module(mod)
    atp = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv").merge(
        pd.read_csv(atp_canonical, usecols=["match_id", "player_a_name", "player_b_name"]), on="match_id", how="left")
    wta = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    rows = []
    for tour, ours in (("ATP", atp), ("WTA", wta)):
        ours = ours.dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "player_a_name", "player_b_name"]).copy()
        ours["date"] = pd.to_datetime(ours.scheduled_start.str[:10])
        m, _ = mod.build(tour, mod.load_td(td_dir, tour), ours)
        m = m[m.b365_valid & m.pPS_a.notna()]
        for s in ("a", "b"):
            rows.append(pd.DataFrame({"tour": tour, "year": m.year, "p": m[f"pPS_{s}"], "odds": m[f"b365_{s}"], "won": m[f"won_{s}"],
                                      "b365_margin": 1 / m.b365_a + 1 / m.b365_b - 1}))
    c = pd.concat(rows)
    c["ev"] = c.p * (c.odds - 1) - (1 - c.p)
    c["ret"] = np.where(c.won == 1, c.odds - 1, -1.0)
    c["period"] = np.where(c.year <= 2023, "discovery", "confirmation")
    res["T2_ev_continuum_both_sides"] = {f"{bb}|{per}": summ(g) for (bb, per), g in c.groupby([c.ev.map(lambda x: band(x, EVB)), c.period])}
    res["T2_by_pband_both_sides"] = {f"{bb}|{per}": summ(g) for (bb, per), g in c.groupby([c.p.map(lambda x: band(x, PB)), c.period])}
    res["T2_b365_margin_mean"] = round(float(c.b365_margin.mean()), 4)
    fit = np.polyfit(c.ev.clip(-.3, .3), c.ret, 1)
    res["T2_linear_return_on_ev"] = {"slope": round(float(fit[0]), 3), "intercept": round(float(fit[1]), 4)}
    pos = c[c.ev > 0]
    ci, pv = boot_mean(pos.ret.to_numpy())
    atlas("TN-SOFT-ABOVE-SHARP", "B365 close above Pinnacle-fair (EV>0), both sides", "tennis", "ATP+WTA", "match_winner",
          "tennis-data close", summ(pos[pos.period == "discovery"]), summ(pos[pos.period == "confirmation"]),
          "soft book vs sharp book dispersion", "return", "C", "low (aligned closes)", "low (one pre-stated rule)", pv)
    for lab, (lo, hi) in {"underdog P<0.35": (0, .35), "P 0.35-0.5": (.35, .5), "fav P>=0.8": (.8, 1.01)}.items():
        g = c[(c.p >= lo) & (c.p < hi)]
        ci, pv = boot_mean(g.ret.to_numpy())
        atlas(f"TN-SIDE-{lab}", f"B365 close, {lab}, PS-fair P", "tennis", "ATP+WTA", "match_winner", "tennis-data close",
              summ(g[g.period == "discovery"]), summ(g[g.period == "confirmation"]), "margin distribution / favourite-longshot",
              "return", "C", "low", "low", pv)
    return res


# ------------------------------------------------------------------------------------------------ NBA
def nba(dd: Path) -> dict:
    fr = []
    for f in sorted(dd.glob("nba_*_results_odds.csv")):
        x = pd.read_csv(f)
        x["season"] = f.stem.split("_")[1]
        fr.append(x)
    x = pd.concat(fr)
    x = x[(x["round"].astype(str) != "Pre-season") & (~x.is_allstar.astype(bool)) & (x.home_odds > 1) & (x.away_odds > 1)]
    ph = (1 / x.home_odds) / (1 / x.home_odds + 1 / x.away_odds)
    per = np.where(x.season.str[:4].astype(int) <= 2021, "discovery", "confirmation")
    L = pd.concat([pd.DataFrame({"side": "home", "p": ph, "won": x.home_win.astype(int), "period": per}),
                   pd.DataFrame({"side": "away", "p": 1 - ph, "won": 1 - x.home_win.astype(int), "period": per})])
    res = {"N1_calibration_side_band_period": {f"{s}|{bb}|{p}": summ(g) for (s, bb, p), g in
                                               L.groupby([L.side, L.p.map(lambda v: band(v, PB)), L.period])}}
    for side in ("home", "away"):
        g = L[L.side == side]
        atlas(f"NBA-CAL-{side}", f"NBA average-close de-vig calibration, {side}", "NBA", "NBA", "moneyline", "wippa",
              summ(g[g.period == "discovery"]), summ(g[g.period == "confirmation"]), "home-court pricing", "calibration",
              "D(prob)", "low", "low")
    return res


# ------------------------------------------------------------------------------------------------ prospective tennis snapshots
def prospective() -> dict:
    s = pd.read_csv(REPO / "tennis_predictions/price_snapshots.csv")
    s = s[(s.odds_a > 1) & (s.odds_b > 1)].copy()
    s["scan"] = pd.to_datetime(s.scan_timestamp_utc, format="ISO8601")
    s["upd"] = pd.to_datetime(s.last_update, format="ISO8601", utc=True)
    s["stale_min"] = (s.scan - s.upd).dt.total_seconds() / 60
    s["margin"] = 1 / s.odds_a + 1 / s.odds_b - 1
    ex = s[s.bookmaker == "betfair_ex_uk"][["scan_timestamp_utc", "event_id", "odds_a", "odds_b"]].rename(columns={"odds_a": "ex_a", "odds_b": "ex_b"})
    j = s.merge(ex, on=["scan_timestamp_utc", "event_id"])
    j["p_ex_a"] = (1 / j.ex_a) / (1 / j.ex_a + 1 / j.ex_b)          # exchange back-price de-vig (no lay here)
    rows = []
    for side, o, p in (("a", "odds_a", "p_ex_a"), ("b", "odds_b", None)):
        pp = j.p_ex_a if side == "a" else 1 - j.p_ex_a
        rows.append(pd.DataFrame({"book": j.bookmaker, "p": pp, "odds": j[o], "stale_min": j.stale_min, "scan": j.scan_timestamp_utc, "event": j.event_id}))
    q = pd.concat(rows)
    q = q[q.book != "betfair_ex_uk"]
    q["ev"] = q.p * (q.odds - 1) - (1 - q.p)
    res = {"n_quotes": int(len(s)), "books": int(s.bookmaker.nunique()), "scans": int(s.scan_timestamp_utc.nunique()),
           "events": int(s.event_id.nunique()),
           "P1_margin_by_book": s.groupby("bookmaker").margin.mean().round(4).sort_values().to_dict(),
           "P1_ev_gt0_share_by_book_vs_exchange_devig": q.groupby("book").ev.apply(lambda v: round(float((v > 0).mean()), 4)).sort_values(ascending=False).to_dict(),
           "P2_stale_minutes_by_ev_band": {bb: {"n": int(len(g)), "median_stale_min": round(float(g.stale_min.median()), 1)}
                                           for bb, g in q.groupby(q.ev.map(lambda v: band(v, EVB)))},
           "P1_best_price_book_frequency": q.loc[q.groupby(["scan", "event", q.p.round(6)]).odds.idxmax()].book.value_counts().head(10).to_dict()
           if False else None}
    best = q.sort_values("odds", ascending=False).drop_duplicates(["scan", "event", "p"])
    res["P1_best_price_book_frequency"] = best.book.value_counts().head(12).to_dict()
    res["P1_best_quote_ev_distribution"] = {k: round(float(v), 4) for k, v in best.ev.describe(percentiles=[.1, .5, .9]).items()}
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("football-dir", "tennis-dir", "atp-canonical", "nba-dir", "xgabora"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    res = {"label": "EDGE DISCOVERY CYCLE 1 -- DISCOVERY ONLY; nothing here is validated"}
    res["football_per_book"] = football(a.football_dir)
    res["xgabora"] = xgabora(a.xgabora)
    res["tennis"] = tennis(a.tennis_dir, a.atp_canonical)
    res["nba"] = nba(a.nba_dir)
    res["prospective_tennis_snapshots"] = prospective()
    at = pd.DataFrame(ATLAS)
    # Benjamini-Hochberg across atlas tests with p-values
    pv = at.p_value_full.astype(float)
    ok = pv.notna()
    order = pv[ok].sort_values()
    m = len(order)
    bh = pd.Series(False, index=at.index)
    if m:
        thr = (np.arange(1, m + 1) / m) * 0.10
        passed = order.values <= thr
        if passed.any():
            k = np.max(np.where(passed)[0])
            bh[order.index[: k + 1]] = True
    at["bh_q10_significant"] = bh
    at["status"] = np.where(at.temporal_sign_stable.fillna(False) & at.bh_q10_significant, "CANDIDATE", "OBSERVED")
    res["atlas_tests_with_p"] = int(m)
    OUT.mkdir(parents=True, exist_ok=True)
    at.to_csv(OUT / "ATLAS.csv", index=False)
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print(at[["behaviour_id", "n_discovery", "n_confirmation", "discovery_effect", "confirmation_effect", "confirmation_ci", "temporal_sign_stable", "p_value_full", "bh_q10_significant", "status"]].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
