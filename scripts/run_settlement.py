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
        football_data_fallback(ledger_path, bankroll_cfg["starting_bankroll_gbp"])
        return 1

    summary = settle_pending_paper_bets(
        ledger_path, config, starting_bankroll_gbp=bankroll_cfg["starting_bankroll_gbp"],
        archive_dir=REPO_ROOT / "settlement_archive",  # raw scores kept for the free-source shadow comparison
        skip_if_nothing_started=True,  # V2-5: no scores call for a league with no pending bet started in the window
    )
    if summary.skipped_sport_keys_nothing_started:
        print(f"Skipped (no pending bet started in window; 0 credits): {summary.skipped_sport_keys_nothing_started}")

    print(f"Settled: {len(summary.settled_bet_ids)} -- {summary.settled_bet_ids}")
    print(f"Not yet completed: {len(summary.not_yet_completed_bet_ids)}")
    print(f"Event not found in scores window: {len(summary.event_not_found_bet_ids)}")
    print(
        f"Cannot auto-settle (no provider event id): {len(summary.unresolvable_no_provider_id)} "
        f"-- {summary.unresolvable_no_provider_id}"
    )
    if summary.errors:
        print(f"Errors: {summary.errors}", file=sys.stderr)

    football_data_fallback(ledger_path, bankroll_cfg["starting_bankroll_gbp"])
    return 0


def football_data_fallback(ledger_path: Path, starting_bankroll_gbp: float) -> None:
    """Settlement hardening (2026-10-02): rows the scores API can never settle (no provider id / outside the scores
    window) go through the deterministic football-data.co.uk path. 0 credits. A download failure settles nothing."""
    import urllib.request
    from datetime import datetime, timezone

    from prediction_markets_lab.prediction_platform.settle import COMP_TO_FD
    from prediction_markets_lab.settlement import football_data_results as fd
    from prediction_markets_lab.settlement.settle_paper_ledger import fallback_reason, settle_with_football_data_fallback
    from prediction_markets_lab.storage.paper_ledger import load_paper_bets

    now = datetime.now(timezone.utc)
    due = [r for r in load_paper_bets(ledger_path) if fallback_reason(r, now)]
    if not due:
        print("football-data fallback: nothing eligible")
        return
    aliases, results = fd.load_settlement_aliases(), []
    for code in sorted({COMP_TO_FD[r["competition"]] for r in due if r.get("competition") in COMP_TO_FD}):
        url = fd.fd_url(code, now.date())
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "prediction-markets-lab settlement (non-commercial)"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                results += fd.parse_fd_csv(resp.read().decode("utf-8-sig", errors="replace"), code, aliases)
        except Exception as exc:  # noqa: BLE001 -- fail closed: that league settles nothing this run
            print(f"::warning::football-data {code} unavailable ({exc}); its fallback rows stay pending")
    res = settle_with_football_data_fallback(ledger_path, starting_bankroll_gbp, results, aliases, COMP_TO_FD, now,
                                             REPO_ROOT / "settlement_archive" / "legacy_football_data_settlements.csv")
    print(f"football-data fallback settled: {len(res.settled)} -- {res.settled}")
    if res.left_pending:
        print(f"::warning::football-data fallback left pending: {res.left_pending}")


if __name__ == "__main__":
    sys.exit(main())
