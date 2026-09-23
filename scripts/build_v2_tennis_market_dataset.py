"""Phase V2-1 -- build the 2021-2025 ATP tennis market/Elo probability dataset.

Data assembly only: prints availability counts, never an outcome-linked statistic.
Inputs: canonical TML matches, Workstream B linkage, per-runner Betfair LTP series
re-extracted from Fraser's data.tar (pickled chunks in the VM home, each row carrying
the raw member's SHA-256), frozen Elo outputs (2021-23 discovery dataset, 2024 A4
predictions, 2025 holdout predictions). Output: data/interim/v2_tennis_market_dataset.csv
"""
from __future__ import annotations

import hashlib
import pickle
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from prediction_markets_lab.normalisation.tennis_betfair_linkage import names_are_equivalent  # noqa: E402
from prediction_markets_lab.research.market_observation import latest_price_at_or_before  # noqa: E402
from prediction_markets_lab.research import margin_removal_methods as mrm  # noqa: E402

CHUNKS = Path.home() / "bf_idx"
OUT = REPO / "data" / "interim" / "v2_tennis_market_dataset.csv"
HORIZON_MIN = 30
FRESH_CAP_S = max(2 * HORIZON_MIN * 60, 3600)  # identical to Workstream B's FRESH_CAP(30)


def main() -> None:
    markets = {}
    digest = hashlib.sha256()
    for p in sorted(CHUNKS.glob("chunk_*.pkl")):
        for r in pickle.load(open(p, "rb")):
            markets[r["market_id"]] = r
            digest.update(r["raw_sha256"].encode())
    print("markets loaded", len(markets), "combined source hash", digest.hexdigest()[:16])
    can = pd.read_csv(REPO / "data/processed/tennis/cycle_002_canonical_matches.csv", dtype={"tourney_date": str})
    can = can[~can.walkover].set_index("match_id")
    link = pd.read_csv(REPO / "data/interim/workstream_b_2021_2025_linkage.csv", dtype=str)
    link = link[link.linkage_status == "MATCHED"]
    elo = {}
    d = pd.read_csv(REPO / "data/interim/workstream_b_2021_2023_discovery_dataset.csv", usecols=["match_id", "elo_prob_a", "ranking_prob_a"])
    for r in d.itertuples():
        elo[r.match_id] = (r.elo_prob_a, r.ranking_prob_a)
    for f in ("cycle_002_tennis_a4_predictions.csv", "cycle_002_tennis_2025_holdout_predictions.csv"):
        x = pd.read_csv(REPO / "data/interim" / f)
        for r in x.itertuples():
            elo[r.match_id] = (r.global_elo_p_a_win, r.ranking_baseline_p_a_win)
    rows, skip = [], {"no_canonical": 0, "no_market": 0, "not_match_odds": 0, "runner_map": 0, "stale_or_missing": 0}
    for lk in link.itertuples():
        if lk.tml_match_id not in can.index:
            skip["no_canonical"] += 1
            continue
        m = markets.get(lk.matched_market_id)
        if m is None:
            skip["no_market"] += 1
            continue
        if m["market_type"] != "MATCH_ODDS" or not m["final_market_time"]:
            skip["not_match_odds"] += 1
            continue
        c = can.loc[lk.tml_match_id]
        sel_a = sel_b = None
        if len(m["runner_ids"]) == 2:
            for rid, nm in zip(m["runner_ids"], m["runner_names"]):
                if nm and names_are_equivalent(lk.player_a_name, nm):
                    sel_a = int(rid)
                elif nm and names_are_equivalent(lk.player_b_name, nm):
                    sel_b = int(rid)
        if sel_a is None or sel_b is None:
            skip["runner_map"] += 1
            continue
        start = datetime.fromisoformat(m["final_market_time"])
        cutoff = start - timedelta(minutes=HORIZON_MIN)
        ser: dict[int, list] = {}
        for rid, ltp, ep in zip(m["price_runner_ids"], m["price_ltp"], m["price_epoch_ms"]):
            if ep is not None and ltp is not None:
                ser.setdefault(int(rid), []).append((datetime.fromtimestamp(ep / 1000, tz=timezone.utc), float(ltp)))
        pa_ = latest_price_at_or_before(sorted(ser.get(sel_a, [])), cutoff)
        pb_ = latest_price_at_or_before(sorted(ser.get(sel_b, [])), cutoff)
        if pa_ is None or pb_ is None or max((cutoff - pa_[0]).total_seconds(), (cutoff - pb_[0]).total_seconds()) > FRESH_CAP_S \
                or pa_[1] <= 1.0 or pb_[1] <= 1.0:
            skip["stale_or_missing"] += 1
            continue
        rec = {"match_id": lk.tml_match_id, "year": int(str(c["tourney_date"])[:4]), "tourney_date": c["tourney_date"],
               "tourney_name": c["tourney_name"], "tourney_level": c["tourney_level"], "surface": c["surface"],
               "best_of": c["best_of"], "round": c["round"], "market_id": lk.matched_market_id,
               "scheduled_start": m["final_market_time"], "ltp_a": pa_[1], "ltp_b": pb_[1],
               "ltp_booksum": 1 / pa_[1] + 1 / pb_[1], "raw_sha256": m["raw_sha256"],
               "outcome_a_won": int(c["outcome_a_won"])}
        for meth in mrm.METHODS:
            rec[f"p_a_market_{meth}"] = mrm.devig([pa_[1], pb_[1]], meth)[0]
        e = elo.get(lk.tml_match_id, (None, None))
        rec["p_a_elo_global"], rec["p_a_ranking"] = e
        rows.append(rec)
    df = pd.DataFrame(rows).sort_values(["scheduled_start", "match_id"])
    df.to_csv(OUT, index=False)
    print("rows", len(df), "skips", skip)
    print(df.groupby("year").agg(n=("match_id", "size"), elo=("p_a_elo_global", lambda s: s.notna().sum())).to_string())


if __name__ == "__main__":
    main()
