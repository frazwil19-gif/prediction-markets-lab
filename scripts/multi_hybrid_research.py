"""Probability-first bet construction + multi + hybrid research (pre-registered:
research/platform_v2/multi_hybrid/PREREGISTRATION.md). READ-ONLY research; never touches production or paper ledgers.

Usage: python scripts/multi_hybrid_research.py --football-dir <processed/football> --tennis-dir <tennis_data_co_uk>
         --atp-canonical <cycle_002_canonical_matches.csv> --nba-dir <wippa_nba> --xgabora <Matches.csv>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from prediction_markets_lab.prediction_platform import stage_a as SA

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/multi_hybrid"
SEED, N_BOOT = 20261002, 2000
COHORTS = [0.60, 0.70, 0.75, 0.80, 0.85, 0.90]
KS = [2, 3, 4, 5]
JP_BANDS = [(0, .5, "<0.5"), (.5, .6, "0.5-0.6"), (.6, .7, "0.6-0.7"), (.7, .8, "0.7-0.8"), (.8, 1.01, "0.8+")]
ODDS_BANDS = [(1, 1.2, "<1.20"), (1.2, 1.33, "1.20-1.32"), (1.33, 1.5, "1.33-1.49"), (1.5, 2, "1.50-1.99"), (2, 3, "2.00-2.99"), (3, 1e9, "3.00+")]
FB_BOOKS = ["B365", "WH", "BW"]
XG = ["N1", "D1", "F1", "SP1", "I1", "P1", "B1", "E2", "E3", "SP2", "D2", "I2", "F2"]
RNG = np.random.default_rng(SEED)


def h(x) -> str:
    return hashlib.sha256(str(x).encode()).hexdigest()


def band(x, bands):
    for lo, hi, lab in bands:
        if lo <= x < hi:
            return lab
    return "?"


def _mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------------ legs
def tennis_prob_legs() -> pd.DataFrame:
    fr = []
    for tour, f in (("ATP", "v2_tennis_market_dataset.csv"), ("WTA", "v2_wta_market_dataset.csv")):
        x = pd.read_csv(REPO / "data/interim" / f).dropna(subset=["p_a_market_multiplicative", "outcome_a_won"])
        pa = x.p_a_market_multiplicative
        fr.append(pd.DataFrame({"sport": tour, "event": x.match_id.astype(str), "day": x.scheduled_start.str[:10],
                                "p": np.maximum(pa, 1 - pa), "won": np.where(pa >= .5, x.outcome_a_won, 1 - x.outcome_a_won).astype(int)}))
    return pd.concat(fr)


def nba_prob_legs(d: Path) -> pd.DataFrame:
    x = pd.concat([pd.read_csv(f) for f in sorted(d.glob("nba_*_results_odds.csv"))])
    x = x[(x["round"].astype(str) != "Pre-season") & (~x.is_allstar.astype(bool)) & (x.home_odds > 1) & (x.away_odds > 1)]
    ph = (1 / x.home_odds) / (1 / x.home_odds + 1 / x.away_odds)
    return pd.DataFrame({"sport": "NBA", "event": x.date + x.home_team + x.away_team, "day": x.date,
                         "p": np.maximum(ph, 1 - ph), "won": np.where(ph >= .5, x.home_win.astype(bool), ~x.home_win.astype(bool)).astype(int)})


def football_legs(d: Path, fse) -> pd.DataFrame:
    """Pre-closing consensus favourite with each book's price for that selection (same snapshot)."""
    b = pd.concat([pd.read_csv(d / "cycle_001_bookmaker_markets_full.csv"),
                   pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_bookmaker_markets.csv")], ignore_index=True)
    b = b[b.price_timing == "opening"]
    m = pd.concat([pd.read_csv(d / f, usecols=["match_id", "competition_code", "match_date", "full_time_result"])
                   for f in ("cycle_001_matches_full.csv", "h_fb2_002_sealed_oos_2025_26_matches.csv")]).drop_duplicates("match_id")
    fair = ["fair_home_probability", "fair_draw_probability", "fair_away_probability"]
    g = b.groupby("match_id")
    c = g[fair].median()
    c = c[g.size() >= 3]
    tri = c.div(c.sum(axis=1), axis=0)
    sel = np.array(["home", "draw", "away"])[tri.to_numpy().argmax(1)]
    legs = pd.DataFrame({"match_id": c.index, "p": tri.to_numpy().max(1), "sel": sel}).merge(m, on="match_id")
    legs["won"] = (legs.full_time_result == legs.sel.map({"home": "H", "draw": "D", "away": "A"})).astype(int)
    for bk in FB_BOOKS:
        q = b[b.bookmaker == bk].set_index("match_id")
        legs[f"odds_{bk}"] = [q[f"{s}_odds"].get(i, np.nan) if i in q.index else np.nan for i, s in zip(legs.match_id, legs.sel)]
    legs["sigma"] = [fse("1x2", v) for v in legs.p]
    return legs.rename(columns={"match_id": "event", "match_date": "day"}).assign(sport="football")


def tennis_fin_legs(td_dir: Path, atp_canonical: Path, cal) -> pd.DataFrame:
    v = _mod("v26d_mh", REPO / "scripts/v2_6d_tennis_closing_diagnostic.py")
    atp = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv").merge(
        pd.read_csv(atp_canonical, usecols=["match_id", "player_a_name", "player_b_name"]), on="match_id", how="left")
    wta = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    fr = []
    for tour, ours in (("ATP", atp), ("WTA", wta)):
        ours = ours.dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "player_a_name", "player_b_name"]).copy()
        ours["date"] = pd.to_datetime(ours.scheduled_start.str[:10])
        m, _ = v.build(tour, v.load_td(td_dir, tour), ours)
        m = m[m.b365_valid & m.pPS_a.notna()]
        a_fav = m.pPS_a >= .5
        fr.append(pd.DataFrame({"sport": tour, "event": m.match_id.astype(str), "day": m.date.dt.strftime("%Y-%m-%d"),
                                "p": np.where(a_fav, m.pPS_a, m.pPS_b), "won": np.where(a_fav, m.won_a, m.won_b).astype(int),
                                "odds_B365": np.where(a_fav, m.b365_a, m.b365_b)}))
    x = pd.concat(fr)
    x["sigma"] = [cal(p) for p in x.p]
    return x


