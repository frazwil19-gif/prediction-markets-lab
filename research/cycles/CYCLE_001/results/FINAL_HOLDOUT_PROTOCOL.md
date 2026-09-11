# Final Holdout Protocol (Stage 3B, Checkpoint 5)

**This document is the pre-registration for Checkpoint 6 — the sealed
2024/25 holdout evaluation. It is written and committed BEFORE the holdout
season is read by any script. Once committed, it may not be edited to
change what will be measured, how, or what counts as a passing result. Any
change discovered to be necessary after the holdout is opened invalidates
the run (see "Verdict rubric" §5, INVALID) rather than being applied
retroactively.**

## 1. What is frozen at the moment this protocol is committed

- Data version: `cycle_001_v1.0.0-20260910T234139` (`reports/audits/CYCLE_001_FREEZE_RECORD.json`,
  unchanged since Stage 3A).
- Code commit: `6195fbf2a11d3da6705e4e418532ea4676011123` (Checkpoint 4,
  "research: run blends + bootstrap CIs + calibration across development
  folds") — every model definition (`models.football_elo`,
  `models.football_poisson`, `models.football_blended`), every metric
  (`performance.log_loss`, `performance.brier`, `performance.calibration`),
  and the bootstrap procedure (`probability.uncertainty`) are frozen as of
  this commit. No model, hyperparameter, metric definition, or blend
  combination may change between this protocol's commit and Checkpoint 6's
  execution.
