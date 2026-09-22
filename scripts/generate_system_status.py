#!/usr/bin/env python3
"""Write status/latest.json (Section 12; extended Section 13 -- TARGETED
PRODUCTION CHANGE, 2026-09-22).

Usage:
    python scripts/generate_system_status.py --scan-status success
    python scripts/generate_system_status.py --scan-status failure
    python scripts/generate_system_status.py --settlement-status success --performance-updated

Designed to be called from every GitHub Actions job that could otherwise
leave ChatGPT unable to distinguish "nothing qualified" from "something
broke" -- see reports.system_status's module docstring. Called with
`if: always()` from each workflow so a failed step still updates status.
Each field this script does not receive an update for this run is carried
forward from the existing status/latest.json (a settlement run does not
know the day's scan counts, and should not blank them out).

2026-09-22 addition: also reads today's money_card.json (written
alongside card.json by run_daily_scan.py -- see reports/money_card.py)
to populate research_candidates/money_qualified_count/money_card_status,
and splits the paper ledger's pending count into paper_money_pending vs
paper_research_pending by storage.paper_ledger.PaperBet.money_qualified.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from prediction_markets_lab.reports.daily_bet_card import ENGINE_VERSION
from prediction_markets_lab.reports.system_status import SystemStatus
from prediction_markets_lab.storage.paper_ledger import load_paper_bets

REPO_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = REPO_ROOT / "status" / "latest.json"


def _load_existing() -> dict:
    if STATUS_PATH.exists():
        try:
            return json.loads(STATUS_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _read_todays_card_counts() -> tuple[int | None, int | None]:
    """Best-effort read of today's own card.json for candidate/qualified
    counts, so the workflow does not need to parse run_daily_scan.py's
    stdout -- card.json is the single source of truth for these numbers.
    """
    card_path = REPO_ROOT / "daily_cards" / date.today().isoformat() / "card.json"
    if not card_path.exists():
        return None, None
    try:
        card = json.loads(card_path.read_text())
    except json.JSONDecodeError:
        return None, None
    candidates = card.get("candidates_analysed")
    grade_counts = card.get("grade_counts", {})
    qualified = sum(grade_counts.get(g, 0) for g in ("A+", "A", "B"))
    return candidates, qualified


def _read_todays_money_card() -> tuple[str, int | None, int | None]:
    """Best-effort read of today's own money_card.json.

    Returns (money_card_status, research_candidates_analysed,
    money_qualified_count). money_card_status is "ok" if the file exists
    (a valid, successful "zero qualified" run still produces one) and
    "missing" otherwise -- e.g. because the scan itself failed before
    reaching the money-card write.
    """
    money_card_path = REPO_ROOT / "daily_cards" / date.today().isoformat() / "money_card.json"
    if not money_card_path.exists():
        return "missing", None, None
    try:
        money_card = json.loads(money_card_path.read_text())
    except json.JSONDecodeError:
        return "missing", None, None
    return (
        "ok",
        money_card.get("research_candidates_analysed"),
        money_card.get("money_qualified_count"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scan-status", choices=["success", "failure"], default=None)
    parser.add_argument("--scan-candidates", type=int, default=None)
    parser.add_argument("--scan-qualified", type=int, default=None)
    parser.add_argument("--settlement-status", choices=["success", "failure"], default=None)
    parser.add_argument("--performance-updated", action="store_true")
    parser.add_argument("--warning", action="append", default=[])
    args = parser.parse_args()

    existing = _load_existing()
    now = datetime.now(timezone.utc).isoformat()

    last_scan = existing.get("last_scan", {})
    last_settlement = existing.get("last_settlement", {})

    scan_at = now if args.scan_status else last_scan.get("at", "")
    scan_status = args.scan_status or last_scan.get("status", "unknown")
    scan_candidates = args.scan_candidates
    scan_qualified = args.scan_qualified
    if args.scan_status == "success" and scan_candidates is None and scan_qualified is None:
        scan_candidates, scan_qualified = _read_todays_card_counts()
    if scan_candidates is None:
        scan_candidates = last_scan.get("candidates_analysed")
    if scan_qualified is None:
        scan_qualified = last_scan.get("qualified_count")

    settlement_at = now if args.settlement_status else last_settlement.get("at", "")
    settlement_status = args.settlement_status or last_settlement.get("status", "unknown")

    performance_at = now if args.performance_updated else existing.get("last_performance_update_at", "")

    ledger_path = REPO_ROOT / "paper_ledger" / "paper_bets.csv"
    ledger_rows = load_paper_bets(ledger_path)
    unsettled = sum(1 for row in ledger_rows if row.get("status") == "pending")
    paper_money_pending = sum(
        1
        for row in ledger_rows
        if row.get("status") == "pending" and str(row.get("money_qualified", "")).strip().lower() in {"true", "1", "yes"}
    )
    paper_research_pending = unsettled - paper_money_pending

    money_card_status, research_candidates, money_qualified_count = existing.get(
        "money_card_status", "unknown"
    ), existing.get("research_candidates"), existing.get("money_qualified_count")
    if args.scan_status == "success":
        money_card_status, research_candidates, money_qualified_count = _read_todays_money_card()
    elif args.scan_status == "failure":
        money_card_status = "missing"

    status = SystemStatus(
        last_scan_at=scan_at,
        last_scan_status=scan_status,
        last_scan_candidates=scan_candidates,
        last_scan_qualified_count=scan_qualified,
        last_settlement_at=settlement_at,
        last_settlement_status=settlement_status,
        last_performance_update_at=performance_at,
        engine_version=ENGINE_VERSION,
        unsettled_paper_bet_count=unsettled,
        warnings=args.warning,
        research_candidates=research_candidates,
        money_qualified_count=money_qualified_count,
        paper_money_pending=paper_money_pending,
        paper_research_pending=paper_research_pending,
        money_card_status=money_card_status,
    )

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status.to_dict(), indent=2) + "\n")
    print(f"System status written to {STATUS_PATH}")
    print(json.dumps(status.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
