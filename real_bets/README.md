# Real-Money Bet Ledger (Track A)

This directory holds `bets.csv` and `bankroll.csv`: the record of bets
Fraser actually placed with real money, plus the real bankroll ledger.

**Deliberately separate from `paper_ledger/`** (Track B, every A+/A/B
candidate recorded automatically whether or not Fraser placed it). The
operator's "MAJOR NEXT PHASE -- PRODUCTION INFRASTRUCTURE BUILD"
instruction, Section 6: "DO NOT mix PAPER PERFORMANCE with REAL
PERFORMANCE." `reports/latest_performance.json` reports on the paper
ledger only; a real-money performance view would be a separate report
over this directory, not yet built (see the production-infrastructure
audit's remaining-work list).

Record a real placement with:

    python scripts/record_real_bet.py --card daily_cards/<date>/card.json \
        --event "Team A v Team B" --market 1x2 --selection home

Settle it once the result is known with the existing (KEEP, unchanged)
`scripts/settle_results.py`:

    python scripts/settle_results.py --bets real_bets/bets.csv \
        --bankroll real_bets/bankroll.csv --bet-id <bet_id> --result win

Both files are committed to the repository (not gitignored), matching
`paper_ledger/`'s and `daily_cards/`'s placement: GitHub is this
project's canonical source of truth, and Fraser's real-money record must
not live only inside a Claude Cowork session.
