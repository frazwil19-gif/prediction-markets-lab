"""V2-7H historical betting-card backtest (RESEARCH ONLY). Pre-registration:
research/platform_v2/card_backtest_v2_7h/PREREGISTRATION.md (+ AMENDMENTS.md).

Never touches production, the V2-7 prospective logger, bsv2-3 or frozen engines. Never pairs the frozen tennis T-30 P with a
closing bookmaker price. Evidence labels: PROB, ASOF-FB, CLOSE-DIAG, SYNTH (see pre-registration section 0).

Usage: python scripts/v2_7h_card_backtest.py --data /mnt/user-data/uploads/prediction-markets-lab/data [--cache <dir>]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.research import card_backtest as CB

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/card_backtest_v2_7h"
HOLDOUT = {"tennis_atp": {2024, 2025}, "tennis_wta": {2024, 2025}, "nba": {"2024-2025", "2025-2026"},
           "football": {"2024_25", "2025_26"}}
STAKES = (0.005, 0.01, 0.02, 0.03, 0.05)
PRIMARY_BOOKS = {"B365": 0.0, "WH": 0.0, "BW": 0.0, "BF": 0.05}
MULTI_BOOKS = ("B365", "WH", "BW")          # amendment A1: BF singles only
SYNTH_M = (0.0, 0.05)
DELTAS = (0.005, 0.01, 0.015, 0.02, 0.03, 0.05)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def period_of(sport: str, per) -> str:
    key = "tennis_atp" if sport.startswith("tennis_atp") else "tennis_wta" if sport.startswith("tennis_wta") else sport
    return "holdout" if per in HOLDOUT[key] else "development"


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


# ---------------------------------------------------------------- legs (frozen estimators, favourite side)
def legs_tennis(tour: str, canon: Path) -> pd.DataFrame:
    if tour == "atp":
        t = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv")
        t = t.merge(pd.read_csv(canon, usecols=["match_id", "player_a_name", "player_b_name"]), on="match_id", how="left")
    else:
        t = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    t = t.dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "scheduled_start"])
    p = t.p_a_market_multiplicative.astype(float).values
    y = t.outcome_a_won.astype(int).values
    fav_a = p >= 0.5
    pa = t.player_a_name.fillna("?A" + t.match_id.astype(str)).values
    pb = t.player_b_name.fillna("?B" + t.match_id.astype(str)).values
    return pd.DataFrame({"sport": f"tennis_{tour}", "event": t.match_id.astype(str).values, "start": t.scheduled_start.values,
                         "day": t.scheduled_start.str[:10].values, "period": t.year.values, "group": t.tourney_name.values,
                         "p": np.where(fav_a, p, 1 - p), "won": np.where(fav_a, y, 1 - y),
                         "participants": [tuple(sorted((a, b))) for a, b in zip(pa, pb)], "p_a_T30": p})


def legs_nba(d: Path) -> pd.DataFrame:
    fr = []
    for f in sorted(d.glob("nba_*_results_odds.csv")):
        x = pd.read_csv(f)
        x["season"] = f.stem.split("_")[1]
        fr.append(x)
    n = pd.concat(fr, ignore_index=True)
    n = n[(n["round"].astype(str) != "Pre-season")]
    if "is_allstar" in n:
        n = n[n.is_allstar.astype(str) != "True"]
    n = n.dropna(subset=["home_odds", "away_odds"])
    n = n[(n.home_odds > 1) & (n.away_odds > 1)]
    ih, ia = 1 / n.home_odds, 1 / n.away_odds
    ph = (ih / (ih + ia)).values
    y = n.home_win.astype(str).eq("True").astype(int).values
    return pd.DataFrame({"sport": "nba", "event": (n.date.astype(str) + "|" + n.home_team).values, "start": n.date.astype(str).values,
                         "day": n.date.astype(str).values, "period": n.season.values, "group": "NBA",
                         "p": np.where(ph >= 0.5, ph, 1 - ph), "won": np.where(ph >= 0.5, y, 1 - y),
                         "participants": [tuple(sorted((a, b))) for a, b in zip(n.home_team, n.away_team)]})


def football_frames(d: Path):
    bt = _load("bt6h", REPO / "scripts/v2_6h_historical_backtest.py")
    b, m = bt.load_football(d)
    teams = pd.concat([pd.read_csv(d / "cycle_001_matches_full.csv"), pd.read_csv(d / "h_fb2_002_sealed_oos_2025_26_matches.csv")]
                      ).drop_duplicates("match_id")[["match_id", "home_team_normalised", "away_team_normalised"]]
    return bt, b, m.merge(teams, on="match_id", how="left")


def legs_football(bt, b, m, snapshot: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Favourite legs from the frozen consensus of ONE snapshot, plus same-snapshot per-book quotes for that selection."""
    bs = b[b.price_timing == snapshot]
    c = bt.consensus(bs).merge(m, on="match_id")
    P = c[["home", "draw", "away"]].to_numpy(float)
    P = P / P.sum(1, keepdims=True)
    k = P.argmax(1)
    sel = np.array(["home", "draw", "away"])[k]
    pf = P[np.arange(len(P)), k]
    won = (c.full_time_result.to_numpy() == np.array(["H", "D", "A"])[k]).astype(int)
    legs = pd.DataFrame({"sport": "football", "event": c.match_id.astype(str).values, "start": c.match_date.astype(str).values,
                         "day": c.match_date.astype(str).values, "period": c.season.values, "group": c.competition_code.values,
                         "p": pf, "won": won, "selection": sel,
                         "participants": [tuple(sorted((str(a), str(bb)))) for a, bb in zip(c.home_team_normalised, c.away_team_normalised)]})
    legs = legs[legs.p >= 0.5].reset_index(drop=True)
    q = bs[bs.bookmaker.isin(PRIMARY_BOOKS)].merge(legs[["event", "selection"]].assign(match_id=lambda x: x.event.astype(int)), on="match_id")
    q["odds"] = np.select([q.selection == "home", q.selection == "draw"], [q.home_odds, q.draw_odds], q.away_odds).astype(float)
    q = q[q.odds > 1.0]
    quotes = q[["event", "bookmaker", "odds"]].rename(columns={"bookmaker": "book"}).merge(legs, on="event")
    quotes["comm"] = quotes.book.map(PRIMARY_BOOKS)
    return legs, finish_quotes(quotes)


