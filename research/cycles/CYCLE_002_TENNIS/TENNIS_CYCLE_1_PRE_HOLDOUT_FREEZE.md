# Tennis Cycle 1 -- Pre-Holdout Freeze

**STATUS: EVALUATED, 2026-09-15. VERDICT: PARTIAL.** The one-time 2025
evaluation (`scripts/run_cycle_002_tennis_2025_holdout.py`) has been run
exactly once, after the section 9 correction below and a passing seal
check. Full numbers and the mechanical verdict are in
`TENNIS_CYCLE_1_2025_HOLDOUT_REPORT.md`. Headline: the log-loss delta
favoured Global Elo (-0.0088) but its 95% CI, [-0.0202, 0.0016], includes
zero -- inconclusive, not a clean PASS, and not a FAIL either (AUC 0.6925
and calibration slope 0.8130 both comfortably clear their bands). Per
section 11 / the operator's PARTIAL branch: the model is NOT modified in
response to this result. This document's specification remains frozen
exactly as approved; no further evaluation of 2025 will occur under this
cycle's name.

This document exists to be approved BEFORE the sealed 2025 holdout is ever
evaluated, per the research operator's explicit instruction: "Before opening
2025 we need: final candidate model specification; final hyperparameters;
final feature set; final calibration method; frozen evaluation metrics; tests
passing; explicit pre-holdout protocol committed." Everything below is that
freeze. A dedicated, purpose-built evaluation script re-runs EXACTLY this
frozen specification against 2025 once, and the result is recorded as-is --
PASS, PARTIAL, or FAIL -- with no further tuning permitted afterward under
this cycle's name.

**Correction (2026-09-15, same day, applied BEFORE 2025 was opened)**: the
operator's review of this freeze flagged a genuine ambiguity in the original
section 9 -- a FAIL clause ("the CI doesn't exclude zero favourably") and a
PARTIAL clause ("a favourable point estimate but an inconclusive CI") could
describe the exact same result, leaving the rule non-mechanical. Section 9
below has been rewritten as a single, strictly ordered, mutually exclusive
and exhaustive decision function -- `classify_holdout_result` in
`src/prediction_markets_lab/research/holdout_verdict.py` -- with 19 unit
tests (`tests/unit/test_holdout_verdict.py`) proving every boundary case maps
to exactly one verdict. No other section of this freeze changed. This
correction was committed before any 2025 row was read by any script.

**Naming note**: "Tennis Cycle 1" here is the operator's name for this first
frozen model/holdout-test within the tennis initiative. It is not the same
number as the repo's own `CYCLE_002_TENNIS` directory (which refers to this
being the project's second overall research cycle, after football Cycle 1).
Both names are correct in their own numbering scheme; this note exists only
so nobody confuses the two when reading the repo.

## 1. Dataset version (frozen)

- Canonicalisation version: `tennis_cycle_002_canonical_v0.1.0`
- File: `data/processed/tennis/cycle_002_canonical_matches.csv`
- SHA-256: `03043d3387e0d9dfe72cf3b79a8f9f9cfc5e444a3ce637f49e68403b0f7daf91`
- Counts: 14,668 total raw rows -> 14,564 canonical rows (99 walkovers + 5
  confirmed upstream duplicates excluded; 410 retirements kept and flagged,
  not excluded; 143 / 114 rows missing player_a/player_b rank respectively,
  never imputed).
- Season split (via the TML-file-derived `_season` label, the pipeline's
  ground-truth partition -- not an arbitrary calendar cut):
  - **2021, 2022, 2023 -- TRAINING** (k_factor calibration, calibration-fit,
    step-D feature fitting all happened here only)
  - **2024 -- VALIDATION** (every metric reported in A4_BASELINE_RESULTS.md,
    A4_STEP_D_INCREMENTAL_FEATURES.md, and A4_CALIBRATION_RESEARCH.md)
  - **2025 -- SEALED HOLDOUT.** Not loaded by any script to date. This freeze
    exists to define exactly what happens when it finally is.

## 2. Eligibility rules / exclusions (frozen, from Workstream A2)

- Walkovers excluded entirely (no real match played).
- 5 confirmed upstream duplicates excluded (identical tourney/players/round/
  score under a different `match_num`) -- first occurrence kept.
- Retirements KEPT, flagged via the `retired` column, no special handling
  (a documented simplification: a retirement still has a real winner).
- Missing rank/rank_points is NEVER imputed -- flagged via
  `player_a_rank_missing` / `player_b_rank_missing`; the ranking-only
  baseline excludes these matches, both Elo models score every match.
- `player_a` / `player_b` assignment is by ID sort order (whichever of
  winner_id/loser_id sorts first lexicographically) -- carries zero outcome
  information (verified: 50.7%/49.3% real split on the full dataset).
- Post-match stat columns are suffixed `_POST_MATCH_LEAKAGE` and are not
  used as features anywhere in this model.

## 3. Model specification (frozen)

**Global Elo** (`src/prediction_markets_lab/models/tennis_elo.py`,
`global_rating_key`) is the sole candidate model.

