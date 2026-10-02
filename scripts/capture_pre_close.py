"""H2 PRE_CLOSE_VALUE capture (pre-registered: research/platform_v2/track_a/H2_PREREGISTRATION.md). Diagnostic only.

Hourly: for paper selections starting within the capture window and not yet captured, make ONE /odds call (h2h, uk;
1 credit) per sport key, and append a PRE_CLOSE_VALUE row per selection to research_shadow/h2_pre_close/pre_close_value.csv.
Credit guard: monthly spend (own ledger research_shadow/h2_pre_close/credit_ledger.csv, included in credit_report) < monthly_cap AND remaining >= the Tier-2
shadow floor (checked with the free /events call first). Never modifies selections, decisions or any production file.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.ingestion import the_odds_api_loader as L
from prediction_markets_lab.ops import credit_ledger as CL
from prediction_markets_lab.ops import football_coverage as FC
from prediction_markets_lab.research_shadow import pre_close as PC

REPO = Path(__file__).resolve().parents[1]
CONSUMER = "pre_close_capture"
OUT_DIR = "research_shadow/h2_pre_close"


def month_spend(ledger: Path, now: datetime) -> int:
    m = now.strftime("%Y-%m")
    return sum(int(r.get("credits_charged") or 0) for r in CL.read(ledger)
               if r["consumer"] == CONSUMER and r["timestamp_utc"].startswith(m) and r["outcome"] == CL.PAID)


def run(repo: Path, now: datetime, fetch_events=None, fetch_odds=None) -> dict:
    fetch_events = fetch_events or L.fetch_events_raw
    fetch_odds = fetch_odds or L.fetch_odds_raw
    budget = FC.load_budget(repo / "config/api_budget.json")
    cfgb = budget["pre_close_capture"]
    base = repo / OUT_DIR       # own files only: no production workflow writes here, so hourly commits never conflict
    ledger, out, missed = base / "credit_ledger.csv", base / "pre_close_value.csv", base / "pre_close_missed.csv"
    sels = PC.read_rows(repo / "paper_betting_v2/selections.csv")
    done = {r["selection_id"] for r in PC.read_rows(out)}
    terminal = {r["selection_id"] for r in PC.read_rows(missed) if r["status"] == PC.NOT_CAPTURED}
    for s in PC.never_captured(sels, done, terminal, now, PC.ts(cfgb["active_from"])):   # missing data, never imputed
        PC.log_missed(missed, s, now, PC.NOT_CAPTURED, "no successful capture inside the window before start")
    todo = PC.due(sels, done, now, float(cfgb["capture_window_minutes"]))
    fkeys = FC.sport_keys(FC.load(repo / "config/football_coverage.yaml"))
    football = {name: key for key, name in fkeys.items()}
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in todo:
        k = PC.sport_key_for(s, football)
        if k:
            groups[k].append(s)
        else:
            PC.log_missed(missed, s, now, PC.ATTEMPT_FAILED, "UNSUPPORTED_SPORT_KEY")
    summary = {"due": len(todo), "sport_keys": len(groups), "captured": 0, "skipped": []}
    floor = FC.tier_floor(budget, int(cfgb["protect_as_tier"]), now)
    cfg = L.TheOddsApiConfig(markets=("h2h",), markets_by_sport={})
    rows = []
    for key, items in groups.items():
        if month_spend(ledger, now) >= int(cfgb["monthly_cap"]):
            summary["skipped"].append((key, "monthly cap"))
            for s in items:
                PC.log_missed(missed, s, now, PC.ATTEMPT_FAILED, "SKIPPED_MONTHLY_CAP")
            CL.append(ledger, CONSUMER, f"odds:{key}", CL.SKIPPED_FLOOR, 0, 1, None, "monthly cap reached", now=now)
            continue
        hdr: dict = {}
        try:
            fetch_events(key, cfg, hdr)                                   # free: credit headers only
        except Exception as exc:                                          # fail closed for an optional consumer
            summary["skipped"].append((key, f"events check failed: {exc}"))
            for s in items:
                PC.log_missed(missed, s, now, PC.ATTEMPT_FAILED, f"EVENTS_CHECK_FAILED: {type(exc).__name__}")
            continue
        rem = hdr.get("x-requests-remaining")
        if rem in (None, "") or float(rem) < floor:
            summary["skipped"].append((key, f"floor: remaining {rem} < {floor}"))
            for s in items:
                PC.log_missed(missed, s, now, PC.ATTEMPT_FAILED, f"SKIPPED_CREDIT_FLOOR remaining={rem} floor={floor:.0f}")
            CL.append(ledger, CONSUMER, f"odds:{key}", CL.SKIPPED_FLOOR, 0, 1, hdr, f"remaining {rem} < floor {floor}", now=now)
            continue
        hdr = {}
        try:
            raw = fetch_odds(key, cfg, hdr)
        except Exception as exc:                                          # isolated: one key failing never stops others
            CL.append(ledger, CONSUMER, f"odds:{key}", CL.PAID, None, 0, hdr, f"error {type(exc).__name__}", now=now)
            for s in items:
                PC.log_missed(missed, s, now, PC.ATTEMPT_FAILED, f"ODDS_CALL_FAILED: {type(exc).__name__}")
            continue
        CL.append(ledger, CONSUMER, f"odds:{key}", CL.PAID, int(hdr.get("x-requests-last") or 1), 0, hdr, "", now=now)
        for s in items:
            ev = PC.find_event(raw if isinstance(raw, list) else [], s)
            r = PC.measure(s, ev, now) if ev else None
            if r:
                rows.append(r)
            else:
                why = "EVENT_NOT_FOUND_OR_AMBIGUOUS" if not ev else "NO_REFERENCE_PRICE_OR_STARTED"
                summary["skipped"].append((s["selection_id"], why))
                PC.log_missed(missed, s, now, PC.ATTEMPT_FAILED, why)
    summary["captured"] = PC.append_rows(out, rows)
    return summary


def main() -> int:
    print(run(REPO, datetime.now(timezone.utc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