def finish_quotes(q: pd.DataFrame) -> pd.DataFrame:
    q = q.copy()
    q["odds_net"] = 1 + (q.odds - 1) * (1 - q.comm)
    q["ev"] = q.p * q.odds_net - 1
    return q


def legs_tennis_closing_diag(tour: str, canon: Path, td_dir: Path, cache: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """CLOSE-DIAG: P = Pinnacle-close de-vig (reference estimator), price = Bet365 close; V2-6D linkage + validity screen.
    Returns (legs with PS P, quotes at B365, linked frame with T-30 P for the contamination sensitivity)."""
    f = cache / f"td_linked_{tour}.pkl"
    if f.exists():
        m = pd.read_pickle(f)
    else:
        d6 = _load("d6", REPO / "scripts/v2_6d_tennis_closing_diagnostic.py")
        if tour == "atp":
            ours = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv").merge(
                pd.read_csv(canon, usecols=["match_id", "player_a_name", "player_b_name"]), on="match_id", how="left")
        else:
            ours = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
        ours = ours.dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "player_a_name", "player_b_name"]).copy()
        ours["date"] = pd.to_datetime(ours.scheduled_start.str[:10])
        m, _ = d6.build(tour.upper(), d6.load_td(td_dir, tour.upper()), ours)
        m.to_pickle(f)
    m = m[m.b365_valid & m.pPS_a.notna() & (m.ps_a > 1) & (m.ps_b > 1)].copy()
    fav_a = m.pPS_a >= 0.5
    legs = pd.DataFrame({"sport": f"tennis_{tour}", "event": m.match_id.astype(str).values, "start": m.scheduled_start.values,
                         "day": m.scheduled_start.str[:10].values, "period": m.year.values, "group": m.tourney_name.values,
                         "p": np.where(fav_a, m.pPS_a, m.pPS_b), "won": np.where(fav_a, m.won_a, m.won_b),
                         "participants": [tuple(sorted((a, b))) for a, b in zip(m.player_a_name, m.player_b_name)],
                         "odds": np.where(fav_a, m.b365_a, m.b365_b), "p_T30_fav": np.where(fav_a, m.pT30_a, m.pT30_b)})
    quotes = finish_quotes(legs.assign(book="B365", comm=0.0))
    return legs.drop(columns=["odds"]), quotes, m


