"""Phase V2-2 -- build the WTA 2021-2025 market/Elo dataset (data assembly only).

Prints availability counts only -- never an outcome-linked statistic. See
research/platform_v2/wta/WTA_PROTOCOL.md.
"""
from __future__ import annotations

import glob
import hashlib
import math
import pickle
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from prediction_markets_lab.models.tennis_elo import EloConfig, EloMatchInput, global_rating_key, run_elo_over_matches  # noqa: E402
from prediction_markets_lab.normalisation.tennis_betfair_linkage import (  # noqa: E402
    BetfairEventCandidate, TMLMatchRecord, _fold, classify_tennis_betfair_match, names_are_equivalent)
from prediction_markets_lab.research.market_observation import latest_price_at_or_before  # noqa: E402
from prediction_markets_lab.research import margin_removal_methods as mrm  # noqa: E402

RAW = REPO / "data/raw/tennis/tennis_court_log_wta"
CHUNKS = Path.home() / "bf_all"
OUT = REPO / "data/interim/v2_wta_market_dataset.csv"
OUT_LINK = REPO / "data/interim/v2_wta_linkage.csv"
ROUND_ORDER = {"RR": 0, "R128": 1, "R64": 2, "R32": 3, "R16": 4, "QF": 5, "SF": 6, "BR": 7, "F": 8}
DATE_TOLERANCE_DAYS = 14
HORIZON_MIN = 30
FRESH_CAP_S = 3600
K_GRID = (16.0, 24.0, 32.0, 40.0, 48.0, 64.0)
WARMUP = (2018, 2019, 2020)
TRAIN = (2021, 2022, 2023)
LEVEL_MAP = {"I": "250/International", "WTA250": "250/International", "WTA 250": "250/International",
             "P": "500/Premier", "WTA500": "500/Premier", "WTA 500": "500/Premier",
             "PM": "1000/Premier Mandatory", "WTA1000": "1000/Premier Mandatory", "WTA 1000": "1000/Premier Mandatory",
             "Grand Slam": "Grand Slam", "F": "Finals", "WTA Finals": "Finals", "D": "Team (BJK/United Cup)",
             "O": "Olympics", "W": "Other"}


def load_results() -> pd.DataFrame:
    frames = []
    for f in sorted(RAW.glob("wta_matches_*.csv")):
        d = pd.read_csv(f)
        d["season"] = int(f.stem[-4:])
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["tourney_date"] = pd.to_datetime(d.tourney_date.astype(str).str.replace("/", "-"))
    sc = d.score.astype(str)
    d["walkover"] = sc.str.contains(r"W/O|\bWO\b", case=False, regex=True)
    d["retired"] = sc.str.contains("RET", case=False)
    d = d[~d.walkover & d.winner_name.notna() & d.loser_name.notna()].copy()
    d["w"], d["l"] = d.winner_name.map(_fold), d.loser_name.map(_fold)
    d["player_a_name"] = [w_ if a < b else l_ for a, b, w_, l_ in zip(d.w, d.l, d.winner_name, d.loser_name)]
    d["player_b_name"] = [l_ if a < b else w_ for a, b, w_, l_ in zip(d.w, d.l, d.winner_name, d.loser_name)]
    d["outcome_a_won"] = (d.w < d.l).astype(int)
    d["level"] = d.tourney_level.map(LEVEL_MAP).fillna("Other")
    d["_round_order"] = d["round"].map(ROUND_ORDER).fillna(-1)
    d = d.sort_values(["tourney_date", "_round_order", "tourney_name", "winner_name"]).reset_index(drop=True)
    d["match_id"] = [f"WTA-{s}-{i:05d}" for i, s in enumerate(d.season)]
    return d


def elo(d: pd.DataFrame) -> tuple[dict, float, dict]:
    inputs = [EloMatchInput(match_id=r.match_id, match_date=r.tourney_date.date(),
                            surface=r.surface if isinstance(r.surface, str) else "Unknown",
                            player_a_id=_fold(r.player_a_name), player_b_id=_fold(r.player_b_name),
                            outcome_a_won=int(r.outcome_a_won)) for r in d.itertuples()]
    train_ids = set(d[d.season.isin(TRAIN)].match_id)
    scores = {}
    for k in K_GRID:
        preds = run_elo_over_matches(inputs, EloConfig(initial_rating=1500.0, k_factor=k), global_rating_key)
        y = dict(zip(d.match_id, d.outcome_a_won))
        ll = [-math.log(max(p.p_a_win if y[p.match_id] else 1 - p.p_a_win, 1e-15)) for p in preds if p.match_id in train_ids]
        scores[k] = sum(ll) / len(ll)
    best = min(scores, key=scores.get)
    preds = run_elo_over_matches(inputs, EloConfig(initial_rating=1500.0, k_factor=best), global_rating_key)
    return {p.match_id: p.p_a_win for p in preds}, best, scores


