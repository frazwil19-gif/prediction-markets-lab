#!/usr/bin/env python3
"""Record a real-money bet Fraser actually placed (Track A) -- Section 6.

This is the "easy for ChatGPT to record... without editing production
calculations" entry point the operator's instruction asks for: it never
recomputes probability/EV/grading -- it only copies the relevant fields
from an already-generated Daily Bet Card contract (card.json) into a
storage.schemas.BetRecord row in real_bets/bets.csv, the REAL-money
ledger, kept deliberately separate from paper_ledger/paper_bets.csv
(Track B) so paper and real performance are never mixed (Section 6).

Usage:
    python scripts/record_real_bet.py \\
        --card daily_cards/2026-09-20/card.json \\
        --event "Team A v Team B" --market 1x2 --selection home \\
        [--actual-odds 2.15] [--actual-stake 0.25]

If --actual-odds/--actual-stake are omitted, the card's own recommended
odds/stake are used -- pass them explicitly when Fraser got a different
price or staked a different amount than recommended.

Settle later with scripts/settle_results.py, exactly as before this
change -- this script only creates the pending row; it does not touch
settlement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prediction_markets_lab.storage.csv_store import append_record, read_records
from prediction_markets_lab.storage.schemas import BankrollTransaction, BetRecord
from prediction_markets_lab.utils.dates import now_utc_iso

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BETS_PATH = REPO_ROOT / "real_bets" / "bets.csv"
DEFAULT_BANKROLL_PATH = REPO_ROOT / "real_bets" / "bankroll.csv"


def _find_candidate(contract: dict, event: str, market: str, selection: str) -> dict:
    for candidate in contract["candidates"]:
        if candidate["event"] == event and candidate["market"] == market and candidate["selection"] == selection:
            return candidate
    raise SystemExit(
        f"No candidate found in this card for event={event!r} market={market!r} selection={selection!r}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--card", type=Path, required=True, help="Path to a card.json")
    parser.add_argument("--event", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--actual-odds", type=float, default=None)
    parser.add_argument("--actual-stake", type=float, default=None)
    parser.add_argument("--bets", type=Path, default=DEFAULT_BETS_PATH)
    parser.add_argument("--bankroll", type=Path, default=DEFAULT_BANKROLL_PATH)
    args = parser.parse_args()

    contract = json.loads(args.card.read_text())
    candidate = _find_candidate(contract, args.event, args.market, args.selection)

    odds = args.actual_odds if args.actual_odds is not None else candidate["available_odds"]
    stake = args.actual_stake if args.actual_stake is not None else candidate["recommended_stake"]
    if stake <= 0:
        print(
            f"REJECTED: recommended_stake for this candidate is {candidate['recommended_stake']} "
            "(grade below A -- not a live-stake recommendation). Pass --actual-stake explicitly if "
            "Fraser chose to stake it anyway.",
            file=sys.stderr,
        )
        return 1

    existing_ledger = read_records(args.bankroll, BankrollTransaction)
    bankroll_before = existing_ledger[-1].balance if existing_ledger else 10.0

    bet_id = f"REAL-{candidate['date']}-{args.event}-{args.market}-{args.selection}".replace(" ", "_")

    existing_bets = read_records(args.bets, BetRecord)
    if any(b.bet_id == bet_id for b in existing_bets):
        print(f"REJECTED: {bet_id} is already recorded -- duplicate real-bet placement.", file=sys.stderr)
        return 1

    bet = BetRecord(
        bet_id=bet_id,
        market_id=bet_id,
        bet_timestamp=now_utc_iso(),
        sport=candidate["sport"],
        competition=candidate["competition"],
        event=candidate["event"],
        market=candidate["market"],
        selection=candidate["selection"],
        venue=candidate["bookmaker"],
        requested_odds=candidate["available_odds"],
        matched_odds=odds,
        stake=stake,
        estimated_probability=candidate["estimated_probability"],
        implied_probability=1.0 / odds if odds else 0.0,
        net_ev_at_entry=candidate["ev_value_indicator"],
        confidence_score=candidate["confidence"],
        grade=candidate["grade"],
        bankroll_before=bankroll_before,
        liability=stake,
    )

    append_record(args.bets, bet)
    print(f"Recorded real bet {bet.bet_id}: GBP{stake:.2f} on {args.selection} @ {odds} ({args.event})")
    print(
        "Settle later with: python scripts/settle_results.py "
        f"--bets {args.bets} --bankroll {args.bankroll} --bet-id {bet.bet_id} --result <win|loss|void>"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