# ---------------------------------------------------------------- analyses
def calibration_section(legs: pd.DataFrame) -> dict:
    out = {}
    for k in (1, 2, 3):
        cards, dropped = CB.disjoint_cards(legs, k)
        r = {"dropped_repeated_participant": dropped}
        for per in ("development", "holdout"):
            c = cards[cards.period.map(lambda x: period_of(legs.sport.iloc[0], x)) == per]
            if not len(c):
                continue
            m = CB.calib_metrics(c.p_joint.values, c.won.values, c.day.values)
            m.update({"distinct_leg_sets": int(c.legset.nunique()), "distinct_events": int(len({e for t in c.events for e in t})),
                      "distinct_days": int(c.day.nunique())})
            r[per] = {"overall": m, "bands": CB.band_metrics(c, CB.CARD_BANDS),
                      "fine_bands": CB.band_metrics(c, CB.FINE_BANDS)}
            if k == 1:
                r[per]["leg_thresholds"] = {f">={t:.2f}": CB.calib_metrics(c[c.p_joint >= t].p_joint.values, c[c.p_joint >= t].won.values,
                                                                          c[c.p_joint >= t].day.values, recal=False)
                                            for t in CB.LEG_THRESHOLDS}
            if k >= 2 and "group" in legs:
                sg = c[c.same_group == 1]
                dg = c[c.same_group == 0]
                r[per]["same_group_cards"] = CB.calib_metrics(sg.p_joint.values, sg.won.values, sg.day.values, recal=False) if len(sg) else {}
                r[per]["cross_group_cards"] = CB.calib_metrics(dg.p_joint.values, dg.won.values, dg.day.values, recal=False) if len(dg) else {}
        out[f"k{k}"] = r
    return out


def independence_section(legs: pd.DataFrame) -> dict:
    out = {}
    for per in ("development", "holdout"):
        g = legs[legs.period.map(lambda x: period_of(legs.sport.iloc[0], x)) == per]
        out[per] = {"pair_residuals": CB.pair_residual_stats(g), "dispersion": CB.dispersion_index(g),
                    "U2_exhaustive": {f"k{k}": CB.exhaustive_inlarge(g, k) for k in (2, 3)}}
    return out


def kish_section(legs: pd.DataFrame) -> dict:
    """Model-implied Kish n_eff / raw for the exhaustive within-day universe (U2) on 60 seeded random days."""
    rng = np.random.default_rng(CB.SEED)
    days = sorted(legs.day.unique())
    res = {}
    for k, cap in ((2, 40), (3, 14)):
        eligible = [d for d in days if k <= (legs.day == d).sum() <= cap]
        pick = rng.choice(len(eligible), size=min(60, len(eligible)), replace=False) if eligible else []
        raw = neff = 0.0
        for i in pick:
            g = legs[legs.day == eligible[i]]
            p = dict(zip(g.event, g.p))
            cards = list(__import__("itertools").combinations(sorted(p), k))
            raw += len(cards)
            neff += CB.kish_neff(cards, p)
        res[f"k{k}"] = {"days_sampled": len(pick), "max_legs_per_day": cap, "raw_cards": int(raw),
                        "kish_n_eff": round(neff, 1), "ratio": round(neff / raw, 4) if raw else None,
                        "distinct_events": int(sum((legs.day == eligible[i]).sum() for i in pick))}
    return res


def strategy_context(legs_dev: pd.DataFrame) -> dict:
    """S2 supported bands and S5 band SE, from DEVELOPMENT-period singles only (fixed before holdout evaluation)."""
    supported, se = [], {}
    for lo, hi, lab in CB.FINE_BANDS:
        x = legs_dev[(legs_dev.p >= lo) & (legs_dev.p < hi)]
        if len(x) < 30:
            continue
        m = CB.calib_metrics(x.p.values, x.won.values, x.day.values, recal=False)
        se[(lo, hi)] = m["min_detectable_dev_2se"] / 2
        if abs(m["bias"]) <= 0.01 and m["ci_halfwidth"] <= 0.015:
            supported.append((lo, hi))
    big = max(se.values()) if se else 0.05

    def band_se(p: float) -> float:
        for (lo, hi), v in se.items():
            if lo <= p < hi:
                return v
        return big
    return {"supported_bands": supported, "band_se": band_se,
            "_report": {"supported_bands": [f"{lo:.2f}-{hi:.2f}" for lo, hi in supported],
                        "band_se": {f"{lo:.2f}-{hi:.2f}": round(v, 4) for (lo, hi), v in se.items()}}}