def main() -> None:
    d = load_results()
    print("result rows (non-walkover)", len(d), d.groupby("season").size().to_dict())
    elo_p, k, k_scores = elo(d)
    print("Elo k chosen on 2021-23 log loss:", k)
    markets, digest = {}, hashlib.sha256()
    for p in sorted(CHUNKS.glob("chunk_*.pkl")):
        for r in pickle.load(open(p, "rb")):
            if r["n_price_points"] > 0 and r["final_market_time"]:
                markets[r["market_id"]] = r
                digest.update(r["raw_sha256"].encode())
    print("singles MATCH_ODDS with prices", len(markets), "source hash", digest.hexdigest()[:16])
    pair_index = defaultdict(list)
    for m in markets.values():
        n = m["runner_names"]
        if None in n:
            continue
        pair_index[frozenset({_fold(n[0]), _fold(n[1])})].append(BetfairEventCandidate(
            market_id=m["market_id"], event_id=m["event_id"],
            event_open_date=datetime.fromisoformat(m["final_market_time"]).date(), runner_names=(n[0], n[1])))
    ev = d[d.season >= 2021]
    link_rows, rows = [], []
    status_by_year = defaultdict(lambda: defaultdict(int))
    for r in ev.itertuples():
        tml = TMLMatchRecord(match_id=r.match_id, match_date=r.tourney_date.date(),
                             player_a_name=r.player_a_name, player_b_name=r.player_b_name)
        res = classify_tennis_betfair_match(tml, pair_index.get(frozenset({_fold(r.player_a_name), _fold(r.player_b_name)}), []),
                                            date_tolerance_days=DATE_TOLERANCE_DAYS)
        status_by_year[r.season][res.status] += 1
        link_rows.append({"match_id": r.match_id, "status": res.status, "market_id": res.matched_market_id})
        if res.status != "MATCHED":
            continue
        m = markets[res.matched_market_id]
        sel = {}
        for rid, nm in zip(m["runner_ids"], m["runner_names"]):
            if names_are_equivalent(r.player_a_name, nm):
                sel["a"] = int(rid)
            elif names_are_equivalent(r.player_b_name, nm):
                sel["b"] = int(rid)
        if len(sel) != 2:
            status_by_year[r.season]["runner_map_failed"] += 1
            continue
        start = datetime.fromisoformat(m["final_market_time"])
        cut = start - timedelta(minutes=HORIZON_MIN)
        ser = defaultdict(list)
        for rid, ltp, ep in zip(m["price_runner_ids"], m["price_ltp"], m["price_epoch_ms"]):
            if ep is not None and ltp is not None:
                ser[int(rid)].append((datetime.fromtimestamp(ep / 1000, tz=timezone.utc), float(ltp)))
        pa_ = latest_price_at_or_before(sorted(ser[sel["a"]]), cut)
        pb_ = latest_price_at_or_before(sorted(ser[sel["b"]]), cut)
        if pa_ is None or pb_ is None or max((cut - pa_[0]).total_seconds(), (cut - pb_[0]).total_seconds()) > FRESH_CAP_S \
                or pa_[1] <= 1.0 or pb_[1] <= 1.0:
            status_by_year[r.season]["stale_or_missing"] += 1
            continue
        rec = {"match_id": r.match_id, "year": r.season, "tourney_date": r.tourney_date.date().isoformat(),
               "tourney_name": r.tourney_name, "level": r.level, "surface": r.surface, "round": r.round,
               "retired": bool(r.retired), "player_a_name": r.player_a_name, "player_b_name": r.player_b_name,
               "market_id": m["market_id"], "scheduled_start": m["final_market_time"], "ltp_a": pa_[1], "ltp_b": pb_[1],
               "raw_sha256": m["raw_sha256"], "outcome_a_won": int(r.outcome_a_won), "p_a_elo_global": elo_p.get(r.match_id)}
        for meth in mrm.METHODS:
            rec[f"p_a_market_{meth}"] = mrm.devig([pa_[1], pb_[1]], meth)[0]
        rows.append(rec)
    pd.DataFrame(link_rows).to_csv(OUT_LINK, index=False)
    out = pd.DataFrame(rows).sort_values(["scheduled_start", "match_id"])
    out.to_csv(OUT, index=False)
    print("linkage/pricing by season:", {s: dict(v) for s, v in sorted(status_by_year.items())})
    print("dataset rows", len(out), out.groupby("year").size().to_dict())
    print("k grid log loss (training, a model-fit diagnostic, not a market/outcome result):", {k_: round(v, 4) for k_, v in k_scores.items()})


if __name__ == "__main__":
    main()
