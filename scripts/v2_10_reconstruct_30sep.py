"""V2-10 diagnostic reconstruction of the two 30 Sep 2026 live scans under fix A (est-1) and fix B (stage-a-1).

Read-only: every input is read with `git show` at the exact production commit; nothing in the repo's ledgers,
prospective V2-7 files or reports is written. No outcomes are read. 0 API calls.
Output: research/platform_v2/v2_10_fixes/RECONSTRUCTION_30SEP.json
"""
from __future__ import annotations

import csv
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
OUT = REPO / "research/platform_v2/v2_10_fixes/RECONSTRUCTION_30SEP.json"
# V2-7 prospective files are NOT read or reinterpreted here; the V2-7 HIGH_P counts (16 / 17) are quoted from the V2-9 audit.
SCANS = {  # production commit, V2-7 shadow commit (provenance only), scan timestamp, bet-selection run time (evaluation_runs.csv)
    "morning": ("e9cc1a4", "5c4db9d", "2026-09-30T12:54:22.695202+00:00", "2026-09-30T12:54:25.206146+00:00", "2026-09-29"),
    "afternoon": ("7e3ce99", "18f0747", "2026-09-30T20:16:17.495727+00:00", "2026-09-30T20:16:18.937926+00:00", "2026-09-30"),
}


def show(commit: str, path: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"], text=True)


def rows(commit: str, path: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(show(commit, path))))


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / f"scripts/{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main() -> int:
    bs_script = load_script("run_bet_selection_v2")
    bs_cfg = load_bs()
    sa_cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    cal = SA.calibration_se(sa_cfg.calibration_results)
    out = {"label": "V2-10 diagnostic reconstruction; read-only; no outcomes; production inputs via git show", "scans": {}}
    for name, (prod, _shadow_commit, scan, run_at, card_day) in SCANS.items():
        now = ET.parse_ts(run_at)
        preds = rows(prod, "predictions/unified_ledger.csv")
        prob = rows(prod, "tennis_predictions/exchange_probability_snapshots.csv")
        price = rows(prod, "tennis_predictions/price_snapshots.csv")
        card = json.loads(show(prod, f"daily_cards/{card_day}/card.json"))
        idx = ET.StartIndex()
        for rel in ET.TENNIS_START_SOURCES:
            idx.add_tennis_rows(rows(prod, rel), rel)
        old_up = [p for p in preds if PR.ts(p["event_start"]) > now]
        new_up, res = ET.apply(preds, idx, now)

        def decide(universe):
            return {p["prediction_id"]: evaluate_prediction(p, bs_script.gather_snapshots(p, price, card, prob), bs_cfg, now)[0]
                    for p in universe}
        old_dec, new_dec = decide(old_up), decide(new_up)
        prod_cands = {r["prediction_id"]: r for r in rows(prod, "reports/bet_selection_v2_candidates.csv")}
        harness_ok = set(prod_cands) == set(old_dec) and all(
            prod_cands[k]["decision"] == c.decision and prod_cands[k]["reasons"] == "|".join(c.reasons) for k, c in old_dec.items())
        unchanged_existing = all(new_dec[k].decision == c.decision and new_dec[k].reasons == c.reasons for k, c in old_dec.items())
        restored = [k for k in new_dec if k not in old_dec]

        def snaps_for(p):
            own = PR.from_ledger_row(p)
            return ([own] if own else []) + PR.tennis_from_snapshots(p, price, prob) + PR.football_from_card(p, card)
        board = SA.build(new_up, prob, snaps_for, bs_cfg, sa_cfg, cal, now)
        strong = [r for r in board["predictions"] if r["strength"] == SA.STRONG]
        # the V2-9 scan board (validated same-scan favourite P >= 0.70) for comparison
        scan_rows = [r for r in prob if r["scan_timestamp_utc"] == scan and r["source_validated"] == "True"]
        scan_strong = {r["event_id"] for r in scan_rows if max(float(r["p_a"]), float(r["p_b"])) >= sa_cfg.strong_min_probability}
        strong_events = {r["event_key"].split("|")[-1] for r in strong}
        rescheduled = [r for r in res if r["start_time_status"] == ET.RESCHEDULED]
        out["scans"][name] = {
            "production_commit": prod, "scan": scan, "evaluated_at": run_at,
            "start_time_resolution": ET.summary(res),
            "universe_old_filter": len(old_up), "universe_est_1": len(new_up),
            "unique_events_old": len({p["event_key"] for p in old_up}), "unique_events_est_1": len({p["event_key"] for p in new_up}),
            "harness_reproduces_production_bsv2_3_exactly": harness_ok,
            "existing_candidates_unchanged": unchanged_existing,
            "restored_predictions": [{"prediction_id": k, "event": new_dec[k].event_name, "selection": new_dec[k].selection,
                                      "event_start_original": next(r["event_start_original"] for r in res if r["prediction_id"] == k),
                                      "event_start_current": new_dec[k].event_start, "p": round(new_dec[k].probability, 4),
                                      "best_source": new_dec[k].source, "best_odds": new_dec[k].decimal_odds,
                                      "net_ev": None if new_dec[k].net_ev is None else round(new_dec[k].net_ev, 4),
                                      "decision": new_dec[k].decision, "reasons": new_dec[k].reasons} for k in restored],
            "stage_b_decisions_old": dict(Counter(c.decision for c in old_dec.values())),
            "stage_b_decisions_est_1": dict(Counter(c.decision for c in new_dec.values())),
            "stage_b_paper_bets_old": sum(c.decision == "PAPER_BET" for c in old_dec.values()),
            "stage_b_paper_bets_est_1": sum(c.decision == "PAPER_BET" for c in new_dec.values()),
            "rescheduled_eligible": [{"event": r["event_name"], "original": r["event_start_original"], "current": r["event_start_current"]}
                                     for r in rescheduled if r["eligibility"] == ET.ELIGIBLE],
            "stage_a_summary": board["summary"],
            "stage_a_strong": [{k: r[k] for k in ("rank", "event_name", "selection", "probability", "sigma", "probability_basis",
                                                  "event_start", "start_time_status", "stage_a_label", "price_status_reasons",
                                                  "best_clean_source", "best_clean_odds", "best_clean_net_ev")} for r in strong],
            "scan_board_validated_strong_events": len(scan_strong),
            "stage_a_strong_events_in_scan_board": len(scan_strong & strong_events),
            "scan_board_strong_missing_from_stage_a": sorted(scan_strong - strong_events),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))
    for n, s in out["scans"].items():
        print(n, json.dumps({k: v for k, v in s.items() if k not in ("stage_a_strong", "restored_predictions", "rescheduled_eligible")}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
