# V2-6D — Free Tennis Data: Acquisition, Audit and Closing-Price Diagnostic — Results (2026-09-29)

**Label: CLOSING-TIME DIAGNOSTIC. Not an executable backtest, not paper betting, not prospective evidence.** A negative result
does not prove that earlier opportunities were absent; a positive result is not an achievable edge. Pre-registration:
`V2_6D_CLOSING_DIAGNOSTIC_PREREGISTRATION.md` (commit `bfab37b`) plus the disclosed post-hoc Amendment A1. Code:
`scripts/v2_6d_tennis_closing_diagnostic.py`. Numbers: `V2_6D_CLOSING_DIAGNOSTIC_RESULTS.json`. Nothing was purchased.

## 1. Acquisition
- **10/10 files** (ATP + WTA 2021–2025) downloaded through the in-app browser with Fraser's authorisation. The sandbox and Mac shell
  proxies return HTTP 403 for this site.
- The SHA-256 of every file was computed from the server response before saving, and each matches the saved copy
  (`tennis_data_co_uk/SHA256SUMS`).
- The raw files live in `data/raw/tennis/tennis_data_co_uk/` on the Mac and are gitignored. Provenance and hashes are committed.
- One sheet per file: ATP 2,489–2,703 and WTA 2,369–2,505 rows a year.
- **Odds columns:** B365 and PS every year, BFE (Betfair Exchange) in 2025 only, plus Max/Avg (aggregates, not executable).
- **No timestamps.** Odds are the "most recent before play starts" (provider notes).

## 2. Linkage audit
| | our Betfair rows | matched uniquely | ambiguous | unmatched name / date | winner agreement | excluded retired/W.O. | failed B365 validity |
|---|---|---|---|---|---|---|---|
| ATP | 12,202 | 10,765 (88.2%) | **0** | 1,315 / 122 | **99.95%** (5 excluded) | 311 | 81 |
| WTA | 10,352 | 9,229 (89.2%) | **0** | 1,116 / 7 | **99.96%** (4 excluded) | 304 | 12 |
- Matched and completed, by year: ATP 1,964 / 2,076 / 2,067 / 2,195 / 2,147 · WTA 1,734 / 1,727 / 1,684 / 1,777 / 1,999 (2021 → 2025).
- Price coverage: B365 99.8%, PS 99%, **BFE 5%** (part of 2025 only).
- This is the first real-data validation of the project's `player_names` matcher: 0 ambiguous matches and 99.95% winner agreement.

## 3. Data-quality finding (Amendment A1)
tennis-data contains corrupt price rows (e.g. B365W 29.0 / B365L 0.967). Because an error recorded in Winner/Loser orientation
becomes "value" only when the favourite **won**, it **leaks the outcome**. Unscreened, the ATP misaligned variant showed an absurd
+93% mean estimated EV and +77% ROI; 4 corrupt rows produced most of that. A generic validity screen (both prices > 1.01, overround
0.98–1.20) removes 81 ATP and 12 WTA rows. **Lesson: tennis-data needs row-level validation before any use.**

## 4. Results (bsv2-1 gates; ROI per unit, 95% bootstrap CI)
| variant | timing | tour | favourites | qualifying | per 100 matches | est. EV | win / P | ROI (CI) |
|---|---|---|---|---|---|---|---|---|
| V1 frozen Betfair T−30 P vs B365 close | **MISALIGNED** | ATP | 10,377 | 143 | 1.38 | +37.6% | 65% / 71% | +21.4% (+4.7, +38.0) |
| | | WTA | 8,913 | 162 | 1.82 | +23.8% | 66% / 67% | +21.2% (+6.7, +35.7) |
| V1, only if T−30 P within 0.10 of the PS close | misaligned (sensitivity) | ATP | 10,198 | 52 | 0.51 | +5.1% | 56% / 62% | −5.4% (−30, +18) |
| | | WTA | 8,725 | 93 | 1.07 | +4.3% | 57% / 60% | −2.3% (−21, +16) |
| **V2 BFE close vs B365 close (2025)** | **ALIGNED** | ATP | 517 | **1** | 0.19 | +2.4% | — | n = 1 |
| | | WTA | 482 | **2** | 0.41 | +2.9% | — | n = 2 |
| **V3 Pinnacle close vs B365 close** (reference, not the frozen engine) | **ALIGNED** | ATP | 10,326 | 99 | 0.96 | +3.9% | 58% / 58% | +5.0% (−12.9, +22.8) |
| | | WTA | 8,823 | 94 | 1.07 | +4.1% | 56% / 59% | −0.6% (−18.6, +16.7) |
| All favourites at B365 close, no value filter | — | ATP / WTA | ~10.4k / ~8.9k | — | — | — | calibrated | **−3.3% / −3.8%** (CIs < 0) |
| Self-check: BFE close vs its own de-vig, 5% commission | aligned | both | ~500 | **0** | 0 | — | — | as expected |