# ------------------------------------------------------------------------------------------------ cards
def disjoint_cards(legs: pd.DataFrame, k: int, cohort: float) -> list[np.ndarray]:
    """Per day: cohort legs ordered by outcome-free hash, chunked into non-overlapping k-groups."""
    out = []
    x = legs[legs.p >= cohort]
    for _, g in x.groupby("day"):
        idx = g.assign(_h=g.event.map(h)).sort_values("_h").index.to_numpy()
        for i in range(0, len(idx) - k + 1, k):
            out.append(idx[i:i + k])
    return out


def topn_cards(legs: pd.DataFrame, k: int) -> list[np.ndarray]:
    out = []
    for _, g in legs.groupby("day"):
        if len(g) >= k:
            out.append(g.assign(_h=g.event.map(h)).sort_values(["p", "_h"], ascending=[False, True]).index.to_numpy()[:k])
    return out


def card_frame(legs: pd.DataFrame, cards: list[np.ndarray], odds_col: str | None = None) -> pd.DataFrame:
    if not cards:
        return pd.DataFrame()
    P, W, D = legs.p.to_numpy(), legs.won.to_numpy(), legs.day.to_numpy()
    O = legs[odds_col].to_numpy() if odds_col else None
    S = legs.sigma.to_numpy() if "sigma" in legs else None
    rows = []
    for c in cards:
        r = {"day": D[c[0]], "k": len(c), "joint_p": float(np.prod(P[c])), "hit": int(np.all(W[c])), "legs_won": int(W[c].sum())}
        if O is not None:
            o = O[c]
            if np.any(~np.isfinite(o)) or np.any(o <= 1):
                continue
            r.update(odds=float(np.prod(o)), card_ret=float(np.all(W[c]) * np.prod(o) - 1),
                     singles_ret=float(np.mean(W[c] * o - 1)), leg_ev=float(np.mean(P[c] * o - 1)),
                     card_ev=float(np.prod(P[c]) * np.prod(o) - 1),
                     card_ev_1sig=float(np.prod(np.clip(P[c] - S[c], 0, 1)) * np.prod(o) - 1),
                     min_leg_odds=float(o.min()))
        rows.append(r)
    return pd.DataFrame(rows)


