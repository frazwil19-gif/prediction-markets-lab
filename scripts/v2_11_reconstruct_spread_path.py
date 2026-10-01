"""V2-11 diagnostic: bsv2-3 (actual) vs bsv2-4 (ledger-path spread correction) on every bsv2-3 production run.

Read-only: inputs via `git show` at each production commit; no outcomes; 0 API calls; nothing in the repo's ledgers,
prospective V2-7 files or reports is written.
  A  = actual historical implementation (bsv2-3; old start filter). Must reproduce the committed candidates CSV exactly.
  B  = bsv2-4 on the same universe (isolates the spread correction).
  C  = bsv2-4 + est-1 universe (the full post-V2-10 pipeline), for the two 30 Sep scans.
Output: research/platform_v2/v2_11_spread_gate_ledger_path/RECONSTRUCTION.json
"""
from __future__ import annotations

import csv
import dataclasses
import importlib.util
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import evaluate_prediction, load_config as load_bs
from prediction_markets_lab.prediction_platform import event_times as ET
from prediction_markets_lab.prediction_platform import stage_a as SA

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/v2_11_spread_gate_ledger_path/RECONSTRUCTION.json"
LEDGER_ORIGIN = "unified_ledger.live_price"
RUNS = {  # label: (production commit, evaluated_at from the committed candidates CSV)
    "2026-09-29T20:11": ("896cdbf", "2026-09-29T20:11:51.841749+00:00"),
    "2026-09-30T12:54 (morning)": ("e9cc1a4", "2026-09-30T12:54:25.206146+00:00"),
    "2026-09-30T13:26 (daily scan)": ("a893041", "2026-09-30T13:26:36.200034+00:00"),
    "2026-09-30T20:16 (afternoon)": ("7e3ce99", "2026-09-30T20:16:18.937926+00:00"),
}


def show(c: str, path: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{c}:{path}"], text=True)


def rows(c: str, path: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(show(c, path))))


def latest_card(c: str) -> dict | None:
    names = subprocess.check_output(["git", "-C", str(REPO), "ls-tree", "--name-only", c, "daily_cards/"], text=True).split()
    for d in sorted(names, reverse=True):
        try:
            return json.loads(show(c, f"{d}/card.json"))
        except subprocess.CalledProcessError:
            continue
    return None


def snapshots(p: dict, price: list[dict], prob: list[dict], card: dict | None, bsv2_3: bool) -> list[PR.PriceSnapshot]:
    own = PR.from_ledger_row(p, prob)
    if own and bsv2_3:   # the bsv2-3 ledger path carried no engine source / spread
        own = dataclasses.replace(own, p_same_spread=None, p_same_source=None)
    return ([own] if own else []) + PR.tennis_from_snapshots(p, price, prob) + (PR.football_from_card(p, card) if card else [])


