# Tennis Cycle 1 -- Pre-Holdout Freeze

**STATUS: AWAITING APPROVAL. 2025 HAS NOT BEEN OPENED. No script in this repo
has read a 2025 row for modelling purposes as of this freeze.**

This document exists to be approved BEFORE the sealed 2025 holdout is ever
evaluated, per the research operator's explicit instruction: "Before opening
2025 we need: final candidate model specification; final hyperparameters;
final feature set; final calibration method; frozen evaluation metrics; tests
passing; explicit pre-holdout protocol committed." Everything below is that
freeze. Once Fraser/the operator approves this document, a dedicated,
purpose-built evaluation script is written that re-runs EXACTLY this frozen
specification against 2025 once, and the result is recorded as-is --
PASS, PARTIAL, or FAIL -- with no further tuning permitted afterward under
this cycle's name.

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

**PASS** -- all three:
1. Global Elo beats the ranking-only baseline on 2025 (paired bootstrap,
   same-match common sample where both have a prediction): the 95% CI for
   (Global Elo log loss - ranking baseline log loss) lies entirely below
   zero.
2. Global Elo's 2025 AUC >= 0.65 (meaningfully better than chance
   discrimination; 2024's was 0.6991).
3. Global Elo's 2025 calibration slope is in [0.7, 1.3] (no severe
   miscalibration/drift; 2024's was 0.8749).

**FAIL** -- any of:
1. The 95% CI for (Global Elo - ranking baseline) log loss does NOT
   exclude zero in Global Elo's favour (i.e. includes zero, or Global Elo
   is worse).
2. AUC < 0.65 (discrimination has collapsed toward chance).
3. Calibration slope falls outside [0.4, 1.6] (severe drift) AND the log-
   loss CI also fails to exclude zero (both signals bad together, not one
   borderline number alone).

**PARTIAL** -- everything not covered by PASS or FAIL above: e.g. the
log-loss CI excludes zero in Global Elo's favour but AUC or calibration
slope falls slightly outside the PASS band, or the point estimate favours
Global Elo but the CI is inconclusive given 2025's sample size. A PARTIAL
result means "the model generalises somewhat but not as cleanly as 2024,"
not "the model is broken" -- it is reported honestly either way, and
whatever the verdict, it does NOT by itself establish a betting edge (see
§10).

## 10. What this evaluation does NOT establish, whatever the result

PASS on this holdout means Global Elo's PREDICTIVE performance generalises
out of sample. It does not mean a betting edge exists -- that requires a
market price to compare against (Workstream B, still blocked on Fraser's
Betfair account signup) and a full EV/CLV/liquidity/cost analysis on top of
predictive skill. No live betting, no paper trading, and no strategy
promotion follow from this holdout result alone, whatever it is.

## 11. Process (frozen)

1. This document is reviewed and approved by Fraser/the operator.
2. Only after approval, a new, dedicated script (not yet written) loads
   2025 for the first time, re-runs the frozen model spec above unchanged,
   and evaluates it against the criteria in §9 -- exactly once.
3. The result -- PASS, PARTIAL, or FAIL -- is recorded honestly in a
   results document, with no retrying, no threshold-loosening, and no
   silent model changes after seeing 2025.
4. Any model change made AFTER this point (rescuing Surface Elo, revisiting
   a null feature, adjusting k_factor, adding calibration) is explicitly a
   NEW research cycle, not a continuation of Tennis Cycle 1.

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
