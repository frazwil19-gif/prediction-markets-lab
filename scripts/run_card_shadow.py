"""V2-7 prospective SHADOW card logger (cer-2). RESEARCH ONLY. 0 Odds API credits (no network code at all).

  log            log the scan THIS workflow run produced (needs WORKFLOW_START); gated by logging_enabled
  settle         settle logged cards from the verified tennis settlement ledger; gated by settlement_enabled
  record-failure write an explicit failure record (e.g. research tests failed) so a missing scan is never a silent zero
  dry-run        replay one historical scan into a SCRATCH directory (never the prospective ledger), for verification

Writes only under the configured research output directory (enforced by ShadowStore). Exit code 1 on a research failure
(visible in the Actions log); the workflow step is continue-on-error and runs after production artefacts are committed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.card_engine import shadow as S
from prediction_markets_lab.card_engine import shadow_settle as SS

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config/card_research_shadow.yaml"


def cal_se_fn(results_path: Path):
    """Per-band calibration SE from the V2-7 A1 tennis holdout singles (the larger of ATP/WTA)."""
    r = json.loads(results_path.read_text())["A1_joint_calibration"]
    se = {}
    for band in ("50-65%", "65-80%", "80%+"):
        se[band] = max((b["wilson95"][1] - b["wilson95"][0]) / (2 * 1.96)
                       for sp in ("tennis_atp", "tennis_wta") if (b := r[sp]["holdout_years"]["singles"].get(band)))
    return lambda p: se["80%+"] if p >= 0.80 else se["65-80%"] if p >= 0.65 else se["50-65%"]


def provenance() -> dict:
    return {"run_id": os.environ.get("RUN_ID", ""), "commit_sha": os.environ.get("GITHUB_SHA", ""),
            "trigger": f"{os.environ.get('TRIGGER_EVENT', '')}:{os.environ.get('TRIGGER_SCHEDULE', '')}",
            "workflow_start": os.environ.get("WORKFLOW_START", ""),
            "production_tests": os.environ.get("PRODUCTION_TESTS", "")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["log", "settle", "record-failure", "dry-run"])
    ap.add_argument("--reason", default="")
    ap.add_argument("--scan", default="")
    ap.add_argument("--now", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--config", default=str(CONFIG))
    a = ap.parse_args(argv)
    cfg = S.load_config(Path(a.config), REPO)
    now = S.ts(a.now) if a.now else datetime.now(timezone.utc)
    prov = provenance()

    if a.command == "dry-run":
        if not a.out or not a.scan:
            print("dry-run needs --scan and --out (a scratch directory)")
            return 2
        out = Path(a.out).resolve()
        if out == (REPO / cfg.output_dir).resolve():
            print("dry-run refuses to write into the prospective ledger")
            return 2
        rec = S.run_shadow(REPO, cfg, S.ShadowStore(out), now, {**prov, "run_id": "DRY_RUN"}, "DRY_RUN_REPLAY",
                           cal_se_fn(REPO / cfg.inputs["calibration_results"]), None, scan_override=a.scan)
        print(json.dumps({k: rec.get(k) for k in ("status", "failure_reason", "scan", "legs_logged", "cards_logged")}))
        return 0 if rec["status"] in S.SUCCESS_STATUSES else 1

    store = S.ShadowStore(REPO / cfg.output_dir)
    if a.command == "record-failure":
        if not cfg.logging_enabled:
            print("card shadow logging disabled (config) -- nothing recorded")
            return 0
        status = a.reason if a.reason in (S.RESEARCH_TESTS_FAILED, S.PROD_TESTS_FAILED) else S.FAILED
        rec = S.scan_record(status, a.reason, "", "PROSPECTIVE", now, prov, cfg)
        store.append_unique(f"{now.isoformat()[:7]}/scan_runs.csv", S.SCAN_FIELDS, "record_id", [rec])
        print(f"recorded {status}")
        return 1

    if a.command == "log":
        if not cfg.logging_enabled:
            print("card shadow logging disabled (config) -- nothing written")
            return 0
        ws = S.ts(prov["workflow_start"]) if prov["workflow_start"] else None
        if ws is None:
            rec = S.scan_record(S.INPUT_INVALID, "WORKFLOW_START missing: cannot identify this run's scan", "", "PROSPECTIVE",
                                now, prov, cfg)
            store.append_unique(f"{now.isoformat()[:7]}/scan_runs.csv", S.SCAN_FIELDS, "record_id", [rec])
            print("FAILED: WORKFLOW_START missing")
            return 1
        rec = S.run_shadow(REPO, cfg, store, now, prov, "PROSPECTIVE",
                           cal_se_fn(REPO / cfg.inputs["calibration_results"]), ws)
        print(json.dumps({k: rec.get(k) for k in ("status", "failure_reason", "scan", "legs_logged", "cards_logged")}))
        return 0 if rec["status"] in S.SUCCESS_STATUSES + ("ALREADY_LOGGED", S.NO_SCAN) else 1

    # settle
    if not cfg.settlement_enabled:
        print("card shadow settlement disabled (config) -- nothing written")
        return 0
    try:
        valid = {r["record_id"] for r in store.read_all("scan_runs.csv") if r["status"] in S.SUCCESS_STATUSES}
        leg_rows = store.read_all("legs.csv")
        cards, unresolved = SS.attach_legs([c for c in store.read_all("cards.csv") if c["record_id"] in valid], leg_rows)
        legs = {r["leg_id"]: r for r in leg_rows}
        rows, diag = SS.settle_cards(cards, legs, S.read_csv(REPO / cfg.inputs["ledger_predictions"]),
                                     S.read_csv(REPO / cfg.inputs["ledger_settlements"]),
                                     store.read_all("card_settlements.csv"), now, cfg.overdue_days)
        diag["legs_unresolved"] = unresolved
        m = now.isoformat()[:7]
        n = store.append_unique(f"{m}/card_settlements.csv", SS.SETTLE_FIELDS, "settlement_id", rows)
        store.append_jsonl(f"{m}/settlement_runs.jsonl", {"at": now.isoformat(), **prov, "new_rows": n, **diag})
        print(json.dumps({"new_rows": n, **diag}))
        return 0
    except Exception as exc:
        try:
            store.append_jsonl(f"{now.isoformat()[:7]}/settlement_runs.jsonl", {"at": now.isoformat(), **prov, "status": S.FAILED,
                                                         "failure_reason": f"{type(exc).__name__}: {exc}"[:300]})
        except Exception:
            pass
        print(f"FAILED: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