def main() -> int:
    cfg = load_bs()
    sa_cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    cal = SA.calibration_se(sa_cfg.calibration_results)
    out: dict = {"label": "V2-11 diagnostic; read-only; no outcomes; production inputs via git show",
                 "rule_versions": {"A": "bsv2-3 (actual)", "B": "bsv2-4 (proposed)"}, "runs": {}}
    for label, (c, at) in RUNS.items():
        now = PR.ts(at)
        preds, prob = rows(c, "predictions/unified_ledger.csv"), rows(c, "tennis_predictions/exchange_probability_snapshots.csv")
        price, card = rows(c, "tennis_predictions/price_snapshots.csv"), latest_card(c)
        universe = [p for p in preds if PR.ts(p["event_start"]) > now]
        dec = {}
        for mode in ("A", "B"):
            dec[mode] = {p["prediction_id"]: evaluate_prediction(p, snapshots(p, price, prob, card, mode == "A"), cfg, now)
                         for p in universe}
        prod = {r["prediction_id"]: r for r in rows(c, "reports/bet_selection_v2_candidates.csv")}
        a_ok = set(prod) == set(dec["A"]) and all(prod[k]["decision"] == v[0].decision and prod[k]["reasons"] == "|".join(v[0].reasons)
                                                   for k, v in dec["A"].items())
        changes = []
        for k, (a, _ca) in dec["A"].items():
            b, cb = dec["B"][k]
            if (a.decision, a.reasons, a.source) != (b.decision, b.reasons, b.source):
                led = [x for x in cb if x.price_origin == LEDGER_ORIGIN]
                changes.append({"prediction_id": k, "event": a.event_name, "selection": a.selection,
                                "A": {"decision": a.decision, "reasons": a.reasons, "source": a.source, "origin": a.price_origin,
                                      "net_ev": a.net_ev},
                                "B": {"decision": b.decision, "reasons": b.reasons, "source": b.source, "origin": b.price_origin,
                                      "net_ev": b.net_ev},
                                "ledger_quote_B_reasons": led[0].reasons if led else None})
        # every ledger-path quote in this run: was its bsv2-3 treatment ever decision-bearing, and its EV range
        led_a = [x for _, (_, cs) in dec["A"].items() for x in cs if x.price_origin == LEDGER_ORIGIN and x.net_ev is not None]
        led_b = [x for _, (_, cs) in dec["B"].items() for x in cs if x.price_origin == LEDGER_ORIGIN]
        bsel = [(k, v[0]) for k, v in dec["A"].items() if v[0].decision == "PAPER_BET"]
        count = lambda m: dict(Counter(v[0].decision for v in dec[m].values()))                     # noqa: E731
        qual = lambda m: sum(bool({"EXCHANGE_SPREAD_TOO_WIDE", "EXCHANGE_SPREAD_UNKNOWN"} & set(v[0].reasons))  # noqa: E731
                             for v in dec[m].values())
        r = {"production_commit": c, "evaluated_at": at, "universe": len(universe),
             "A_reproduces_production_exactly": a_ok,
             "decisions_A": count("A"), "decisions_B": count("B"),
             "spread_quality_failures_on_decided_A": qual("A"), "spread_quality_failures_on_decided_B": qual("B"),
             "paper_bets_A": [{"prediction_id": k, "event": v.event_name, "source": v.source, "origin": v.price_origin}
                              for k, v in bsel],
             "paper_bets_B": [{"prediction_id": k, "event": v[0].event_name, "source": v[0].source}
                              for k, v in dec["B"].items() if v[0].decision == "PAPER_BET"],
             "decided_on_ledger_path_A": sum(v[0].price_origin == LEDGER_ORIGIN for v in dec["A"].values()),
             "ledger_path_quotes": len(led_a),
             "ledger_path_net_ev_max_A": max((x.net_ev for x in led_a), default=None),
             "ledger_path_quotes_resolved_B": sum(x.reasons.count("EXCHANGE_SPREAD_UNKNOWN") == 0 for x in led_b),
             "ledger_path_B_reason_counts": dict(Counter(rr for x in led_b for rr in x.reasons
                                                         if rr.startswith("EXCHANGE_SPREAD") or rr in ("PRICE_STALE",))),
             "changed_predictions": changes}
        if "30T12:54" in label or "30T20:16" in label:   # C: full post-V2-10 pipeline + Stage A
            idx = ET.StartIndex()
            for rel in ET.TENNIS_START_SOURCES:
                idx.add_tennis_rows(rows(c, rel), rel)
            uni_c, _ = ET.apply(preds, idx, now)
            dc = {p["prediction_id"]: evaluate_prediction(p, snapshots(p, price, prob, card, False), cfg, now)[0] for p in uni_c}
            board = SA.build(uni_c, prob, lambda p: snapshots(p, price, prob, card, False), cfg, sa_cfg, cal, now)
            r["C_est1_plus_bsv2_4"] = {"universe": len(uni_c), "decisions": dict(Counter(v.decision for v in dc.values())),
                                       "paper_bets": sum(v.decision == "PAPER_BET" for v in dc.values()),
                                       "stage_a_summary": board["summary"]}
        out["runs"][label] = r
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))
    for k, r in out["runs"].items():
        print(k, json.dumps({x: y for x, y in r.items() if x != "changed_predictions"}, default=str))
        for ch in r["changed_predictions"]:
            print("   ", ch["event"][:36], ch["A"]["decision"], ch["A"]["reasons"], ch["A"]["origin"][:12], "=>",
                  ch["B"]["decision"], ch["B"]["reasons"], ch["B"]["source"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