def build_days(legs: pd.DataFrame, quotes: pd.DataFrame | None, strategy: str, k: int, ctx: dict, synth_m: float | None) -> tuple[list, dict]:
    """Chronological frozen selections. Returns days [{day, period, p, o, y, events, book}] and counts."""
    days, counts = [], {"days_total": 0, "days_no_card": 0, "days_no_single_book": 0}
    qd = dict(tuple(quotes.groupby("day"))) if quotes is not None else {}
    lookup = legs.set_index("event")
    for day, g in legs.groupby("day", sort=True):
        counts["days_total"] += 1
        if strategy in ("S1", "S2", "S5"):
            sel = CB.select_prob(g, k, strategy, ctx)
            if sel is None:
                counts["days_no_card"] += 1
                continue
            evs = [r["event"] for r in sel]
            ps = [r["p"] for r in sel]
            if synth_m is not None:
                o = [1 / (p * (1 + synth_m)) for p in ps]
                book = "SYNTH"
            else:
                q = qd.get(day)
                q = q[q.event.isin(evs)] if q is not None else None
                books = MULTI_BOOKS if k >= 2 else tuple(PRIMARY_BOOKS)
                best = None
                if q is not None:
                    for bk, gb in q[q.book.isin(books)].groupby("book"):
                        if set(gb.event) == set(evs):
                            on = [float(gb[gb.event == e].odds_net.iloc[0]) for e in evs]
                            if best is None or math.prod(on) > math.prod(best[1]):
                                best = (bk, on)
                if best is None:
                    counts["days_no_single_book"] += 1
                    continue
                book, o = best
        else:
            q = qd.get(day)
            if q is None:
                counts["days_no_card"] += 1
                continue
            q = q[q.book.isin(MULTI_BOOKS if k >= 2 else tuple(PRIMARY_BOOKS))]
            sel = CB.select_priced(q, k, strategy)
            if sel is None:
                counts["days_no_card"] += 1
                continue
            evs, ps, o, book = [r["event"] for r in sel], [r["p"] for r in sel], [r["odds_net"] for r in sel], sel[0]["book"]
        y = [int(lookup.loc[e, "won"]) for e in evs]           # outcomes revealed only after the selection is frozen
        days.append({"day": day, "period": period_of(legs.sport.iloc[0], lookup.loc[evs[0], "period"]), "p": ps, "o": o, "y": y,
                     "events": evs, "book": book})
    return days, counts


def simulation_section(legs: pd.DataFrame, quotes: pd.DataFrame | None, strategies: tuple, label: str,
                       synth_m: float | None, ctx: dict) -> dict:
    out = {"label": label}
    for st in strategies:
        for k in (1, 2, 3):
            days, counts = build_days(legs, quotes, st, k, ctx, synth_m)
            r = {"counts": counts}
            for per in ("development", "holdout"):
                dd = [d for d in days if d["period"] == per]
                if not dd:
                    continue
                ev_card = [math.prod(d["p"]) * math.prod(d["o"]) - 1 for d in dd]
                evs = [e for d in dd for e in d["events"]]
                rr = {"n_days": len(dd), "distinct_events": len(set(evs)), "event_reuse_max": int(pd.Series(evs).value_counts().max()),
                      "books": dict(pd.Series([d["book"] for d in dd]).value_counts()),
                      "mean_p_joint": round(float(np.mean([math.prod(d["p"]) for d in dd])), 4),
                      "realised_card_win_rate": round(float(np.mean([all(d["y"]) for d in dd])), 4),
                      "mean_model_card_ev": round(float(np.mean(ev_card)), 5),
                      "calibration": CB.calib_metrics(np.array([math.prod(d["p"]) for d in dd]), np.array([int(all(d["y"])) for d in dd]),
                                                      np.array([d["day"] for d in dd]), recal=False),
                      "stakes": {}}
                for s in STAKES:
                    card = CB.simulate(dd, s, "card", n_boot=500)
                    if k == 1:
                        rr["stakes"][str(s)] = {"single": card}
                        continue
                    sing = CB.simulate(dd, s, "singles", n_boot=500)
                    rr["stakes"][str(s)] = {"card": card, "singles": sing, "comparison": CB.compare(card, sing)}
                r[per] = rr
            out[f"{st}|k{k}"] = r
    return out


