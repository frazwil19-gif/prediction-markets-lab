# Paper-Bet Ledger (Track B)

This directory holds `paper_bets.csv`: the append-only, unbiased forward record of every candidate the Daily Engine graded A+/A/B, whether or not Fraser actually placed a real-money bet on it.

**Do not hand-edit this file.** Use `src/prediction_markets_lab/storage/paper_ledger.py`'s `record_qualifying_candidates` (from a live scan) or `record_qualifying_candidates_from_contract` (from an already-written `daily_cards/<date>/card.json`) to add rows, and `settle_paper_bet` to settle one after the event finishes. Core decision fields (everything except `status`, `result`, `closing_odds_if_available`, `actual_pnl`, `paper_bankroll_after_settlement`) are immutable once written — `settle_paper_bet` enforces this and raises if anything else would change.

This file is committed to the repository deliberately (it lives at the repo root, not under `data/` or `reports/daily/`, both gitignored) — it is the evidence base the whole future automated-execution decision depends on, per the project's master research directive §14 and the "MAJOR NEXT PHASE — LIVE COMMISSIONING" instruction's Track B design.

**Known limitation**: `kickoff` currently holds only the fixture's date, not a full kickoff time-of-day — see `storage/paper_ledger.py`'s module docstring for why, and what a fuller fix would involve.
