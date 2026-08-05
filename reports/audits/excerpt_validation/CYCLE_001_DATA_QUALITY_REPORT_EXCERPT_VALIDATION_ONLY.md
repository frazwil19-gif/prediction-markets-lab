# CYCLE_001 Data Quality Report

**Scope: the 29-match excerpt sample acquired in this session (see
CYCLE_001_DATA_ACQUISITION_REPORT.md). Findings here are real and
computed from genuine data, but the sample size is small — treat
percentages as indicative, not as final Cycle 1 data-quality
statistics.**

## Schema

`reports/audits/football_data_schema_inventory.csv` — 360 rows, one
per (competition, column) pair across the 3 files. Every column from
the confirmed live schema (see `FOOTBALL_DATA_FEASIBILITY.md`) is
present and categorised (identity/date/result/score/match statistic/
opening odds/closing odds/average odds/maximum odds/Asian handicap/
totals). E0 and E1 have byte-identical column sets; SC0 has the same
header but with more per-bookmaker blanks in this small sample (see
below).

## Missing odds

Real, counted values from the 348 extracted bookmaker triplets:

- **6 of 6 known bookmakers** (Bet365, BetWin, Betfair Exchange,
  Pinnacle, William Hill, 1xBet) quoted **both opening and closing**
  prices for **every one of the 10 E0 rows and 10 E1 rows** in the
  sample — 0% missing in this subset.
- SC0 had a small number of genuine blanks even in this 9-row sample
  (e.g. William Hill's closing triplet missing for the St Mirren vs
  Hibernian and St Johnstone vs Aberdeen matches, confirmed directly
  in `tests/unit/test_football_bookmaker_extraction.py::test_real_sc0_row_with_a_genuinely_missing_bookmaker`)
  — correctly treated as "did not quote," not as zero or an error, per
  `ingestion.football_bookmaker_extraction`.

## Complete bookmaker counts

All 29 matches had 6 complete bookmaker markets at opening (100% of
the maximum possible in this schema). See
`reports/audits/football_bookmaker_coverage.csv` for the exact
per-bookmaker, per-timing counts (all real, computed values).

## Duplicate findings

None found in this sample (`reports/audits/football_duplicate_review.csv`).
With only one season and 29 rows, meaningful duplicate/reschedule
detection has not really been exercised — this check needs to be
re-run once multi-season data is loaded, where genuine reschedules
(postponed fixtures played on a different date) are much more likely
to actually occur.

## Team-normalisation issues

None — all 40 distinct raw team names in the sample resolved
successfully against `config/football_team_aliases.yaml`
(`reports/audits/unresolved_team_names.csv`). This is expected and not
very informative yet: the alias table was seeded directly from these
same teams. The real test of the normalisation table comes once
multi-season data introduces promoted/relegated clubs not in the
current 2024/25-only alias list.

## Consensus validity check

All 58 consensus rows (29 matches × 2 timings) have
`probability_sum_check` (median home + median draw + median away fair
probability) between 0.9952 and 1.0065 — i.e. within ~0.7% of the
theoretical 1.0, which is the expected behaviour for a median-based
consensus of margin-free probabilities (medians of several
approximately-1.0-summing distributions won't sum to exactly 1.0, but
should be close). No consensus row summed to an implausible value,
which would have indicated a bug in the margin-removal or extraction
pipeline.

## Outcome/consensus eligibility

29/29 matches eligible for outcome modelling (valid FTR present).
29/29 matches eligible for consensus modelling (≥4 complete bookmaker
markets — the configured minimum in
`config/thresholds.yaml`/research design; actual count was 6/6 for
every match). 0 exclusions
(`reports/audits/cycle_001_exclusions.csv`).

## Known limitations of this quality report

1. Sample size (29 matches) is far too small to draw any conclusion
   about data quality across the full ~1,700+ match, 5-season target
   dataset — it only proves the pipeline mechanics are correct.
2. Only one season (2024/25) has been inspected; column-count
   variation across seasons (122 columns in 2024/25 vs. 108 in
   2020/21-2023/24, per the original feasibility audit) has not been
   re-verified against actually-downloaded older-season files in this
   session.
3. No cross-season duplicate/reschedule patterns have been tested.
4. Bookmaker coverage in this specific sample (100% for 6/6
   bookmakers) is unusually clean — the original feasibility audit did
   observe blank bookmaker cells elsewhere in the same 2024/25 E0
   season (e.g. December 2024 matches), so the true missing-data rate
   across a full season is very likely non-zero even for E0/E1, and
   should not be assumed to be 0% based on this sample alone.
