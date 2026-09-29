"""V2-6D tennis closing-price DIAGNOSTIC (pre-registered: research/platform_v2/historical_v2_6h/
V2_6D_CLOSING_DIAGNOSTIC_PREREGISTRATION.md). NOT an executable backtest; never writes paper selections.

Usage: python scripts/v2_6d_tennis_closing_diagnostic.py --td-dir <tennis_data_co_uk dir> --atp-canonical <cycle_002_canonical_matches.csv>
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.bet_selection_v2.evaluate import load_config
from prediction_markets_lab.normalisation.player_names import full_name_matches_abbreviated, parse_abbreviated_name

REPO = Path(__file__).resolve().parents[1]
SEED, N_BOOT = 20260929, 2000
LABEL = "CLOSING-TIME DIAGNOSTIC -- not an executable backtest, not paper betting, not prospective evidence"


def load_td(d: Path, tour: str) -> pd.DataFrame:
    frames = []
    for y in range(2021, 2026):
        x = pd.read_excel(d / f"tennis_data_{tour.lower()}_{y}.xlsx")
        x["td_year_file"] = y
        frames.append(x)
    t = pd.concat(frames, ignore_index=True)
    t["Date"] = pd.to_datetime(t["Date"])
    for c in ("B365W", "B365L", "PSW", "PSL", "BFEW", "BFEL"):
        if c in t:
            t[c] = pd.to_numeric(t[c], errors="coerce")
    t["td_row"] = np.arange(len(t))
    return t


def parse(name: str):
    try:
        return parse_abbreviated_name(str(name))
    except (ValueError, TypeError):
        return None


def link(ours: pd.DataFrame, td: pd.DataFrame) -> tuple[pd.DataFrame, Counter]:
    """ours: match_id, date, player_a_name, player_b_name. Unique match on +-3 days + both structural names."""
    stats: Counter = Counter()
    td = td.assign(pw=td.Winner.map(parse), pl=td.Loser.map(parse))
    by_date = {d: g for d, g in td.groupby(td.Date.dt.normalize())}
    rows = []
    for r in ours.itertuples(index=False):
        cands = [g for k in range(-3, 4) if (g := by_date.get(r.date + pd.Timedelta(days=k))) is not None]
        if not cands:
            stats["NO_TD_ROWS_NEAR_DATE"] += 1
            continue
        c = pd.concat(cands)
        hits = []
        for t in c.itertuples(index=False):
            if t.pw is None or t.pl is None:
                continue
            aw = full_name_matches_abbreviated(r.player_a_name, t.pw) and full_name_matches_abbreviated(r.player_b_name, t.pl)
            bw = full_name_matches_abbreviated(r.player_b_name, t.pw) and full_name_matches_abbreviated(r.player_a_name, t.pl)
            if aw or bw:
                hits.append((t.td_row, "A" if aw else "B"))
        if len(hits) == 1:
            stats["MATCHED"] += 1
            rows.append({"match_id": r.match_id, "td_row": hits[0][0], "td_winner_side": hits[0][1]})
        elif len(hits) > 1:
            stats["AMBIGUOUS"] += 1
        else:
            stats["NO_NAME_MATCH"] += 1
    return pd.DataFrame(rows), stats


def mult(o1, o2):
    i1, i2 = 1 / o1, 1 / o2
    return i1 / (i1 + i2)


def boot(pnl: np.ndarray, rng) -> list:
    n = len(pnl)
    if n < 2:
        return [None, None]
    idx = rng.integers(0, n, size=(N_BOOT, n))
    r = pnl[idx].mean(1)
    return [round(float(np.percentile(r, 2.5)), 4), round(float(np.percentile(r, 97.5)), 4)]


def evaluate(df: pd.DataFrame, p_col: str, odds_col: str, comm: float, gates: dict, rng) -> dict:
    """Favourite-side only (P >= 0.5 by construction of the gate); df has p_<side>, odds_<side>, won_<side> per side a/b."""
    rows = []
    for s in ("a", "b"):
        x = pd.DataFrame({"match_id": df.match_id, "year": df.year, "p": df[f"{p_col}_{s}"], "odds": df[f"{odds_col}_{s}"],
                          "won": df[f"won_{s}"]})
        rows.append(x)
    x = pd.concat(rows).dropna(subset=["p", "odds"])
    x = x[(x.odds > 1.0)]
    x["net_ev"] = x.p * (x.odds - 1) * (1 - comm) - (1 - x.p)
    x["pnl"] = np.where(x.won == 1, (x.odds - 1) * (1 - comm), -1.0)
    fav = x[x.p >= gates["min_probability"]]
    q = fav[(fav.net_ev >= gates["min_net_ev"]) & (fav.odds >= gates["min_decimal_odds"])]

    def summ(g: pd.DataFrame) -> dict:
        return {"n": int(len(g)), "win_rate": round(float(g.won.mean()), 4) if len(g) else None,
                "avg_p": round(float(g.p.mean()), 4) if len(g) else None,
                "avg_odds": round(float(g.odds.mean()), 3) if len(g) else None,
                "mean_est_net_ev": round(float(g.net_ev.mean()), 4) if len(g) else None,
                "realised_units": round(float(g.pnl.sum()), 2), "roi": round(float(g.pnl.mean()), 4) if len(g) else None,
                "roi_ci95": boot(g.pnl.values, rng)}
    return {"matches_priced": int(x.match_id.nunique()), "favourites": int(len(fav)),
            "favourites_positive_ev": int((fav.net_ev > 0).sum()), "qualifying": int(len(q)),
            "qualifying_per_100_matches": round(100 * len(q) / max(1, x.match_id.nunique()), 3),
            "odds_distribution_favourites": {k: round(float(v), 3) for k, v in fav.odds.describe(percentiles=[.1, .5, .9]).items()},
            "qualifying_summary": summ(q), "qualifying_by_year": {int(k): summ(g) for k, g in q.groupby("year")},
            "all_favourites_no_value_filter": summ(fav)}


def build(tour: str, td: pd.DataFrame, ours: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    links, stats = link(ours[["match_id", "date", "player_a_name", "player_b_name"]], td)
    m = ours.merge(links, on="match_id").merge(td, left_on="td_row", right_on="td_row")
    # integrity: our outcome must agree with tennis-data's winner
    ours_a_won = m.outcome_a_won.astype(int)
    agree = (ours_a_won == (m.td_winner_side == "A").astype(int))
    out = {"our_rows": int(len(ours)), "link_stats": dict(stats), "winner_agreement": round(float(agree.mean()), 5),
           "winner_disagreements_excluded": int((~agree).sum())}
    m = m[agree].copy()
    comp = m.Comment.astype(str).str.lower()
    completed = comp.str.startswith("completed")
    out["excluded_retired_or_walkover"] = int((~completed).sum())
    m = m[completed].copy()
    a_is_w = m.td_winner_side == "A"
    for tag, (cw, cl) in {"b365": ("B365W", "B365L"), "ps": ("PSW", "PSL"), "bfe": ("BFEW", "BFEL")}.items():
        if cw not in m:
            m[f"{tag}_a"] = m[f"{tag}_b"] = np.nan
            continue
        m[f"{tag}_a"] = np.where(a_is_w, m[cw], m[cl])
        m[f"{tag}_b"] = np.where(a_is_w, m[cl], m[cw])
    m["won_a"], m["won_b"] = a_is_w.astype(int), (~a_is_w).astype(int)
    m["pT30_a"] = m.p_a_market_multiplicative
    m["pT30_b"] = 1 - m.p_a_market_multiplicative
    ok_ps = (m.ps_a > 1) & (m.ps_b > 1)
    m["pPS_a"] = np.where(ok_ps, mult(m.ps_a, m.ps_b), np.nan)
    m["pPS_b"] = 1 - m.pPS_a
    ok_bfe = (m.bfe_a > 1) & (m.bfe_b > 1)
    m["pBFE_a"] = np.where(ok_bfe, mult(m.bfe_a, m.bfe_b), np.nan)
    m["pBFE_b"] = 1 - m.pBFE_a
    # POST-HOC DATA-VALIDITY SCREEN (disclosed amendment A1 to the pre-registration, added after the first run exposed
    # corrupt rows such as B365W=29.0 / B365L=0.967): generic sanity only, no reference to other books, no betting rule.
    ob = 1 / m.b365_a + 1 / m.b365_b
    m["b365_valid"] = (m.b365_a > 1.01) & (m.b365_b > 1.01) & (ob >= 0.98) & (ob <= 1.20)
    out["b365_rows_failing_validity_screen"] = int((~m.b365_valid & m.b365_a.notna()).sum())
    out["matched_completed_by_year"] = {int(k): int(v) for k, v in m.groupby("year").size().items()}
    out["price_coverage"] = {c: round(float(m[f"{c}_a"].notna().mean()), 4) for c in ("b365", "ps", "bfe")}
    return m, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--td-dir", type=Path, required=True)
    ap.add_argument("--atp-canonical", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=REPO / "research/platform_v2/historical_v2_6h")
    a = ap.parse_args()
    gates = load_config()["decision_gates"]["paper_bet"]
    res: dict = {"label": LABEL, "rule_version": load_config()["rule_version"],
                 "preregistration": "research/platform_v2/historical_v2_6h/V2_6D_CLOSING_DIAGNOSTIC_PREREGISTRATION.md"}
    atp = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv")
    names = pd.read_csv(a.atp_canonical, usecols=["match_id", "player_a_name", "player_b_name"])
    atp = atp.merge(names, on="match_id", how="left")
    wta = pd.read_csv(REPO / "data/interim/v2_wta_market_dataset.csv")
    for tour, ours in (("ATP", atp), ("WTA", wta)):
        rng = np.random.default_rng(SEED)
        ours = ours.dropna(subset=["p_a_market_multiplicative", "outcome_a_won", "player_a_name", "player_b_name"]).copy()
        ours["date"] = pd.to_datetime(ours.scheduled_start.str[:10])
        m, info = build(tour, load_td(a.td_dir, tour), ours)
        r = {"linkage": info}
        raw = m
        m = m[m.b365_valid]
        r["V1_MISALIGNED_frozenT30_vs_B365close__RAW_UNSCREENED"] = evaluate(raw, "pT30", "b365", 0.0, gates, rng)
        r["V1_MISALIGNED_frozenT30_vs_B365close"] = evaluate(m, "pT30", "b365", 0.0, gates, rng)
        # sensitivity: drop matches where the T-30 Betfair P and the Pinnacle close disagree by > 0.10 (stale or possibly
        # in-play-contaminated LTP when a match started earlier than scheduled) -- descriptive only
        near = m[(m.pT30_a - m.pPS_a).abs() <= 0.10]
        r["V1_sensitivity_T30_within_0.10_of_PSclose"] = evaluate(near, "pT30", "b365", 0.0, gates, rng)
        r["V2_ALIGNED_BFEclose_vs_B365close_2025"] = evaluate(m[m.pBFE_a.notna()], "pBFE", "b365", 0.0, gates, rng)
        r["V3_ALIGNED_PSclose_vs_B365close_REFERENCE"] = evaluate(m[m.pPS_a.notna()], "pPS", "b365", 0.0, gates, rng)
        r["selfcheck_BFEclose_vs_BFEclose_5pct"] = evaluate(m[m.pBFE_a.notna()], "pBFE", "bfe", 0.05, gates, rng)
        d_ps = (m.pT30_a - m.pPS_a).abs().dropna()
        d_bfe = (m.pT30_a - m.pBFE_a).abs().dropna()
        r["time_mismatch_sensitivity"] = {
            "abs_diff_T30_vs_PSclose": {k: round(float(v), 4) for k, v in d_ps.describe(percentiles=[.5, .9]).items()},
            "abs_diff_T30_vs_BFEclose_2025": {k: round(float(v), 4) for k, v in d_bfe.describe(percentiles=[.5, .9]).items()}}
        # V1 'value' selections: did the aligned closing reference agree it was value?
        v1 = []
        for s in ("a", "b"):
            x = m[(m[f"pT30_{s}"] >= 0.5)].copy()
            ev = x[f"pT30_{s}"] * (x[f"b365_{s}"] - 1) - (1 - x[f"pT30_{s}"])
            x = x[(ev >= gates["min_net_ev"]) & (x[f"b365_{s}"] >= gates["min_decimal_odds"])]
            ev_ps = x[f"pPS_{s}"] * (x[f"b365_{s}"] - 1) - (1 - x[f"pPS_{s}"])
            v1.append(pd.DataFrame({"moved_against": (x[f"pPS_{s}"] < x[f"pT30_{s}"]), "still_value_vs_PS": ev_ps >= gates["min_net_ev"],
                                    "has_ps": x[f"pPS_{s}"].notna()}))
        v = pd.concat(v1)
        v = v[v.has_ps]
        r["V1_value_bets_vs_closing_reference"] = {"n_with_PS": int(len(v)),
                                                   "share_where_close_moved_against_selection": round(float(v.moved_against.mean()), 4) if len(v) else None,
                                                   "share_still_value_vs_PS_close": round(float(v.still_value_vs_PS.mean()), 4) if len(v) else None}
        res[tour] = r
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "V2_6D_CLOSING_DIAGNOSTIC_RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