def margin_section(quotes: pd.DataFrame, legs: pd.DataFrame) -> dict:
    """Margin compounding: mean net EV of ALL favourite same-book cards (disjoint within day per book) by k."""
    res = {}
    for book, q in quotes.groupby("book"):
        if book not in MULTI_BOOKS and book != "B365":
            continue
        base = q[["event", "sport", "day", "period", "group", "participants", "p", "won", "ev"]]
        r = {"legs": int(len(base)), "mean_leg_ev": round(float(base.ev.mean()), 5)}
        for k in (2, 3):
            cards, _ = CB.disjoint_cards(base.assign(p=1 + base.ev), k)     # p field reused to carry (1+EV); product = 1+card EV
            r[f"k{k}_mean_card_ev"] = round(float((cards.p_joint - 1).mean()), 5) if len(cards) else None
            r[f"k{k}_n"] = int(len(cards))
            r[f"k{k}_naive_k_times_leg_ev"] = round(k * float(base.ev.mean()), 5)
        res[book] = r
    return res


def stress_section(priced_cards: list[dict]) -> dict:
    """Deterministic grid + empirical tolerance on POS_EV cards (k>=2 and singles)."""
    grid = {}
    for k in (1, 2, 3):
        for p0 in (0.55, 0.60, 0.70, 0.80, 0.90):
            for e0 in (0.02, 0.05):
                pj = p0 ** k
                o = (1 + e0) / pj                                    # price at which model card EV = e0
                ol = (1 + e0) ** (1 / k) / p0                        # the same card built from k equal legs
                rows = {}
                for d in (-0.05, -0.03, -0.02, -0.015, -0.01, -0.005, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05):
                    pt = p0 - d                                      # d > 0: model OVERestimates each leg by d
                    pjt = pt ** k
                    ev = pjt * o - 1
                    kelly = ev / (o - 1) if o > 1 else 0.0
                    gc, gs = CB.growth_pair([pt] * k, [ol] * k, 0.01) if k > 1 else (None, None)
                    rows[f"{d:+.3f}"] = {"true_p_joint": round(pjt, 5), "rel_change_p_joint": round(pjt / pj - 1, 4),
                                         "fair_odds_true": round(1 / pjt, 4), "true_ev": round(ev, 5), "kelly": round(max(kelly, 0.0), 5),
                                         "qualifies_ev_gt0": ev > 0, "qualifies_ev_ge2pct": ev >= 0.02,
                                         "card_minus_singles_growth_1pct": round(gc - gs, 7) if gc is not None else None}
                grid[f"k{k}|p{p0}|modelEV{e0}"] = {"card_price": round(o, 4), "tolerance_to_ev0_pp": round(100 * CB.tolerance([p0] * k, o), 3),
                                                   "tolerance_to_ev2pct_pp": round(100 * CB.tolerance([p0] * k, o, 0.02), 3), "shifts": rows}
    emp = {}
    for k in (1, 2, 3):
        cs = [c for c in priced_cards if len(c["p"]) == k]
        if not cs:
            continue
        tol = np.array([CB.tolerance(c["p"], math.prod(c["o"])) for c in cs])
        surv = {}
        for d in DELTAS:
            evd = np.array([math.prod(max(p - d, 0) for p in c["p"]) * math.prod(c["o"]) - 1 for c in cs])
            surv[f"{d*100:.1f}pp"] = {"share_ev_gt0": round(float((evd > 0).mean()), 4), "share_ev_ge2pct": round(float((evd >= 0.02).mean()), 4)}
        adv = []
        if k > 1:
            for c in cs:
                gc, gs = CB.growth_pair(c["p"], c["o"], 0.01)
                if gc <= gs:
                    adv.append(0.0)
                    continue
                lo, hi = 0.0, min(c["p"])
                for _ in range(40):
                    m = (lo + hi) / 2
                    a, b = CB.growth_pair([max(p - m, 1e-6) for p in c["p"]], c["o"], 0.01)
                    lo, hi = (m, hi) if a > b else (lo, m)
                adv.append(lo)
        emp[f"k{k}"] = {"cards": len(cs), "tolerance_to_ev0_pp": {q: round(100 * float(np.percentile(tol, q)), 3) for q in (10, 50, 90)},
                        "survival_under_uniform_overestimate": surv,
                        "growth_advantage_1pct_tolerance_pp": ({q: round(100 * float(np.percentile(adv, q)), 3) for q in (10, 50, 90)}
                                                               if adv else None),
                        "share_with_card_growth_advantage_1pct": round(float(np.mean([a > 0 for a in adv])), 4) if adv else None}
    return {"deterministic_grid": grid, "empirical_pos_ev_cards": emp}


