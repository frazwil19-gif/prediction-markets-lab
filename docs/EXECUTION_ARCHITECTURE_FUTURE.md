# Future Automated-Execution Architecture (Documentation Only -- NOT Enabled)

**Status: interface documented, NOT built, NOT enabled.** This is Section 14
of the operator's "MAJOR NEXT PHASE -- PRODUCTION INFRASTRUCTURE BUILD"
instruction (2026-09-20): "DO NOT PLACE REAL BETS AUTOMATICALLY. However,
build the architecture so future execution can be added cleanly." Nothing
in this document is wired into any running code. No automatic real-money
execution exists anywhere in this repository, and none is authorised.

## The interface

```text
Qualified Recommendation (Daily Bet Card contract, Grade A+/A only)
    -> Risk Manager        (portfolio-level checks: exposure, duplicate bets, loss locks)
    -> Execution Guard      (final pre-trade gate: fresh price, kill switch, sanity bounds)
    -> Execution Adapter    (translates a decision into one bookmaker/exchange's specific API calls)
    -> bookmaker/exchange API
    -> confirmation          (the venue's own fill/acceptance response)
    -> immutable real bet ledger (real_bets/bets.csv -- append-only, same
                                   immutability discipline as paper_ledger/)
```

Every stage between "Qualified Recommendation" and "confirmation" is new
work, not a relabelling of anything that exists today. `real_bets/` (this
build) and `scripts/settle_results.py` (pre-existing, KEEP) already cover
the ledger and settlement end of this diagram for a bet Fraser enters by
hand; nothing upstream of that -- the Risk Manager, Execution Guard, or
Execution Adapter -- exists in any form.

## Required gates before this could ever be considered (not built)

- Minimum probability, minimum confidence, minimum odds/payout (this
  build's `decisions.payout_policy`, Section 3, already implements the
  odds floor for the *recommendation* layer -- an Execution Guard would
  need to re-check it against a fresh price immediately before placing,
  not just at recommendation time), minimum value/EV.
- Fresh-price requirement: the price used to justify the bet must be
  re-verified, not assumed to still hold, at the moment of placement
  (this is the "no stale prices" risk rule already in the master
  research directive, extended to an automated context).
- Maximum stake per bet, maximum daily exposure, maximum drawdown, a
  daily loss lock -- config/bankroll.yaml already defines the values for
  a human deciding whether to place a bet; an Execution Guard would need
  to enforce them programmatically and refuse to place a bet that would
  breach any of them, not just flag it.
- Duplicate-bet protection and idempotency: placing the same
  recommendation twice (e.g. a retried request after a timeout) must
  never result in two live bets. paper_ledger's bet_id-keyed duplicate
  check (Section 3B / this ledger's whole design) is the closest existing
  analogue, but a real-money version needs to be robust to a genuinely
  uncertain response from the venue (did the bet go through or not?),
  which paper trading never has to handle.
- Price/slippage tolerance: what happens if the price has moved between
  recommendation and placement -- accept within a tolerance band, or
  refuse and log a "stale/moved price" rejection.
- Liquidity checks where available (decisions.liquidity already exists
  for the recommendation layer -- KEEP -- but has never been exercised
  against a real, time-sensitive liquidity constraint at placement time).
- API failure handling: a bookmaker/exchange API error, timeout, or
  ambiguous response must never be silently treated as "no bet placed"
  if it might actually have gone through, and never silently retried in
  a way that could double-place a bet.
- A kill switch: a single, fast, reliable way to halt all automated
  placement immediately, independent of any other part of the system
  being healthy.

## Why this stays documentation-only for now

Section 17 (commissioning) and Section 9 (Phase 9's priority order, from
the prior "LIVE COMMISSIONING" instruction) are explicit: prove the
operational engine and validation infrastructure first. At the time this
document was written, the system has exactly one real live Daily Bet
Card, zero settled paper bets, and zero backtest results. None of the
"required gates" above have real-world evidence behind their proposed
values (the bankroll config's numbers are the operator's own initial
choices, not yet validated against realised drawdown or loss-lock
behaviour). Building an Execution Guard against untested assumptions
would be exactly the kind of premature complexity Section 17's "do not
loosen thresholds merely so a paper bet appears" discipline warns
against in spirit -- automating execution before there is a track record
to automate against.
