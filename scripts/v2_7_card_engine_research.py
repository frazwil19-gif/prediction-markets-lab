"""V2-7 card-engine research (pre-registered: research/platform_v2/card_engine_v2_7/PREREGISTRATION.md).

Research only: never writes paper ledgers, never changes gates. Evidence classes A (probability-only), B (indicative odds),
D (live descriptive). Class C (executable multi backtest) is not possible with available data.
Usage: python scripts/v2_7_card_engine_research.py --football-dir <dir> --nba-dir <dir> --td-dir <dir> --atp-canonical <csv>
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/card_engine_v2_7"
SEED, N_BOOT = 20260930, 2000
BANDS = [(0.50, 0.65, "50-65%"), (0.65, 0.80, "65-80%"), (0.80, 1.01, "80%+")]
HOLDOUT = {"tennis_atp": {2024, 2025}, "tennis_wta": {2024, 2025}, "nba": {"2024-2025", "2025-2026"},
           "football": {"2024_25", "2025_26"}}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def wilson(k: int, n: int, z: float = 1.96) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


# ---------------------------------------------------------------- legs (favourite side, frozen estimators)
def legs_tennis(path: Path, tour: str) -> pd.DataFrame:
    t = pd.read_csv(path).dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "scheduled_start"])
    p = t.p_a_market_multiplicative.astype(float)
    y = t.outcome_a_won.astype(int)
    return pd.DataFrame({"sport": f"tennis_{tour}", "event": t.match_id.astype(str), "start": t.scheduled_start,
                         "day": t.scheduled_start.str[:10], "period": t.year, "group": t.tourney_name,
                         "p": np.where(p >= 0.5, p, 1 - p), "won": np.where(p >= 0.5, y, 1 - y)})


def legs_nba(d: Path) -> pd.DataFrame:
    fr = []
    for f in sorted(d.glob("nba_*_results_odds.csv")):
        x = pd.read_csv(f)
        x["season"] = f.stem.split("_")[1]
        fr.append(x)
    n = pd.concat(fr, ignore_index=True)
    n = n[(n["round"].astype(str) != "Pre-season") & (n.is_allstar.astype(str) != "True")].dropna(subset=["home_odds", "away_odds"])
    ih, ia = 1 / n.home_odds, 1 / n.away_odds
    ph = ih / (ih + ia)
    y = n.home_win.astype(str).eq("True").astype(int)
    return pd.DataFrame({"sport": "nba", "event": n.date.astype(str) + "|" + n.home_team, "start": n.date.astype(str),
                         "day": n.date.astype(str), "period": n.season, "group": "NBA",
                         "p": np.where(ph >= 0.5, ph, 1 - ph), "won": np.where(ph >= 0.5, y, 1 - y)})


def legs_football(d: Path) -> pd.DataFrame:
    bt = _load("bt6h", REPO / "scripts/v2_6h_historical_backtest.py")
    b, m = bt.load_football(d)
    c = bt.consensus(b[b.price_timing == "closing"]).merge(m, on="match_id")
    P = c[["home", "draw", "away"]].to_numpy(float)
    P = P / P.sum(1, keepdims=True)
    k = P.argmax(1)
    pf = P[np.arange(len(P)), k]
    won = (c.full_time_result.to_numpy() == np.array(["H", "D", "A"])[k]).astype(int)
    out = pd.DataFrame({"sport": "football", "event": c.match_id.astype(str), "start": c.match_date.astype(str),
                        "day": c.match_date.astype(str), "period": c.season, "group": c.competition_code, "p": pf, "won": won})
    return out[out.p >= 0.5]


# ---------------------------------------------------------------- A1 joint calibration
def cards(legs: pd.DataFrame, k: int) -> pd.DataFrame:
    """Deterministic disjoint k-leg cards within sport-day, legs sorted by (start, event)."""
    rows = []
    for (sport, day), g in legs.sort_values(["sport", "day", "start", "event"]).groupby(["sport", "day"], sort=True):
        g = g.reset_index(drop=True)
        for i in range(0, len(g) - k + 1, k):
            c = g.iloc[i:i + k]
            rows.append({"sport": sport, "day": day, "period": c.period.iloc[0], "k": k, "p_joint": float(c.p.prod()),
                         "won": int(c.won.all()), "same_group": int(c.group.nunique() == 1)})
    return pd.DataFrame(rows)


def band_table(df: pd.DataFrame, pcol: str, ycol: str) -> dict:
    out = {}
    for lo, hi, lab in BANDS:
        x = df[(df[pcol] >= lo) & (df[pcol] < hi)]
        n, k = len(x), int(x[ycol].sum())
        if n:
            pred = float(x[pcol].mean())
            out[lab] = {"n": n, "pred": round(pred, 4), "actual": round(k / n, 4), "wilson95": wilson(k, n),
                        "actual_over_pred": round((k / n) / pred, 4), "pred_inside_ci": wilson(k, n)[0] <= pred <= wilson(k, n)[1]}
    return out


def joint_calibration(legs: pd.DataFrame) -> dict:
    res = {}
    for sport, g in legs.groupby("sport"):
        hold = g.period.isin(HOLDOUT[sport])
        r = {}
        for per, gg in (("development", g[~hold]), ("holdout_years", g[hold])):
            singles = gg.rename(columns={"p": "p_joint"}).assign(won=gg.won)
            r[per] = {"singles": band_table(singles, "p_joint", "won"),
                      "doubles": band_table(cards(gg, 2), "p_joint", "won"),
                      "trebles": band_table(cards(gg, 3), "p_joint", "won")}
        if sport.startswith("tennis"):
            d = cards(g, 2)
            r["tennis_doubles_by_dependence"] = {"same_tournament": band_table(d[d.same_group == 1], "p_joint", "won"),
                                                 "different_tournament": band_table(d[d.same_group == 0], "p_joint", "won")}
        r["search_space"] = {"legs": int(len(g)), "days": int(g.day.nunique()), "doubles": int(len(cards(g, 2))),
                             "trebles": int(len(cards(g, 3)))}
        res[sport] = r
    return res


# ---------------------------------------------------------------- A2 over-dispersion
def dispersion(legs: pd.DataFrame) -> dict:
    rng = np.random.default_rng(SEED)
    out = {}
    for sport, g in legs.groupby("sport"):
        d = g.groupby("day").apply(lambda x: pd.Series({"L": int((1 - x.won).sum()), "E": float((1 - x.p).sum()),
                                                       "V": float((x.p * (1 - x.p)).sum()), "n": len(x)}), include_groups=False)
        d = d[(d.V > 0) & (d.n >= 2)]
        z = ((d.L - d.E) ** 2 / d.V).to_numpy()
        bs = [z[rng.integers(0, len(z), len(z))].mean() for _ in range(N_BOOT)]
        out[sport] = {"days": int(len(d)), "dispersion_index": round(float(z.mean()), 4),
                      "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                      "mean_legs_per_day": round(float(d.n.mean()), 2)}
    return out


# ---------------------------------------------------------------- B indicative (tennis-data Bet365 closing, same book)
def indicative_b365(td_dir: Path, atp_canonical: Path) -> dict:
    dg = _load("diag6d", REPO / "scripts/v2_6d_tennis_closing_diagnostic.py")
    atp = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv").merge(
        pd.read_csv(atp_canonical, usecols=["match_id", "player_a_name", "player_b_name"]), on="match_id")
    wta = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    out = {"label": "INDICATIVE (class B): Bet365 closing, untimestamped; P = Pinnacle closing de-vig (reference, not the frozen engine)"}
    for tour, ours in (("ATP", atp), ("WTA", wta)):
        ours = ours.dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "player_a_name", "player_b_name"]).copy()
        ours["date"] = pd.to_datetime(ours.scheduled_start.str[:10])
        m, _ = dg.build(tour, dg.load_td(td_dir, tour), ours)
        m = m[m.b365_valid & m.pPS_a.notna()]
        legs = []
        for s in ("a", "b"):
            p, o = m[f"pPS_{s}"], m[f"b365_{s}"]
            ev = p * (o - 1) - (1 - p)
            legs.append(pd.DataFrame({"event": m.match_id, "day": m.scheduled_start.str[:10], "p": p, "odds": o, "ev": ev,
                                      "won": m[f"won_{s}"]}))
        L = pd.concat(legs)
        L = L[(L.p >= 0.5)]
        pos = L[L.ev > 0]
        r = {"favourite_legs": int(len(L)), "positive_ev_legs": int(len(pos)),
             "positive_ev_legs_per_100_favourites": round(100 * len(pos) / max(1, len(L)), 2)}
        for k, name in ((2, "doubles"), (3, "trebles")):
            combos = []
            for day, g in pos.groupby("day"):
                for c in itertools.combinations(g.itertuples(index=False), k):
                    if len({x.event for x in c}) < k:
                        continue
                    pj = float(np.prod([x.p for x in c]))
                    oj = float(np.prod([x.odds for x in c]))
                    combos.append({"p_joint": pj, "odds_joint": oj, "ev": pj * oj - 1, "won": int(all(x.won for x in c))})
            cdf = pd.DataFrame(combos)
            days = pos.day.nunique()
            r[name] = {"cards": int(len(cdf)), "days_with_any": int(cdf.shape[0] and pos.groupby("day").size().ge(k).sum()),
                       "of_days_with_a_positive_leg": int(days)}
            if len(cdf):
                pnl = np.where(cdf.won == 1, cdf.odds_joint - 1, -1.0)
                r[name].update({"mean_p_joint": round(float(cdf.p_joint.mean()), 4), "mean_est_ev": round(float(cdf.ev.mean()), 4),
                                "hit_rate": round(float(cdf.won.mean()), 4), "wilson95": wilson(int(cdf.won.sum()), len(cdf)),
                                "roi_indicative": round(float(pnl.mean()), 4)})
        pnl1 = np.where(pos.won == 1, pos.odds - 1, -1.0)
        r["singles"] = {"n": int(len(pos)), "mean_p": round(float(pos.p.mean()), 4), "mean_est_ev": round(float(pos.ev.mean()), 4),
                        "hit_rate": round(float(pos.won.mean()), 4), "roi_indicative": round(float(pnl1.mean()), 4)}
        out[tour] = r
    return out


# ---------------------------------------------------------------- D live snapshot
def live_snapshot() -> dict:
    X = list(csv.DictReader(open(REPO / "tennis_predictions/exchange_probability_snapshots.csv")))
    P = list(csv.DictReader(open(REPO / "tennis_predictions/price_snapshots.csv")))
    scan = max(r["scan_timestamp_utc"] for r in X)
    X = [r for r in X if r["scan_timestamp_utc"] == scan and r["source_validated"] == "True"]
    P = [r for r in P if r["scan_timestamp_utc"] == scan]
    books = {}
    legs = []
    for x in X:
        w = float(x["exchange_spread_prob"]) if x["exchange_spread_prob"] not in ("", None) else None
        if w is None or w > 0.03:
            continue
        pa = float(x["p_a"])
        fav, pf = (x["player_a"], pa) if pa >= 0.5 else (x["player_b"], 1 - pa)
        for r in P:
            if r["event_id"] != x["event_id"] or r["bookmaker"].startswith(("betfair_ex", "matchbook", "smarkets")):
                continue
            o = float(r["odds_a"] if r["player_a"] == fav else r["odds_b"])
            books.setdefault(r["bookmaker"], []).append({"event": x["event_id"], "tour": x["sport_key"], "sel": fav, "p": pf,
                                                         "odds": o, "po": pf * o})
    summary = {"scan": scan, "tight_book_favourites": len({l["event"] for b in books.values() for l in b}),
               "per_bookmaker": {}}
    for bk, ls in sorted(books.items()):
        pos = [l for l in ls if l["po"] > 1.0]
        d = sum(1 for c in itertools.combinations(pos, 2) if c[0]["event"] != c[1]["event"])
        t = sum(1 for c in itertools.combinations(pos, 3) if len({x["event"] for x in c}) == 3)
        summary["per_bookmaker"][bk] = {"favourites_priced": len(ls), "positive_ev_legs": len(pos),
                                        "doubles_all_legs_positive": d, "trebles_all_legs_positive": t,
                                        "median_P_times_O": round(float(np.median([l["po"] for l in ls])), 4) if ls else None}
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--football-dir", type=Path, required=True)
    ap.add_argument("--nba-dir", type=Path, required=True)
    ap.add_argument("--td-dir", type=Path, required=True)
    ap.add_argument("--atp-canonical", type=Path, required=True)
    a = ap.parse_args()
    legs = pd.concat([legs_tennis(REPO / "data/interim/v2_tennis_market_dataset.csv", "atp"),
                      legs_tennis(REPO / "data/interim/v2_wta_market_dataset.csv", "wta"),
                      legs_nba(a.nba_dir), legs_football(a.football_dir)], ignore_index=True)
    res = {"label": "RESEARCH ONLY -- classes A (probability-only), B (indicative), D (live descriptive); no executable multi backtest",
           "A1_joint_calibration": joint_calibration(legs), "A2_dispersion": dispersion(legs),
           "B_indicative_b365_tennis": indicative_b365(a.td_dir, a.atp_canonical), "D_live_snapshot": live_snapshot()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print("written", OUT / "RESULTS.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
