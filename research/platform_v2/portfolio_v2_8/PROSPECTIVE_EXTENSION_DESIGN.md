# V2-8 Prospective Extension: Bounded Design (DESIGN ONLY; not deployed; needs separate approval)

## Principle
The live V2-7 logger (cer-2) stays frozen. Its already-logged data are sufficient to reconstruct every V2-8 portfolio, so **no new
live logging, no new API calls and no change to V2-7 are proposed.** V2-8 becomes an **offline, deterministic analyser** that runs
after the fact over frozen prospective records.

## Inputs (all append-only, all written before outcomes were known)
| need | source |
|---|---|
| Strongest daily predictions (P, σ inputs, width) | V2-7 `prospective/<YYYY-MM>/legs.csv`: event-level HIGH_P legs (book `*`, P ≥ 0.70, up to 24 events per scan) |
| Per-book prices for HIGH_P legs, same scan | production `tennis_predictions/price_snapshots.csv` (sha recorded in each V2-7 `scan_runs.csv` record) |
| POS_EV legs, per book | V2-7 `legs.csv` rows with a named book |
| Provenance, run, commit, scan time | V2-7 `scan_runs.csv` (only `OK` / `OK_ZERO_CANDIDATES` records are valid) |
| Outcomes | production tennis settlement ledger (read-only). This is a research settlement and **needs the same separate approval as V2-7 settlement** |

## Deterministic, bounded construction (per valid scan)
1. **HIGH_P set:** top-N legs by P (P ≥ 0.70, distinct participants; ties by event hash), N ∈ {3, 5}.
   **POS_EV set:** top-N by P among EV > 0 at one book, N ∈ {2, 3}; if several books qualify, the book with the highest product of
   leg prices.
2. **Structures:** the pre-registered list in `PREREGISTRATION.md` §3, at most 16 per set. The cap of N ≤ 5 is a computational
   cap, not a betting rule.
3. **Pricing:** same book, same scan. The multi price is the product (**INDICATIVE**). Each leg's price, book, quote timestamp and scan
   are retained, so an eventual real accumulator quote can be compared line by line.
4. **Per structure:**
   - exact 2^N outcome distribution: E[return], SD, P(lose all), P(positive), maximum loss, expected log growth at 1/2/5%;
   - exposure per leg;
   - sensitivity grid δ ∈ {±0.5, 1, 1.5, 2, 3, 5} pp;
   - stake feasibility at £20/30/50/100 with £0.10 and £1 minimum lines.
5. **Two scoreboards:** legs (prediction) and instruments (as settled). A near miss is never counted as a win.
6. **First scan wins:** if a leg set recurs in later scans, the first logged scan is primary, as in the V2-7 analysis plan.

## Storage and runtime
- **Nothing is required**: the analysis can be recomputed on demand from frozen inputs.
- If summaries are stored: about 2 sets × 16 structures × ~300 B ≈ 10 KB per scan, which is about 7 MB/year at two scans a day,
  split into monthly shards.
- **Runtime:** well under 1 s per scan; 2^5 = 32 outcomes × ≤ 31 lines.

## Evaluation (to be pre-registered separately before any prospective V2-8 result)
The same metrics as the historical V2-8 study, applied to prospective data only. The confirmation criteria are those in
REPORT §9, question 12. No threshold changes on early outcomes. Thirty settled scans trigger an operational review, not validation.

## Explicitly out of scope until approved
- Adding 4- or 5-leg cards to the V2-7 logger.
- Enabling any settlement.
- Paper multis.
- Real money.
