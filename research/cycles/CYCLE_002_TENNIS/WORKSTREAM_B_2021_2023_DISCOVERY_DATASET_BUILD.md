# Workstream B — 2021-2023 Discovery Dataset Build (Task #21)

**Date:** 2026-09-16
**Status:** Built. No discovery-family analysis has been run against this
dataset yet (that is Task #22) — this document covers assembly only.
**Script:** `scripts/build_discovery_dataset_2021_2023.py`. Output:
`data/interim/workstream_b_2021_2023_discovery_dataset.csv` (7,668 rows,
37 columns, gitignored per `data/interim/*`).

This build reads `outcome_a_won` into the dataset (Task #22 needs it) but
computes, prints, or inspects no outcome-linked statistic anywhere — every
number in this document is a data-availability count, not a result.

## 1. Population

7,668 rows = every 2021-2023 TML canonical ATP match that is MATCHED under
the frozen linkage spec (7,668 of the 8,588 total 2021-2023 canonical
matches present in the corpus -- 89.3%, consistent with the frozen
linkage's overall 88.96% MATCHED rate). All 7,668 MATCHED-in-2021-2023
links resolved cleanly to a runner-to-player mapping and a final market
time (`skipped` counts in the script's stdout were all zero) -- no
additional rows were dropped at the assembly stage beyond the linkage
step's own AMBIGUOUS/UNMATCHED exclusions.

## 2. Columns and how each of the 13 pre-registered discovery families is covered

| Family | Column(s) |
|---|---|
| 1. Model-market disagreement | `model_market_delta_30min` = `elo_prob_a` − `market_prob_a_30min` |
| 2. Favourite/underdog | derivable from `market_prob_a_30min` > 0.5, or `rank_gap_b_minus_a` |
| 3. Price bands | derivable from `market_prob_a_30min` (discretize as in the coverage audit) |
| 4. Rank gap | `rank_gap_b_minus_a` = `player_b_rank` − `player_a_rank` |
| 5. Elo gap | `elo_prob_a` (a monotonic transform of the underlying rating gap) |
| 6. Elo-vs-ranking disagreement | `elo_vs_ranking_delta` = `elo_prob_a` − `ranking_prob_a` |
| 7. Surface | `surface` |
| 8. Tournament level/format | `tourney_level`, `best_of` |
| 9. Recent/surface form | `player_{a,b}_recent_form`, `player_{a,b}_surface_form` |
| 10. Congestion/rest | `player_{a,b}_rest_days`, `player_{a,b}_matches_last_14d` |
| 11. Time-to-start | `market_prob_a_{24h,6h,1h,30min}` availability lets Task #22 compare disagreement across horizons |
| 12. Cross-horizon price movement | `price_movement_6h_to_30min` = `market_prob_a_30min` − `market_prob_a_6h` |
| 13. Favourite-longshot bias | `market_prob_a_30min` (extreme bands) vs `outcome_a_won` — computed only in Task #22 |

`elo_prob_a` is the FROZEN Global Elo model (k_factor=32.0), reused
unmodified from `run_cycle_002_tennis_checkpoint_a4.run_elo_model`; the
run reconfirmed k_factor=32.0 (the script raises if it doesn't, per the
standing consistency guard) — calibrated on match outcomes only, never on
any market/Betfair data, so this build does not touch the "Elo must never
be retuned using market results" rule. `ranking_prob_a` is the same
frozen ranking-baseline module, likewise unmodified.

## 3. Methodology choices made in this build (recorded for transparency)

- **Market horizon = 30min primary**, per `WORKSTREAM_B_PRICE_COVERAGE_AUDIT.md`
  section 6's recommendation; 24h/6h/1h are also included per match to
  support the time-to-start and cross-horizon-movement families.
- **"Fresh" price definition**: both sides' last-traded price must exist
  and be no older than `max(2x horizon, 1 hour)` — same definition
  established and justified in the price-coverage audit, applied
  identically here.
- **Recent/surface form**: rolling mean of win/loss over the player's
  trailing 10 matches (`FORM_WINDOW=10`), computed with `.shift(1)` before
  the rolling window so the match being predicted is never included in its
  own form calculation — mechanically leakage-safe. Requires >=3 prior
  matches to report a value (`min_periods=3`); earlier matches in a
  player's 2021-2023 history are `NaN`, not zero-filled.
- **Congestion**: count of the player's other matches with `tourney_date`
  in the trailing 14 days, strictly before the current match's date.
- **Rest**: days since the player's immediately preceding match's
  `tourney_date`. Note this is coarse (tournament-start-date granularity,
  the only date resolution TML provides), not the exact match-to-match
  gap — a known limitation to carry into Task #22's interpretation, not a
  new one (the same `tourney_date`-is-not-per-match-date issue already
  documented in the linkage-integrity audit).
- **Form/rest/congestion are computed from ALL 2021-2023 canonical
  matches** (8,588), not just the MATCHED subset — a player's form is a
  real fact about their match history independent of whether that
  particular match happened to link to a Betfair market, so restricting
  form calculation to MATCHED-only would have introduced an artificial,
  Betfair-availability-driven gap into the covariate itself.

## 4. Data-availability counts (real run output)

| Column | N available | % of 7,668 |
|---|---|---|
| `elo_prob_a` | 7,668 | 100.0% |
| `ranking_prob_a` | 7,648 | 99.7% |
| `elo_vs_ranking_delta` | 7,648 | 99.7% |
| `market_prob_a_24h` (fresh) | 4,129 | 53.8% |
| `market_prob_a_6h` (fresh) | 7,291 | 95.1% |
| `market_prob_a_1h` (fresh) | 7,317 | 95.4% |
| `market_prob_a_30min` (fresh) | 7,136 | 93.1% |
| `model_market_delta_30min` | 7,136 | 93.1% |
| `price_movement_6h_to_30min` | 6,927 | 90.3% |
| `player_a_recent_form` | 7,130 | 93.0% |
| `player_a_surface_form` | 6,590 | 85.9% |
| `rank_gap_b_minus_a` | 7,648 | 99.7% |

The 93.1% 30min coverage here is consistent with the price-coverage
audit's 94.2%-of-MATCHED figure computed over the full 2021-2025 corpus
(small difference expected: this is the 2021-2023 subset only, plus the
"fresh" cap is applied identically). No new coverage surprise emerged in
this build.

A random spot-check (2021 Australian Open final, Djokovic vs Medvedev,
`2021-580:127`): `elo_prob_a`=0.466, `market_prob_a_30min`=0.525,
`outcome_a_won`=True (Djokovic won in straight sets, matching the real
historical result) — confirms the assembled row is correctly identified
and internally consistent, not a spot-check of any predictive claim.

## 5. Next gate

Task #22 (run the 13-family discovery analysis on this dataset, reporting
PROMOTE/PARTIAL/REJECT with full statistical rigor and multiple-testing
correction) may now proceed.
