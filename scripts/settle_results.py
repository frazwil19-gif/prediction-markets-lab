#!/usr/bin/env python3
"""Settle a result against an open bet and update the bankroll ledger.

Usage:
    python scripts/settle_results.py \\
        --bets data/processed/bets.csv \\
        --bankroll data/processed/bankroll.csv \\
        --bet-id B-0001 \\
        --result win

This is a Stage 2 command-line helper for the "result settlement
process" (project instructions section 11). It reads storage.schemas
CSV files, computes gross/net profit for the settled bet using
ev-consistent commission handling, appends a Bankroll ledger row, and
rewrites the Bets CSV with the bet marked settled.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prediction_markets_lab.risk.bankroll import BankrollState
from prediction_markets_lab.storage.csv_store import overwrite_records, read_records
from prediction_markets_lab.storage.schemas import BankrollTransaction, BetRecord
from prediction_markets_lab.utils.dates import now_utc_iso


def settle_bet(bet: BetRecord, result: str) -> BetRecord:
    """Compute profit/loss for a single bet given its settlement result.

    Args:
        bet: The bet record to settle (result must currently be "pending").
        result: One of "win", "loss", "void".

    Returns:
        A new BetRecord with result, gross_profit, commission_paid,
        net_profit and bankroll_after populated.

    Raises:
        ValueError: If the bet is not pending, or result is not a
            recognised value.
    """
    if bet.result != "pending":
        raise ValueError(f"bet {bet.bet_id} is already settled as {bet.result!r}")
    if result not in ("win", "loss", "void"):
        raise ValueError(f"unrecognised result: {result!r}")

    if result == "void":
        gross_profit = 0.0
        commission_paid = 0.0
    elif result == "win":
        gross_profit = bet.stake * (bet.matched_odds - 1.0)
        # Commission is charged on net winnings (gross profit) only,
        # matching ev.expected_value's EV formula convention.
        commission_paid = gross_profit * _infer_commission_rate(bet)
    else:  # loss
        gross_profit = -bet.stake
        commission_paid = 0.0

    net_profit = gross_profit - commission_paid
    bankroll_after = bet.bankroll_before + net_profit

    return bet.model_copy(
        update={
            "result": result,
            "gross_profit": gross_profit,
            "commission_paid": commission_paid,
            "net_profit": net_profit,
            "bankroll_after": bankroll_after,
        }
    )


def _infer_commission_rate(bet: BetRecord) -> float:
    """Infer the commission rate implied by net_ev_at_entry, as a fallback.

    Stage 2 does not yet store the raw commission rate on BetRecord
    directly; this uses the venue to apply the config default rather
    than re-deriving it from net_ev_at_entry, which is a cleaner and
    more accurate source of truth.
    """
    import yaml

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "config" / "commissions.yaml") as f:
        commissions = yaml.safe_load(f)
    key = "smarkets" if bet.venue == "Smarkets" else "betfair"
    return commissions[key]["standard_commission"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bets", type=Path, required=True)
    parser.add_argument("--bankroll", type=Path, required=True)
    parser.add_argument("--bet-id", required=True)
    parser.add_argument("--result", required=True, choices=["win", "loss", "void"])
    args = parser.parse_args()

    bets = read_records(args.bets, BetRecord)
    matches = [b for b in bets if b.bet_id == args.bet_id]
    if not matches:
        print(f"REJECTED: no bet found with bet_id {args.bet_id!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        print(f"REJECTED: duplicate bet_id {args.bet_id!r} found — bankroll data is inconsistent", file=sys.stderr)
        return 1

    bet = matches[0]
    try:
        settled = settle_bet(bet, args.result)
    except ValueError as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 1

    updated_bets = [settled if b.bet_id == args.bet_id else b for b in bets]
    overwrite_records(args.bets, updated_bets)

    existing_ledger = read_records(args.bankroll, BankrollTransaction)
    if existing_ledger:
        state = BankrollState(
            current_balance=existing_ledger[-1].balance,
            peak_balance=existing_ledger[-1].peak_balance,
        )
    else:
        state = BankrollState(current_balance=bet.bankroll_before, peak_balance=bet.bankroll_before)

    new_state = state.apply_change(settled.net_profit)

    from prediction_markets_lab.storage.csv_store import append_record

    append_record(
        args.bankroll,
        BankrollTransaction(
            timestamp=now_utc_iso(),
            transaction_type="bet_settlement",
            stake=bet.stake,
            **{"return": settled.gross_profit + bet.stake if args.result == "win" else 0.0},
            commission=settled.commission_paid,
            net_change=settled.net_profit,
            balance=new_state.current_balance,
            peak_balance=new_state.peak_balance,
            drawdown=new_state.drawdown,
            notes=f"settled bet {bet.bet_id} as {args.result}",
        ),
    )

    print(
        f"Settled {bet.bet_id} as {args.result}: net profit £{settled.net_profit:.2f}, "
        f"new bankroll £{new_state.current_balance:.2f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
