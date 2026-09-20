#!/usr/bin/env python3
"""Automated settlement CLI (Section 7, Production Infrastructure Build).

Usage:
    python scripts/run_settlement.py

Reads config/bankroll.yaml for the paper bankroll's starting value, fetches
live results from The Odds API's /v4/sports/{sport}/scores for every
sport_key with at least one pending paper bet, and settles every bet whose
event has a completed score -- via settlement.settle_paper_ledger
(deterministic, idempotent; see that module's docstring). Requires
THE_ODDS_API_KEY exactly as scripts/run_daily_scan.py --source odds-api
does, and stops at that same credential gate if it is not set.

This script settles Track B (paper) bets only. Track A (Fraser's real
placed bets) is confirmed and settled separately and manually via
scripts/settle_results.py against real_bets/ -- see Section 6/16's KEEP
decision on that existing, working script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from prediction_markets_lab.ingestion.the_odds_api_loader import (
    TheOddsApiConfig,
    TheOddsApiCredentialError,
)
from prediction_markets_lab.settlement.settle_paper_ledger import settle_pending_paper_bets

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    bankroll_cfg = yaml.safe_load((REPO_ROOT / "config" / "bankroll.yaml").read_text())
    ledger_path = REPO_ROOT / "paper_ledger" / "paper_bets.csv"

    config = TheOddsApiConfig()
    try:
        config.resolve_api_key()
    except TheOddsApiCredentialError as exc:
        print(f"Cannot run settlement: {exc}", file=sys.stderr)
        return 1

    summary = settle_pending_paper_bets(
        ledger_path, config, starting_bankroll_gbp=bankroll_cfg["starting_bankroll_gbp"]
    )

    print(f"Settled: {len(summary.settled_bet_ids)} -- {summary.settled_bet_ids}")
    print(f"Not yet completed: {len(summary.not_yet_completed_bet_ids)}")
    print(f"Event not found in scores window: {len(summary.event_not_found_bet_ids)}")
    print(
        f"Cannot auto-settle (no provider event id): {len(summary.unresolvable_no_provider_id)} "
        f"-- {summary.unresolvable_no_provider_id}"
    )
    if summary.errors:
        print(f"Errors: {summary.errors}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
