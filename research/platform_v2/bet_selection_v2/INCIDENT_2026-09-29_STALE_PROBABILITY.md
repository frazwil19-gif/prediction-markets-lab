# Incident: Bet-Selection V2 paired a stale probability with later prices (2026-09-29) — fixed as bsv2-2

## What happened
First production run of V2-6: tennis_prediction_board **36573450011** (15:30 cron, started 13:12 UTC, commit `ee7d49a`) wrote
**9 PAPER_BET** selections (`d2e6bb5`). daily_scan **36578206908** (13:51) added 0.
- **5 of the 9 are invalid.** Their probability was the prediction ledger's frozen *first* snapshot (08:31 UTC), while the prices came
  from the 13:13 scan. By 13:13 the market had moved against all five players: the engine's own P at 13:13 was 2–5 pp lower, and the
  same-snapshot net EV was **negative** (−0.8% to −3.4%). Two of them were even Betfair-exchange "value" bets, which is impossible at
  the same snapshot.
- **4 are valid.** They were first predicted at 13:13, so P and price share one snapshot (net EV +2.9% to +10.4% against soft books).
- Mechanism: adverse selection. It is the same bias measured historically in V2-6D, where the close moved against 92–97% of
  "value" found with an earlier P.

## Fix (rule_version bsv2-2; gates unchanged)
- EV is computed only with the engine P from the **same snapshot** as the price (`PriceSnapshot.p_same_snapshot`). A missing P gives
  `PROBABILITY_NOT_SAME_SNAPSHOT` (hard reject).
- Only the **latest** snapshot's coexisting quotes are compared (no best-price-across-time).
- The tennis board now appends every scan's engine output to `tennis_predictions/probability_snapshots.csv` (0 credits; frozen engine
  unchanged; the prediction ledger rule "first valid snapshot is canonical" is unchanged, for calibration).
- Football: the card's own P (same card) is used for its prices.
- Selections record the frozen ledger P in `reasons` (`LEDGER_P=…`). The schema is unchanged.

## Records
- The bsv2-1 rows stay **immutable**. `paper_betting_v2/selection_annotations.csv` marks 5 as `INVALID_STALE_PROBABILITY` and 4 as
  `VALID_SAME_SNAPSHOT`, with evidence.
- Reports count bsv2-2 rows plus bsv2-1 rows annotated VALID. Valid bsv2-1 selections block duplicate exposure on the same prediction.
- Replay of the fixed code on the 13:13 data (scratch only, nothing written): it selects the 4 valid ones plus **Holger Rune** (engine P
  0.62 → 0.81 between 08:31 and 13:13; BoyleSports 1.57 vs fair 1.24, +26% EV). That selection would only happen live if a post-fix scan
  sees it. A +26% edge from a big market move is the classic slow-bookmaker profile: flagged for manual review, no rule added.

Tests: 5 new regression tests (stale P never paired; missing P rejected; latest snapshot only; research-only scans never supply P;
duplicate-exposure guard).
