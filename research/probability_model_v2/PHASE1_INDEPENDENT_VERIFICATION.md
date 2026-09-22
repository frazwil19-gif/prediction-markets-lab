# Phase 2, Section 2 -- Independent Verification of the Phase 1 Backtest Result

**Written 2026-09-22.** Before building anything new, this re-derives Phase 1's headline numbers
directly from the committed backtest output files (`backtests/money-strategy-v1-frozen/`), rather
than trusting the prior write-up's prose. Both `predictions.csv` files were read and recomputed from;
nothing here is copied from `PHASE1_RESULTS_AUDIT.md` without a fresh check.

## Confirmed exactly as reported

- **5,776 matches included** (`manifest.json`: `matches_included: 5776`, of `total_rows_in_source_matches_file: 5800`, with `excluded_ineligible_consensus_model: 24` and zero excluded for kickoff-join failure or missing bookmaker panel).
- **17,328 candidates** in both `predictions.csv` files (5,776 x 3 outcomes) -- row-counted directly, not assumed.
- **Zero money-qualified bets** in both the closing-snapshot and opening-snapshot runs -- `money_qualified == "True"` count is 0 in both files, row-counted directly.
- **Configuration hash** `fca6f23522c449880791e9195c8e5f4eabe77beb5d12494c24e1c1fb2beb4544` recorded identically in both manifests.
- **269 "High"-confidence, actionable-grade (A+/A/B) candidates, all below 50% probability** (max 45.6%, min 3.0%) -- independently recomputed from the closing-run CSV. This claim from the Phase 1 write-up is CONFIRMED correct.
- **No implementation bug found.** Every rejection reason recorded on every actionable-grade, probability->=50% candidate traces to a real, correctly-applied threshold (the Medium-confidence odds-range restriction, the Medium-confidence stricter probability/EV floors, or a Low-confidence ineligibility) -- not a defect in `decisions/money_qualification.py`.

## Correction to the prior write-up

The Phase 1 §22 entry describes the closest miss in a sentence structure that reads as if it belongs
to the "269 High-confidence" group quoted immediately before it. **It does not.** Re-derived directly
from the CSV:

| Field | Value |
|---|---|
| Event | Motherwell v Celtic |
| Competition | SC0 (Scottish Premiership) |
| Season | 2021/22 |
| Match date | 2021-10-16 |
| Selection | Away (Celtic) |
| Estimated (consensus) probability | 68.62% |
| Best price (bookmaker BW) | 1.53 |
| Fair odds (1/probability) | 1.457 |
| Gross EV (probability x odds - 1) | +4.99% |
| Net EV | +4.99% (identical to gross -- this backtest applies no commission, consistent with a bookmaker-price, not exchange-price, comparison) |
| Confidence | **Medium** (not High) |
| Research grade | B |
| Money gates checked, in order: |
| - Research grade actionable (A+/A/B)? | PASS (B) |
| - Confidence eligible (High, or Medium meeting the stricter tests)? | PASS -- Medium with probability >=60% and odds in the 1.40-2.50 preferred range |
| - Data quality mechanical checks | PASS |
| - Minimum probability floor (Medium: 60%) | PASS (68.6%) |
| - Payout floor (odds inside 1.40-2.50) | PASS (1.53) |
| - **Minimum net EV floor (Medium: 5.00%)** | **FAIL -- 4.99% is 0.01 percentage points short of 5.00%** |
| Money decision | PAPER_ONLY |
| Actual result | Won (Celtic did win this match) |

This candidate is correctly a **Medium**-confidence near-miss on the **net EV floor specifically**,
not a High-confidence candidate. The separate claim -- "all 269 High-confidence candidates sit below
50% probability" -- is a different, independently-true fact about a different subset of candidates.
Conflating the two in one sentence was a real clarity defect in the Phase 1 write-up, corrected here.
It does not change any conclusion: the mechanistic explanation (cross-bookmaker disagreement produces
apparent EV concentrated on less-fancied outcomes, which the probability/confidence gates correctly
filter) applies to this Medium-confidence near-miss just as it was described applying to the
High-confidence population -- the specific gate that stopped it (net EV, not probability) is simply
different, and worth stating precisely rather than approximately.

## Broader sanity check

2,487 of the 17,328 candidates (14.3%) clear the bare 50% probability floor; zero of those 2,487 were
money-qualified, each for a specific, itemised reason (confidence ineligibility, the stricter
Medium-confidence odds/EV floors, or occasionally a data-quality/payout-range failure) -- there is no
candidate anywhere in either run that cleared every gate and was still, inexplicably, rejected. This
is the concrete evidence behind "no implementation bug was found."

**Conclusion: the Phase 1 result stands, independently re-derived from the raw output files, with one
documentation-clarity correction (above) and no code defect found.**
