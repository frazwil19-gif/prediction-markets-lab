"""V2-7 OFFLINE research card logger (cer-1). Not wired into any workflow. Writes only under
research/platform_v2/card_engine_v2_7/shadow_cards/.

  log      all scans present in the live same-scan files -> research cards (idempotent)
  settle   settle logged cards from the verified tennis settlement ledger (fail closed)
  summary  counts, representative cards, singles-vs-card equal-capital comparison
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.card_engine import RULE_VERSION
from prediction_markets_lab.card_engine import cards as C
from prediction_markets_lab.card_engine import io as IO

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/card_engine_v2_7/shadow_cards"
PROB = REPO / "tennis_predictions/exchange_probability_snapshots.csv"
PRICE = REPO / "tennis_predictions/price_snapshots.csv"
RESULTS = REPO / "research/platform_v2/card_engine_v2_7/RESULTS.json"
STAKES = (0.01, 0.02, 0.05)


def cal_se_fn():
    """Per-band calibration SE from the V2-7 A1 tennis holdout singles (conservative: the larger of ATP/WTA)."""
    r = json.loads(RESULTS.read_text())["A1_joint_calibration"]
    se = {}
    for band in ("50-65%", "65-80%", "80%+"):
        vals = []
        for sp in ("tennis_atp", "tennis_wta"):
            b = r[sp]["holdout_years"]["singles"].get(band)
            if b:
                vals.append((b["wilson95"][1] - b["wilson95"][0]) / (2 * 1.96))
        se[band] = max(vals)
    return lambda p: se["80%+"] if p >= 0.80 else se["65-80%"] if p >= 0.65 else se["50-65%"]


def log(now: datetime) -> dict:
    prob, price = IO._read(PROB), IO._read(PRICE)
    scans = sorted({r["scan_timestamp_utc"] for r in prob})
    cal = cal_se_fn()
    prov = {"prob_file_sha": IO.file_sha(PROB), "price_file_sha": IO.file_sha(PRICE), "rule": RULE_VERSION,
            "calibration_source": "V2-7 A1 tennis holdout singles (RESULTS.json)", "results_sha": IO.file_sha(RESULTS)}
    total, spaces = 0, {}
    for scan in scans:
        legs = IO.load_legs(prob, price, scan)
        cards, space = C.enumerate_cards(RULE_VERSION, legs, cal)
        spaces[scan] = {"legs": len(legs), "space": space}
        total += IO.append_unique(OUT / "cards.csv", IO.CARD_FIELDS, "card_id",
                                  [IO.card_row(c, now.isoformat(), prov) for c in cards])
    (OUT / "search_space.json").write_text(json.dumps(spaces, indent=1))
    print(f"scans {len(scans)} | new cards {total}")
    return spaces


def settle(now: datetime) -> int:
    cards = IO._read(OUT / "cards.csv")
    done = {r["card_id"] for r in IO._read(OUT / "card_settlements.csv")}
    rows = IO.settle(cards, IO._read(REPO / "tennis_predictions/ledger_predictions.csv"),
                     IO._read(REPO / "tennis_predictions/ledger_settlements.csv"), done, now)
    n = IO.append_unique(OUT / "card_settlements.csv", IO.SETTLE_FIELDS, "card_id", rows)
    print(f"settled {n}")
    return n


def summary() -> dict:
    cards = IO._read(OUT / "cards.csv")
    sett = {r["card_id"]: r for r in IO._read(OUT / "card_settlements.csv")}
    out = {"label": "RESEARCH ONLY (class D shadow). Odds INDICATIVE / NOT EXECUTION-VERIFIED. Not paper bets.",
           "cards": len(cards),
           "by_group_k_status": dict(Counter(f"{c['group']}|k={c['k']}|{c['status']}" for c in cards)),
           "unique_leg_sets_by_k": {k: len({tuple(sorted((l["event_id"], l["selection"]) for l in json.loads(c["legs_json"])))
                                             for c in cards if int(c["k"]) == k}) for k in (1, 2, 3)},
           "settled": dict(Counter(s["status"] for s in sett.values()))}
    # representative cards + equal-capital comparison, from the SHADOW pool (all legs +EV, clean) and the best HIGH_P cards
    def legs_of(c):
        return tuple(C.Leg(**{**l, "quality": tuple(l["quality"])}) for l in json.loads(c["legs_json"]))
    reps = []
    for grp, st in ((C.POS_EV, None), (C.HIGH_P, None)):
        for k in (1, 2, 3):
            pool = [c for c in cards if c["group"] == grp and int(c["k"]) == k and c["ev"] != "" and c["all_legs_clean"] == "True"]
            if not pool:
                continue
            c = max(pool, key=lambda c: float(c["ev"]))
            L = legs_of(c)
            reps.append({"group": grp, "k": k, "card_id": c["card_id"], "status": c["status"], "book": c["book"],
                         "legs": [f"{l.selection} ({l.event_name}) P={l.p:.3f} @ {l.odds} EV={l.ev:+.3f}" for l in L],
                         "p_joint": float(c["p_joint"]), "sigma_joint": float(c["sigma_joint"]),
                         "odds_indicative": float(c["odds_indicative"]), "ev": float(c["ev"]),
                         "ev_range_1sigma": [float(c["ev_low"]), float(c["ev_high"])],
                         "equal_capital": [C.equal_capital(L, s) for s in STAKES] if k > 1 else None})
    out["representative_best_ev_cards"] = reps
    (OUT / "summary.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["log", "settle", "summary"])
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    {"log": lambda: log(now), "settle": lambda: settle(now), "summary": summary}[a.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
