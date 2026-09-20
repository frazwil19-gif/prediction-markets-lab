#!/usr/bin/env python3
"""Write status/latest.json (Section 12).

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
    unsettled = sum(1 for row in load_paper_bets(ledger_path) if row.get("status") == "pending")

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
    )

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status.to_dict(), indent=2) + "\n")
    print(f"System status written to {STATUS_PATH}")
    print(json.dumps(status.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