## 5. Reading
1. **V1's positive ROI is not evidence.**
   - In 97% (ATP) / 92% (WTA) of V1 "value" bets, the aligned Pinnacle close moved *against* the selection, and only 9–16% remain
     value against it.
   - Removing the ~1% of matches where the T−30 Betfair price and the close disagree by > 0.10 wipes out the effect.
   - The likely mechanism is stale or in-play-contaminated historical LTP when a match started earlier than scheduled, which leaks
     information into P.
   - The same contamination barely touches engine calibration: ≥80% band ATP 87.9% → 87.8%, WTA 88.4% → 88.2% when excluded
     (0.6% / 1.0% of holdout-year matches). **Frozen-engine validation is unaffected.**
2. **Time-aligned closing comparisons show value is rare and unproven.**
   - Bet365 closes above an exchange-derived fair price by ≥ 2% in 0.2–0.4 of 100 favourite matches (2025, BFE).
   - It closes above Pinnacle-fair in about 1 per 100, with ROI indistinguishable from zero.
3. **Accuracy without value loses:** backing every favourite at the Bet365 close gives −3.3% / −3.8%, the same pattern as football.
4. Consistent with football (V2-6H): opportunities at UK retail closing prices are rare; any edge would have to come from *earlier*
   prices, which free data cannot show.

## 6. Can a valid executable historical backtest be built from free data?
**No.** Free data has closing-only, untimestamped quotes; one UK book (B365); exchange prices for only ~5% of rows; and no pre-close
prices. Our frozen P (T−30 LTP) cannot be legitimately paired with them. The only time-aligned tests are closing-vs-closing, which
answer a different question (closing efficiency) and cannot simulate a decision.

## 7. The paid replay after this audit
- **Still impossible with free data:** decision-time (e.g. T−24 h … T−30 min) UK bookmaker quotes; Betfair back/lay before the
  close; more than one UK book; an exchange-derived P aligned with those quotes.
- **Cannot be verified for free:** historical tournament-key coverage and `betfair_ex_uk` back/lay presence in past snapshots. The
  historical endpoints are paid-only [V], so the pilot *is* the verification step.
- **Credits (verified unit: 10 per market per region per sport-key snapshot; empty = free):**
  - Pilot: Wimbledon + US Open 2024, both tours, ~56 key-days × 1 snapshot = ~560, plus ~60 events calls (1 each) ≈ **~620 credits**.
  - Full replay: 2024–25 covered key-days 812 × 2 snapshots = **~16,240** (fits the 20K plan).
  - Both sit inside one **$30** month.
- **Worth it?** The free evidence lowers expectations: at closing, aligned value is ~0.2–1 per 100 favourite matches, with ROI
  ≈ 0. The paid replay's distinct value is measuring **frequency and value at decision time** (earlier prices, where soft books are
  slower). That is the one question neither free data nor football can answer, and it would otherwise take months of live collection.

## 8. Limitations
- Closing semantics are provider-defined (no timestamps).
- Pinnacle is not a UK-available book (a reference only).
- BFE here is a single closing price (back vs mid unknown).
- Retirements are excluded.
- Amendment A1 is post-hoc (disclosed; raw results kept).
- 12% of our matches are unmatched (name / date).