def cross_sport_section(all_legs: dict) -> dict:
    """Exploratory: disjoint 2-sport doubles on the same date, legs hash-ordered within each sport-date."""
    frames = []
    for sp, lg in all_legs.items():
        x = lg.assign(_h=lg.event.astype(str).map(CB.h)).sort_values(["day", "_h"])
        x["rank"] = x.groupby("day").cumcount()
        frames.append(x[["sport", "day", "rank", "p", "won", "event"]])
    res = {}
    names = list(all_legs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = frames[i], frames[j]
            mm = a.merge(b, on=["day", "rank"], suffixes=("_a", "_b"))
            if len(mm) < 50:
                continue
            pj = (mm.p_a * mm.p_b).values
            y = (mm.won_a * mm.won_b).values
            res[f"{names[i]}+{names[j]}"] = CB.calib_metrics(pj, y, mm.day.values, recal=False)
    return {"label": "EXPLORATORY cross-sport doubles (PROB)", "pairs": res}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path("/tmp/claude-0/v2_7h_cache"))
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    canon = a.data / "processed/tennis/cycle_002_canonical_matches.csv"
    td = a.data / "raw/tennis/tennis_data_co_uk"
    res: dict = {"label": "V2-7H historical card backtest -- RESEARCH ONLY", "preregistration": "PREREGISTRATION.md + AMENDMENTS.md",
                 "seed": CB.SEED, "n_boot": CB.N_BOOT}
    legs = {"tennis_atp": legs_tennis("atp", canon), "tennis_wta": legs_tennis("wta", canon), "nba": legs_nba(a.data / "raw/basketball/wippa_nba")}
    bt, b, m = football_frames(a.data / "processed/football")
    legs["football"], fq_close = legs_football(bt, b, m, "closing")
    fb_open, fq_open = legs_football(bt, b, m, "opening")
    res["leg_counts"] = {k: {"legs": int(len(v)), "days": int(v.day.nunique()),
                             "by_period": v.period.map(lambda x, s=k: period_of(s, x)).value_counts().to_dict()} for k, v in legs.items()}
    res["leg_counts"]["football_preclosing"] = {"legs": int(len(fb_open)), "days": int(fb_open.day.nunique())}
    print("legs loaded", round(time.time() - t0), "s", flush=True)

    # P1 / calibration, P2 / independence, overlap
    res["calibration_U1_PROB"] = {sp: calibration_section(lg) for sp, lg in legs.items()}
    print("calibration", round(time.time() - t0), flush=True)
    res["independence_PROB"] = {sp: independence_section(lg) for sp, lg in legs.items()}
    res["overlap_kish_U2"] = {sp: kish_section(lg) for sp, lg in legs.items()}
    print("independence/kish", round(time.time() - t0), flush=True)

    # Holm over the 12 primary holdout calibration tests (P1) and 4 independence tests (P2)
    fam = []
    for sp in legs:
        for k in (1, 2, 3):
            o = res["calibration_U1_PROB"][sp][f"k{k}"]["holdout"]["overall"]
            fam.append((f"{sp}|k{k}", o["p_value_normal"], o["ci_halfwidth"], k))
    fam.sort(key=lambda x: x[1])
    holm, running = {}, 0.0
    for i, (name, pv, hw, k) in enumerate(fam):
        adj = min(1.0, max(running, (len(fam) - i) * pv))
        running = adj
        prec_ok = hw <= (0.02 if k == 2 else 0.03 if k == 3 else 0.02)
        holm[name] = {"p": pv, "p_holm": round(adj, 5), "reject_at_0.05": adj < 0.05, "ci_halfwidth": hw,
                      "precision_ok": prec_ok,
                      "verdict": "MISCALIBRATED" if adj < 0.05 else ("CALIBRATED" if prec_ok else "INCONCLUSIVE_IMPRECISE")}
    res["P1_holm_holdout"] = holm
    fam2 = sorted([(sp, res["independence_PROB"][sp]["holdout"]["pair_residuals"]["all_pairs"]) for sp in legs], key=lambda x: abs(x[1]["z"] or 0), reverse=True)
    p2 = {}
    running = 0.0
    for i, (sp, st) in enumerate(fam2):
        pv = math.erfc(abs(st["z"]) / math.sqrt(2)) if st["z"] is not None else 1.0
        adj = min(1.0, max(running, (len(fam2) - i) * pv))
        running = adj
        p2[sp] = {"z": st["z"], "p": round(pv, 6), "p_holm": round(adj, 5), "reject_independence_at_0.05": adj < 0.05}
    res["P2_holm_holdout"] = p2

    # tennis contamination sensitivity + closing diagnostic data
    tn_diag = {}
    for tour in ("atp", "wta"):
        dl, dq, linked = legs_tennis_closing_diag(tour, canon, td, a.cache)
        tn_diag[tour] = (dl, dq)
        ok = linked[(linked.pT30_a - linked.pPS_a).abs() <= 0.10].match_id.astype(str)
        sub = legs[f"tennis_{tour}"][legs[f"tennis_{tour}"].event.isin(set(ok))]
        res.setdefault("tennis_contamination_sensitivity", {})[tour] = {
            "linked_consistent_matches": int(len(sub)), "calibration": calibration_section(sub)}
    print("tennis diag", round(time.time() - t0), flush=True)

    # strategies + equal capital
    sims = {}
    for sp, lg in legs.items():
        dev = lg[lg.period.map(lambda x, s=sp: period_of(s, x)) == "development"]
        ctx = strategy_context(dev)
        res.setdefault("strategy_context", {})[sp] = ctx["_report"]
        for mm_ in SYNTH_M:
            sims[f"{sp}|SYNTH_m{mm_}"] = simulation_section(lg, None, ("S1", "S2", "S5"), f"SYNTH m={mm_} (risk description only)", mm_, ctx)
        print("synth", sp, round(time.time() - t0), flush=True)
    for label, lg, q in (("football|ASOF-FB_preclosing", fb_open, fq_open), ("football|CLOSE-DIAG_closing", legs["football"], fq_close),
                         ("tennis_atp|CLOSE-DIAG_PSclose_vs_B365close", *tn_diag["atp"]),
                         ("tennis_wta|CLOSE-DIAG_PSclose_vs_B365close", *tn_diag["wta"])):
        sp = label.split("|")[0]
        dev = lg[lg.period.map(lambda x, s=sp: period_of(s, x)) == "development"]
        ctx = strategy_context(dev)
        res.setdefault("strategy_context", {})[label] = ctx["_report"]
        sims[label] = simulation_section(lg, q, ("S1", "S2", "S5", "S3", "S4", "S6"), label.split("|")[1], None, ctx)
        res.setdefault("margin_compounding", {})[label] = margin_section(q, lg)
        res.setdefault("priced_calibration_U1", {})[label] = calibration_section(lg)
        print("priced", label, round(time.time() - t0), flush=True)
    res["simulations"] = sims

    # stress: empirical POS_EV cards = the S3/S4/S6 selections of each priced scenario (dedup by events+book)
    stress = {}
    for label in [x for x in sims if "ASOF" in x or "CLOSE" in x]:
        lg, q = {"football|ASOF-FB_preclosing": (fb_open, fq_open), "football|CLOSE-DIAG_closing": (legs["football"], fq_close),
                 "tennis_atp|CLOSE-DIAG_PSclose_vs_B365close": tn_diag["atp"], "tennis_wta|CLOSE-DIAG_PSclose_vs_B365close": tn_diag["wta"]}[label]
        seen, cards = set(), []
        for st in ("S3", "S4", "S6"):
            for k in (1, 2, 3):
                for d in build_days(lg, q, st, k, strategy_context(lg.iloc[:0].assign()), None)[0]:
                    key = (tuple(sorted(d["events"])), d["book"])
                    if key not in seen:
                        seen.add(key)
                        cards.append(d)
        stress[label] = stress_section(cards)["empirical_pos_ev_cards"]
    res["stress"] = {"deterministic_grid": stress_section([])["deterministic_grid"], "empirical_pos_ev_cards": stress}
    res["cross_sport"] = cross_sport_section(legs)
    res["runtime_s"] = round(time.time() - t0)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESULTS.json").write_text(json.dumps(clean(res), indent=1, default=str))
    print("done", res["runtime_s"], "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