def day_boot(df: pd.DataFrame, col: str) -> list:
    """Day-cluster bootstrap 95% CI of the mean of col."""
    if df.empty or df.day.nunique() < 5:
        return [None, None]
    g = df.groupby("day")[col].agg(["sum", "count"])
    s, n = g["sum"].to_numpy(), g["count"].to_numpy()
    idx = RNG.integers(0, len(g), size=(N_BOOT, len(g)))
    m = s[idx].sum(1) / n[idx].sum(1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


def calib(cf: pd.DataFrame) -> dict:
    if cf.empty:
        return {"n_cards": 0}
    cf = cf.assign(bias=cf.hit - cf.joint_p)
    eps = 1e-12
    p, y = cf.joint_p.to_numpy(), cf.hit.to_numpy()
    return {"n_cards": int(len(cf)), "unique_days": int(cf.day.nunique()), "ess": int(len(cf)),
            "mean_joint_p": round(float(p.mean()), 4), "hit_rate": round(float(y.mean()), 4),
            "bias_pp": round(100 * float(cf.bias.mean()), 2), "bias_ci_pp": [None if v is None else round(100 * v, 2) for v in day_boot(cf, "bias")],
            "brier": round(float(((p - y) ** 2).mean()), 5),
            "log_loss": round(float(-(y * np.log(np.clip(p, eps, 1)) + (1 - y) * np.log(np.clip(1 - p, eps, 1))).mean()), 5),
            "leg_accuracy": round(float(cf.legs_won.sum() / (cf.k.sum())), 4)}


def econ(cf: pd.DataFrame) -> dict:
    if cf.empty or "odds" not in cf:
        return {"n_cards": 0}
    cf = cf.assign(diff=cf.card_ret - cf.singles_ret)
    return {"n_cards": int(len(cf)), "days": int(cf.day.nunique()), "mean_joint_p": round(cf.joint_p.mean(), 4),
            "hit_rate": round(cf.hit.mean(), 4), "mean_card_odds": round(cf.odds.mean(), 3),
            "mean_leg_ev": round(cf.leg_ev.mean(), 4), "mean_card_ev": round(cf.card_ev.mean(), 4),
            "mean_card_ev_minus_1sigma": round(cf.card_ev_1sig.mean(), 4),
            "fair_vs_offered_odds_ratio": round(float((cf.odds * cf.joint_p).mean()), 4),
            "card_roi": round(cf.card_ret.mean(), 4), "card_roi_ci": day_boot(cf, "card_ret"),
            "singles_roi_equal_capital": round(cf.singles_ret.mean(), 4), "singles_roi_ci": day_boot(cf, "singles_ret"),
            "card_minus_singles": round(cf["diff"].mean(), 4), "card_minus_singles_ci": day_boot(cf, "diff"),
            "p_lose_whole_stake_card": round(1 - cf.joint_p.mean(), 4), "observed_whole_stake_loss": round(1 - cf.hit.mean(), 4),
            "var_card": round(float(cf.card_ret.var()), 4), "var_singles": round(float(cf.singles_ret.var()), 4)}


def bankroll(cf: pd.DataFrame) -> dict:
    """Chronological, first card per day; card at fraction f vs its legs as singles at f/k each (equal capital)."""
    if cf.empty or "odds" not in cf:
        return {}
    first = cf.sort_values("day").groupby("day").head(1)
    res = {}
    for start in (30, 50, 100):
        for f in (0.005, 0.01, 0.02):
            for kind, col in (("card", "card_ret"), ("singles", "singles_ret")):
                bank = peak = float(start)
                mdd, run, worst = 0.0, 0, 0
                for r in first[col].to_numpy():
                    stake = max(bank * f, 0.10)
                    bank += stake * r
                    peak = max(peak, bank)
                    mdd = max(mdd, (peak - bank) / peak)
                    run = run + 1 if r < 0 else 0
                    worst = max(worst, run)
                res[f"{start}_{f * 100:g}pct_{kind}"] = {"final": round(bank, 2), "max_dd_pct": round(100 * mdd, 1), "longest_losing_run": worst}
    for start in (30, 50):
        for flat in (3.0, 5.0):
            for kind, col in (("card", "card_ret"), ("singles", "singles_ret")):
                bank, peak, mdd, ruined = float(start), float(start), 0.0, False
                for r in first[col].to_numpy():
                    if bank < flat:
                        ruined = True
                        break
                    bank += flat * r
                    peak, mdd = max(peak, bank), max(mdd, (peak - bank) / peak)
                res[f"STRESS_{start}_flat{flat:g}_{kind}"] = {"pct_of_start": round(100 * flat / start, 1), "final": round(bank, 2),
                                                             "max_dd_pct": round(100 * mdd, 1), "ruined": ruined}
    res["cards_used"] = int(len(first))
    return res


# ------------------------------------------------------------------------------------------------ hybrid (Q5)
def hybrid(xg: Path) -> dict:
    d = pd.read_csv(xg, low_memory=False, usecols=["Division", "MatchDate", "FTResult", "OddHome", "OddDraw", "OddAway", "HomeElo", "AwayElo"])
    d["date"] = pd.to_datetime(d.MatchDate)
    d = d[d.Division.isin(XG) & (d.date >= "2020-07-01") & (d.date < "2026-07-01")].dropna()
    d = d[(d.OddHome > 1) & (d.OddDraw > 1) & (d.OddAway > 1)].copy()
    d["season"] = np.where(d.date.dt.month >= 7, d.date.dt.year, d.date.dt.year - 1)
    inv = 1 / d[["OddHome", "OddDraw", "OddAway"]].to_numpy()
    mk = inv / inv.sum(1, keepdims=True)
    d[["mH", "mD", "mA"]] = mk
    d["y"] = d.FTResult.map({"H": 0, "D": 1, "A": 2})
    d["elo_diff"] = (d.HomeElo - d.AwayElo) / 100
    feats_m = np.column_stack([np.log(d.mH / d.mD), np.log(d.mA / d.mD)])
    out = {"leakage_check": {}, "leagues": {}}
    for lg, g in d.groupby("Division"):
        tr, te = g[g.season <= 2022], g[g.season >= 2024]
        if len(tr) < 300 or len(te) < 200:
            continue
        Xm = np.column_stack([np.log(g.mH / g.mD), np.log(g.mA / g.mD)])
        Xe = g[["elo_diff"]].to_numpy()
        Xs = np.column_stack([Xm, Xe])
        itr, ite = (g.season <= 2022).to_numpy(), (g.season >= 2024).to_numpy()
        y = g.y.to_numpy()
        res = {}
        probs = {"market": g[["mH", "mD", "mA"]].to_numpy()[ite]}
        for name, X in (("elo_only", Xe), ("hybrid_stack", Xs), ("market_recalibrated", Xm)):
            mdl = LogisticRegression(max_iter=2000, C=1e6).fit(X[itr], y[itr])
            probs[name] = mdl.predict_proba(X[ite])
        yt = y[ite]
        oh = np.eye(3)[yt]
        base_ll = -np.log(np.clip(probs["market"][np.arange(len(yt)), yt], 1e-12, 1))
        for name, P in probs.items():
            ll = -np.log(np.clip(P[np.arange(len(yt)), yt], 1e-12, 1))
            fav = P.max(1)
            favwon = (P.argmax(1) == yt).astype(int)
            # favourite-side AUC-like discrimination: home-win AUC
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score((yt == 0).astype(int), P[:, 0])
            diff = ll - base_ll
            bi = RNG.integers(0, len(diff), size=(N_BOOT, len(diff)))
            ci = np.percentile(diff[bi].mean(1), [2.5, 97.5])
            hp = fav >= 0.70
            res[name] = {"n_test": int(len(yt)), "log_loss": round(float(ll.mean()), 5), "brier": round(float(((P - oh) ** 2).sum(1).mean()), 5),
                         "home_auc": round(float(auc), 4), "delta_ll_vs_market": round(float(diff.mean()), 5),
                         "delta_ll_ci": [round(float(ci[0]), 5), round(float(ci[1]), 5)],
                         "fav_ge70_n": int(hp.sum()), "fav_ge70_pred": round(float(fav[hp].mean()), 4) if hp.any() else None,
                         "fav_ge70_actual": round(float(favwon[hp].mean()), 4) if hp.any() else None}
        out["leakage_check"][lg] = {"elo_auc": res["elo_only"]["home_auc"], "market_auc": res["market"]["home_auc"],
                                    "leak_suspected": res["elo_only"]["home_auc"] > res["market"]["home_auc"]}
        # disagreement: hybrid vs market favourite-side probability
        Pm, Ph = probs["market"], probs["hybrid_stack"]
        dis = Ph[np.arange(len(yt)), Pm.argmax(1)] - Pm.max(1)
        won = (Pm.argmax(1) == yt).astype(int)
        bands = {}
        for lo, hi, lab in ((-1, -.05, "hybrid < market by >5pp"), (-.05, -.02, "-5..-2pp"), (-.02, .02, "within 2pp"), (.02, .05, "+2..+5pp"), (.05, 1, "hybrid > market by >5pp")):
            m_ = (dis >= lo) & (dis < hi)
            if m_.sum():
                bands[lab] = {"n": int(m_.sum()), "market_p": round(float(Pm.max(1)[m_].mean()), 4),
                              "hybrid_p": round(float(Ph[np.arange(len(yt)), Pm.argmax(1)][m_].mean()), 4), "actual": round(float(won[m_].mean()), 4)}
        res["disagreement_on_market_favourite"] = bands
        out["leagues"][lg] = res
    # pooled + Holm on hybrid delta
    pv = []
    for lg, r in out["leagues"].items():
        lo, hi = r["hybrid_stack"]["delta_ll_ci"]
        pv.append((lg, r["hybrid_stack"]["delta_ll_vs_market"], lo, hi))
    out["hybrid_summary"] = {"leagues_hybrid_better_ci_excludes_0": [x[0] for x in pv if x[3] < 0],
                             "leagues_hybrid_worse_ci_excludes_0": [x[0] for x in pv if x[2] > 0],
                             "mean_delta_ll": round(float(np.mean([x[1] for x in pv])), 5),
                             "note": "Holm: per-league CIs are 95% unadjusted; a league counts as better only if its CI upper bound < 0 (stricter Holm not needed if none qualify)"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    for k in ("football-dir", "tennis-dir", "atp-canonical", "nba-dir", "xgabora"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    fse, cal = SA.football_sigma(cfg.football_sigma_evidence), SA.calibration_se(cfg.calibration_results)
    res: dict = {"label": "RESEARCH ONLY -- prereg research/platform_v2/multi_hybrid/PREREGISTRATION.md"}

    prob_legs = {"ATP": None, "WTA": None}
    tp = tennis_prob_legs()
    for t in ("ATP", "WTA"):
        prob_legs[t] = tp[tp.sport == t].reset_index(drop=True)
    prob_legs["NBA"] = nba_prob_legs(a.nba_dir).reset_index(drop=True)
    fb = football_legs(a.football_dir, fse).reset_index(drop=True)
    prob_legs["football"] = fb
    tf = tennis_fin_legs(a.tennis_dir, a.atp_canonical, cal).reset_index(drop=True)

    # Q1 calibration (PROB evidence)
    q1 = {}
    for sp, legs in prob_legs.items():
        q1[sp] = {"legs": int(len(legs)), "days": int(legs.day.nunique())}
        for c in COHORTS:
            for k in KS:
                q1[sp][f"P>={c}_k{k}"] = calib(card_frame(legs, disjoint_cards(legs, k, c)))
        for k in KS:
            q1[sp][f"top{k}"] = calib(card_frame(legs, topn_cards(legs, k)))
        allc = pd.concat([card_frame(legs, disjoint_cards(legs, k, 0.5)) for k in KS])
        q1[sp]["by_joint_p_band_all_cohort0.5"] = {b: calib(g) for b, g in allc.groupby(allc.joint_p.map(lambda v: band(v, JP_BANDS)))}
    res["Q1_calibration"] = q1
    # confirmatory: >=0.80 doubles, >=0.70 trebles
    conf = []
    for sp in q1:
        for key in ("P>=0.8_k2", "P>=0.7_k3"):
            cell = q1[sp].get(key, {})
            ci = cell.get("bias_ci_pp")
            conf.append({"sport": sp, "cell": key, "n": cell.get("n_cards"), "bias_pp": cell.get("bias_pp"), "ci": ci,
                         "contains_0": None if not ci or ci[0] is None else ci[0] <= 0 <= ci[1]})
    res["Q1_confirmatory"] = conf

    # Q2/Q3 economics (B same-book product proxy)
    q2, bk = {}, {}
    fin_sets = {f"football_{b}": (fb, f"odds_{b}") for b in FB_BOOKS}
    fin_sets["tennis_B365close_PSref"] = (tf, "odds_B365")
    margin_rows = []
    for name, (legs, oc) in fin_sets.items():
        legs = legs[legs[oc].notna() & (legs[oc] > 1)].reset_index(drop=True)
        q2[name] = {}
        for c in [0.5] + COHORTS:
            for k in [1] + KS:
                cards = [np.array([i]) for i in legs.index[legs.p >= c]] if k == 1 else disjoint_cards(legs, k, c)
                cf = card_frame(legs, cards, oc)
                e = econ(cf)
                q2[name][f"P>={c}_k{k}"] = e
                if e.get("n_cards"):
                    margin_rows.append({"set": name, "cohort": c, "k": k, "n": e["n_cards"], "mean_leg_ev": e["mean_leg_ev"],
                                        "mean_card_ev": e["mean_card_ev"], "fair_vs_offered": e["fair_vs_offered_odds_ratio"],
                                        "mean_card_odds": e["mean_card_odds"], "mean_joint_p": e["mean_joint_p"]})
                if k in (2, 3) and c in (0.70, 0.80) and not cf.empty:
                    bk[f"{name}_P>={c}_k{k}"] = bankroll(cf)
        # by combined odds band and joint-P band, all cohort>=0.5 doubles/trebles
        allc = pd.concat([card_frame(legs, disjoint_cards(legs, k, 0.5), oc) for k in (2, 3)])
        q2[name]["by_card_odds_band_k2k3"] = {b: econ(g) for b, g in allc.groupby(allc.odds.map(lambda v: band(v, ODDS_BANDS)))}
        q2[name]["by_joint_p_band_k2k3"] = {b: econ(g) for b, g in allc.groupby(allc.joint_p.map(lambda v: band(v, JP_BANDS)))}
        # Q4: legs rejected by the 1.33 floor, as singles and paired with each other
        for c in (0.75, 0.80, 0.85, 0.90):
            fl = legs[(legs.p >= c) & (legs[oc] < 1.33)].reset_index(drop=True)
            q2[name][f"floor_rejected_P>={c}_singles"] = econ(card_frame(fl, [np.array([i]) for i in fl.index], oc))
            q2[name][f"floor_rejected_P>={c}_doubles"] = econ(card_frame(fl, disjoint_cards(fl, 2, c), oc))
    res["Q2_economics_B_same_book"] = q2
    res["Q3_bankroll"] = bk
    pd.DataFrame(margin_rows).to_csv(OUT / "margin_compounding.csv", index=False)
    # C class demonstration: cross-book best price per leg (football) -- inflation only
    fbc = fb.assign(odds_best=fb[[f"odds_{b}" for b in FB_BOOKS]].max(axis=1))
    fbc = fbc[fbc.odds_best > 1].reset_index(drop=True)
    res["C_cross_book_demo_NOT_EXECUTABLE"] = {f"P>={c}_k{k}": econ(card_frame(fbc, disjoint_cards(fbc, k, c), "odds_best"))
                                               for c in (0.7, 0.8) for k in (2, 3)}
    res["Q5_hybrid"] = hybrid(a.xgabora)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res["Q1_confirmatory"], indent=1))
    print(json.dumps(res["Q5_hybrid"]["hybrid_summary"], indent=1), json.dumps(res["Q5_hybrid"]["leakage_check"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