- This protocol document itself, once committed (the "STAGE 3B PRE-HOLDOUT
  FREEZE" commit).

A companion machine-readable freeze record,
`reports/audits/STAGE_3B_PRE_HOLDOUT_FREEZE.json`, hashes this protocol
document and records the frozen commit, so a later script can verify (like
`verify_frozen_data_hashes.py` does for the raw data) that nothing in the
frozen set drifted between pre-registration and execution.

## 2. The holdout itself

- **Season: 2024/25, all 3 competitions (E0, E1, SC0). Never read by any
  Checkpoint 1-5 script** — enforced by construction (`load_matches()` in
  every prior checkpoint script filters to `DEVELOPMENT_SEASONS` and
  asserts the holdout season is absent) and verified by each checkpoint's
  own seal-guard test.
- **Predeclared expected coverage** (computed once, now, before opening —
  any deviation found when Checkpoint 6 actually reads this data is itself
  a finding to report, not to silently absorb):
  - Full coverage: 1,160 matches (E0: 380, E1: 552, SC0: 228).
  - Common sample (eligible for the consensus model AND a usable closing
    consensus present): **1,160 matches — identical to full coverage.**
    Unlike the development folds (where 34 of 3,480 matches, ~1%, lacked
    usable market data), every 2024/25 match has usable closing-consensus
    coverage. This means, uniquely for the holdout, there is no
    full-coverage-vs-common-sample distinction to track — one N applies to
    every candidate including naive.

## 3. Procedure (the one, single run)

This is structurally the natural 4th walk-forward fold — train on ALL 4
development seasons at once, evaluate once on the season after:

    train_seasons = ["2020_21", "2021_22", "2022_23", "2023_24"]
    evaluate_season = "2024_25"

Concretely, in this exact order, with no branching on intermediate results:

1. Verify frozen data hashes (`verify_frozen_data_hashes.py`) AND verify
   this protocol's own hash against `STAGE_3B_PRE_HOLDOUT_FREEZE.json`.
   Refuse to proceed on any mismatch.
2. Fit the naive frequency baseline, Elo (calibrating `draw_margin` on the
   4 development seasons via the same predeclared candidate grid used
   throughout Stage 3B), and Poisson, all using the full 4-season
   development period as training/rating history, exactly as each model's
   existing implementation already does for any fold — this is not new
   code, it is the existing per-fold procedure applied to one final fold.
3. Calibrate all 4 blend weight combinations
   (`elo_poisson`, `market_elo`, `market_poisson`, `market_elo_poisson`) on
   the same 4-season training period, via the same predeclared 0.1-step
   grid search used in Checkpoint 4. No new blend combinations.
4. Score every one of the 8 predeclared candidates below on the 2024/25
   common sample: log loss, Brier score, raw calibration (ECE per
   outcome), and paired bootstrap CI vs. market (both match-level and
   block-by-date, n_resamples=2000, seed=42 — identical parameters to
   Checkpoint 4, for direct comparability).
5. Write results to `data/interim/stage_3b_checkpoint6_holdout_metrics.json`
   and `STAGE_3B_FINAL_REPORT.md` in one pass. No re-running with different
   parameters after seeing the numbers.

## 4. Predeclared candidate list (exhaustive — no additions after this point)

| # | Candidate | Already known (development) log loss | Included because |
|---|---|---|---|
| 1 | Naive frequency (Baseline 0) | 1.0689 | Sanity floor |
| 2 | Market closing consensus (Baseline 1) | 0.9773 | The benchmark every other candidate is measured against |
| 3 | Elo (Model 1) | 1.0233 | Predeclared Stage 3B model |
| 4 | Poisson (Model 2) | 1.0097 | Predeclared Stage 3B model |
| 5 | `elo_poisson` blend | 1.0035 | Best non-market-degenerate candidate on development folds |
| 6 | `market_elo` blend | 0.9773 (= market) | Completeness — may behave differently on holdout even if it degenerated to pure market on every development fold |
| 7 | `market_poisson` blend | 0.9773 (= market) | Same reasoning as #6 |
| 8 | `market_elo_poisson` blend | 0.9773 (= market) | Same reasoning as #6 |

All 8 are scored regardless of development-fold performance — the holdout
is not used to "confirm" only the promising candidates, it is used to score
every predeclared candidate once. In particular, candidates 6-8 degenerated
to pure market on every development fold; whether that also holds on the
holdout's training data is itself part of what Checkpoint 6 will observe,
not assumed in advance.

## 5. Verdict rubric (predeclared, applied mechanically after the run)

Applied to the **best-performing non-market candidate on the holdout**
(by pooled log loss), using its paired bootstrap CI vs. market on the
holdout sample:

| Verdict | Criterion |
|---|---|
| **STRONG SIGNAL** | The best candidate's log-loss delta vs. market is negative (beats market) AND its 95% CI (both bootstrap methods) lies entirely below zero. |
| **WEAK-UNCERTAIN SIGNAL** | The best candidate's point-estimate delta is negative (beats market) but its CI includes zero, OR the point estimate is very close to zero (\|delta\| < 0.005 log-loss units) in either direction with a CI that includes zero. |
| **MARKET DOMINATES / NULL RESULT** | The best candidate's point-estimate delta is positive (market wins) and its 95% CI lies entirely above zero — i.e., the same pattern already observed on every development fold in Checkpoints 1-4. |
| **INVALID** | A frozen-data hash mismatch, a protocol-hash mismatch, a dataset defect discovered only upon opening the holdout (e.g. a coverage count that does not match §2's predeclared expectation and cannot be explained as an already-documented limitation), or any deviation from the frozen commit's code between pre-registration and execution. An INVALID run is reported as such, not silently corrected and re-run — a new cycle with a new freeze record would be required. |

This rubric is mechanical and pre-committed specifically so that Checkpoint
6's classification cannot be adjusted after seeing which bucket a marginal
result would otherwise fall into.

## 6. What happens after Checkpoint 6, regardless of verdict

- The holdout is opened exactly once. If the result is STRONG SIGNAL,
  WEAK-UNCERTAIN, or MARKET DOMINATES/NULL, Stage 3B is complete and closed
  — there is no "best of N holdout attempts." A second look at the 2024/25
  season under any subsequently modified methodology would be a new
  research cycle (Cycle 2), not a re-run of Cycle 1's Stage 3B.
- `STAGE_3B_FINAL_REPORT.md` is written from whichever verdict actually
  obtains, including a MARKET DOMINATES/NULL RESULT — a clean null result
  answering the Stage 3B research question honestly is a complete and
  valid outcome of this project, not a failure requiring further
  development-fold work to "fix."
- Any staking/EV/execution work (explicitly out of scope for all of Stage
  3B, see `STAGE_3B_PLAN.md` §1) is a separate, later decision gated on
  Stage 3B's actual verdict, not assumed in advance by this protocol.