- `initial_rating = 1500.0`
- `k_factor = 32.0`, selected via training-only (2021-2023) log-loss
  minimisation over the predeclared candidate grid `[16.0, 24.0, 32.0, 40.0,
  48.0, 64.0]` (`calibrate_k_factor`) -- this is deterministic given the
  training data and grid, not re-tuned per split.
- Rating key: ONE rating per player, shared across every surface
  (`global_rating_key(player_id, surface) -> player_id`).
- Update rule (symmetric, zero-sum): for a match between A and B with
  pre-match ratings `r_a`, `r_b`, expected score
  `e_a = 1 / (1 + 10^(-(r_a - r_b)/400))`; after the result,
  `delta = k_factor * (outcome_a_won - e_a)`; `r_a_new = r_a + delta`,
  `r_b_new = r_b - delta`.
- Prediction: `p_a_win = e_a` computed from PRE-MATCH ratings only
  (`get_rating()` is always called before `update()` for the same match --
  `simulate_pre_match_ratings`'s leakage-safety guarantee, unit-tested).
- Ratings are simulated continuously and chronologically across
  2021-2023-and-2024 together for the (already-reported) validation phase;
  for the 2025 evaluation, ratings continue to accumulate continuously
  through 2021-2024-and-2025 together (a player's rating going into 2025
  reflects their real career history, not a reset) -- k_factor stays fixed
  at 32.0, never re-calibrated using 2025 data.

## 4. Feature set (frozen: Elo alone, nothing else)

No feature beyond the Elo-implied win probability is used. Every
alternative tested was explicitly NOT promoted and stays frozen as a
rejected/negative result, not retried under this cycle:

- **Surface Elo V1**: NEGATIVE / DOES NOT PROMOTE (A4_BASELINE_RESULTS.md).
  Worse than Global Elo out of sample (delta +0.0090, 95% CI [0.0011,
  0.0175]).
- **Ranking-only baseline**: a useful sanity floor, not the candidate --
  Global Elo beat it (delta -0.0122, 95% CI [-0.0230, -0.0017]).
- **Recent form beyond Global Elo**: NULL (A4_STEP_D, delta 0.0000, CI
  [-0.0002, 0.0003]).
- **Surface-specific form beyond Global Elo**: NULL (delta -0.0003, CI
  [-0.0014, 0.0009]).
- **Congestion/rest beyond Global Elo**: NULL (delta -0.0009, CI [-0.0052,
  0.0038] -- directionally consistent across every stability slice checked,
  but the corrected CI still includes zero).

Any of these being revisited later (e.g. a shrinkage/hierarchical surface
model) is explicitly a NEW, separately pre-registered specification -- never
a retrofit of this frozen one.

## 5. Calibration (frozen: NONE)

Per `A4_CALIBRATION_RESEARCH.md`: a 2-parameter logistic recalibration fit
on 2021-2023 training predictions (intercept=0.0267, slope=0.9783 -- close
to identity) was applied unchanged to 2024 validation predictions. Result:
log loss 0.6244 (calibrated) vs 0.6248 (raw), 95% CI [-0.0009, 0.0001] --
includes zero. Per the pre-stated decision rule (adopt only if the CI lies
entirely below zero), calibration was NOT adopted. **Raw Global Elo
probabilities are used unchanged.** This calibration research is not
repeated with 2025 folded in before the 2025 evaluation -- doing so would
itself be a form of peeking.

## 6. Evaluation metrics (frozen)

For the 2025 evaluation, exactly the same metrics already used throughout
this cycle, no additions or substitutions:

- Log loss (primary)
- Brier score
- Calibration bins (equal-count, 10 bins where n permits) + Expected
  Calibration Error
- Calibration intercept/slope (2-parameter logistic fit, reported not
  applied)
- AUC (secondary, discrimination only -- never a promotion criterion on
  its own)
- Subgroup diagnostics: by surface, tourney_level, best_of, and rank-gap
  decile (same bucketing logic as A4_BASELINE_RESULTS.md section 5) --
  reported for transparency, not used to cherry-pick a favourable slice.

## 7. Bootstrap method (frozen)

Paired percentile bootstrap: resample match indices with replacement,
`n_bootstrap = 2000`, `seed = 20260915` (the same seed used throughout A4,
step D, and the calibration research). The comparison for the primary
PASS/PARTIAL/FAIL test (§9) is Global Elo vs. the ranking-only baseline on
the SAME 2025 rows (paired), with a plain 95% CI (2.5/97.5 percentiles) --
a single comparison, so no multiple-testing correction is needed here
(unlike step D's 3-family test).

## 8. Random seeds (frozen)

`BOOTSTRAP_SEED = 20260915` is the only stochastic element anywhere in this
pipeline (used for bootstrap resampling only). Elo simulation and logistic-
regression IRLS fitting are fully deterministic given the data and config
above -- no other seed exists to freeze.

## 9. Explicit 2025 PASS / PARTIAL / FAIL criteria (decided now, never after seeing 2025)

**Corrected 2026-09-15** (see the correction note above) to remove an overlap
between the original FAIL and PARTIAL clauses. The rule below is implemented
as a single, ordered, mutually exclusive and exhaustive function --
`classify_holdout_result` in
`src/prediction_markets_lab/research/holdout_verdict.py` -- with unit tests
(`tests/unit/test_holdout_verdict.py`) proving every boundary case maps to
exactly one verdict. The evaluation script (section 11) calls this function
directly on the computed 2025 metrics; nobody reads the 2025 numbers and
picks a verdict by eye.

Let `delta = Global Elo log loss - ranking baseline log loss` on the 2025
holdout (same-match common sample, i.e. matches where both models have a
prediction), with a paired-bootstrap 95% CI `[ci_lower, ci_upper]` on delta
(method: section 7). Evaluated in this fixed order:

**FAIL** -- any ONE of these alone is disqualifying, never combined with
another condition to reach a different verdict:
1. `ci_lower > 0.0` -- the CI lies entirely above zero: Global Elo is
   statistically significantly WORSE than the ranking baseline on 2025, not
   merely inconclusive.
2. 2025 AUC `< 0.65`.
3. 2025 calibration slope `< 0.4` or `> 1.6` (catastrophic drift) -- this
   alone fails the cycle regardless of how the log-loss CI reads.

**PASS** -- only if NONE of the FAIL conditions above triggered, AND all
three of:
1. `ci_upper < 0.0` -- the CI lies entirely below zero: Global Elo is
   statistically significantly better than the ranking baseline on 2025.
2. AUC `>= 0.65` (already guaranteed by not failing condition 2 above).
3. Calibration slope in `[0.7, 1.3]`.

**PARTIAL** -- everything else (the only remaining case, by construction):
- the CI includes zero (`ci_lower <= 0.0 <= ci_upper`) -- any favourable
  point estimate is not statistically conclusive at 2025's sample size; or
- the CI is favourable (`ci_upper < 0.0`) and AUC clears the floor, but the
  calibration slope sits outside `[0.7, 1.3]` without being catastrophic
  (i.e. still within `[0.4, 1.6]`) -- "generalises, but not as cleanly as
  2024," not "the model is broken."

A boundary value (a CI bound of exactly zero, an AUC of exactly 0.65, a
slope of exactly 0.4 / 0.7 / 1.3 / 1.6) is resolved by the strict/non-strict
inequalities above, never by judgement at report time -- see the unit tests
for the exact mapping of every such boundary.

Whatever the verdict, it does NOT by itself establish a betting edge (see
section 10).

## 10. What this evaluation does NOT establish, whatever the result

PASS on this holdout means Global Elo's PREDICTIVE performance generalises
out of sample. It does not mean a betting edge exists -- that requires a
market price to compare against (Workstream B, still blocked on Fraser's
Betfair account signup) and a full EV/CLV/liquidity/cost analysis on top of
predictive skill. No live betting, no paper trading, and no strategy
promotion follow from this holdout result alone, whatever it is.

## 11. Process (frozen)

1. This document is reviewed and approved by Fraser/the operator. **Done,
   2026-09-15, subject to the section 9 correction above.**
2. Before 2025 is loaded, a seal-verification check confirms: 2025 has not
   previously been loaded by any research/model script in this repo; no
   2025-derived statistic informed any model-selection decision recorded in
   this freeze; the canonical dataset's SHA-256 matches section 1; the full
   test suite passes; and the working tree for this cycle's tracked files
   is clean at the moment of running. If any of these fail: STOP, do not
   evaluate the holdout.
3. Only after that check passes, a dedicated script
   (`scripts/run_cycle_002_tennis_2025_holdout.py`) loads 2025 for the first
   time, re-runs the frozen model spec above unchanged, and evaluates it
   against the criteria in §9 -- exactly once, via
   `classify_holdout_result` (never by eye).
4. The result -- PASS, PARTIAL, or FAIL -- is recorded honestly in
   `TENNIS_CYCLE_1_2025_HOLDOUT_REPORT.md`, with no retrying, no
   threshold-loosening, and no silent model changes after seeing 2025.
   Pre-registered subgroup diagnostics (section 6) are reported as
   diagnostics only; an interesting subgroup discovered after opening 2025
   is recorded as a FUTURE HYPOTHESIS -- NOT VALIDATED, and does not change
   this cycle's verdict.
5. Any model change made AFTER this point (rescuing Surface Elo, revisiting
   a null feature, adjusting k_factor, adding calibration, tuning anything
   against the 2025 result) is explicitly a NEW research cycle, not a
   continuation of Tennis Cycle 1.

## 12. Code and commit references (frozen)

- `679cf74` -- Workstream A1 audit + odds-source search (first pass)
- `1d7736e` -- Workstream A2 canonicalisation
- `b8eb396` -- Workstream A3 exploratory analysis
- `0b4b0a1` -- A4 infrastructure (binary metrics, logistic regression, tennis Elo)
- `9d22373` -- A4 baselines A-C (ranking / global Elo / surface Elo)
- `3ee12cf` -- Surface Elo freeze + Workstream B Pass 2
- `48c4f1b` -- A4 step D incremental features (clean null)
- `b86a673` -- Calibration research (CALIBRATION = NONE)

All local, unpushed as of this freeze -- Fraser pushes from his own
Terminal.
