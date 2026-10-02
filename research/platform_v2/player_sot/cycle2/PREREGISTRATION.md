# Player SOT — Cycle 2: generalisation and modern-data validation (PRE-REGISTRATION)

Written and committed 2026-10-02, BEFORE any modern player data has been acquired or inspected.

The pilot (`player_sot/pilot/`, PILOT_SIGNAL on 2017-18 Wyscout data) is preserved untouched. Nothing here retunes it.

**Status entering this cycle: PILOT_SIGNAL / FULL_VALIDATION_JUSTIFIED.** This is not a validated betting edge.

## Question
Does the sports-only Player SOT signal generalise across seasons to modern football, and (Phase 3, separately
pre-registered) does it remain useful against a modern betting market?

## Pilot limitations this cycle must address
| Limitation | How this cycle addresses it |
|---|---|
| One old season | Modern seasons, with the holdout a full later season (temporal generalisation) |
| Poorly calibrated simple baseline | Adds B2, the recalibrated player-rate baseline; comparator chosen on development |
| No market comparison | Phase 3: A/B/C against the Betfair player-SOT market, pre-registered before any price is inspected |
| No modern-data evidence | Phase 1 data gate on modern data |
| Confirmed-starter assumption | Kept explicitly: the model is POST-LINEUP. Operational consequence: prices must be captured after lineups (about T−60 to T−0). A pre-lineup model is out of scope. |

## Data — minimum modern sample (computed before acquisition)
- **Pilot uncertainty:** the 1+ SOT Δ had a 95% CI half-width of about 0.0036 at n = 10,780 (match bootstrap).
- **Target precision:** to confirm a smaller modern effect with materiality Δ ≤ −0.004 and CI upper < 0, a half-width
  of ≤ 0.004 is required.
  - So n ≥ 10,780 × (0.0036 / 0.004)² ≈ 8,700 holdout starter-matches.
  - That is about one EPL season of outfield starters: 380 × 20 = 7,600, or about 7,000 after the history requirement.
- **Minimum design:** EPL 2022-23 (training and development) plus EPL 2023-24 (sealed holdout).
  - That is about 40 API-Football requests (20 per season via `fixtures?ids=`).
  - **If the holdout ends below 8,700 eligible rows,** add EPL 2024-25 as a second holdout season (+20 requests)
    before opening anything. This is decided by row count alone, from a count-only query.
- **Not acquired:** other leagues or extra seasons.
- **Source:** API-Football, only after Fraser has sufficiently clear permission. Raw and player-level data stay in
  `data/private/` (gitignored). Only aggregates are committed.

## Phase 1 — modern data gate (before any modelling)
Using `research_shadow/player_sot.audit`:
- 11 starters per team-match in ≥ 99% of team-matches;
- duplicates = 0;
- SOT ≤ shots and goals ≤ SOT violations < 0.1%;
- team SOT per match within ±5% of Football-Data `HST`/`AST` for the same fixtures (provider-definition check);
- minutes coverage ≥ 99%.

Failure stops the cycle with the reason recorded.

## Phase 2 — model cycle
- **Population:** outfield starters with ≥ 3 prior appearances in the data. Minutes are the exposure only, never a
  feature.
- **Targets:**
  - PRIMARY: `sot_1plus`;
  - SECONDARY: `sot_2plus`.
- **Periods:**
  - TRAIN: 2022-23 matches before 2023-02-01;
  - DEVELOPMENT: 2022-23 matches from 2023-02-01;
  - SEALED HOLDOUT: 2023-24 full season (plus 2024-25 if required by the sample rule), refit on all of 2022-23.
  - The holdout is opened once, after `FROZEN_SPEC.json` is committed, via `player_sot.HoldoutGuard`.
- **Feature families:** the pilot's families only:
  - player prior SOT/90 and shots/90 (shrunk, last 10 appearances);
  - prior starts share;
  - role;
  - team prior SOT for;
  - opponent prior SOT conceded;
  - home.

  Family-level forward selection on development: add a family only if it improves development log loss by
  ≥ 0.0005. No new feature families in this cycle.
- **Structure comparison** (the pre-registered answer to the position question):
  - **S1 — universal:** one logistic model, role as dummies (the pilot structure).
  - **S2 — position-aware:** one logistic model plus role × (player SOT/90, team SOT for, opponent SOT conceded)
    interactions.
  - **S3 — position-specific:** separate logistic models for DF, MD and FW.
  - **Choice:** best development log loss for `sot_1plus` over ALL outfield starters. The simpler structure
    (S1 < S2 < S3) is preferred if within 0.0005.
  - **No subgroup selection:** the verdict is always computed on all outfield starters. Per-position results are
    reported, never used to choose a betting subgroup.
- **Baselines:**
  - B0: role × league rate.
  - B1: the pilot player-rate Poisson.
  - B2: B1 recalibrated by logistic intercept/slope fitted on TRAIN.
  - Comparator: the best of B0–B2 on development `sot_1plus` log loss.
- **Transfer check (secondary, reported only):** the frozen pilot model's coefficients applied unchanged to the
  modern holdout. This tests a pure transfer of the old fitted model.
- **Metrics:**
  - log loss (primary);
  - Brier;
  - calibration intercept and slope;
  - reliability by decile;
  - AUC;
  - match-cluster bootstrap 95% CI (1,000 resamples, seed 7).

## Verdict (fixed)
**MODERN_VALIDATED** iff all of these hold on the sealed holdout for `sot_1plus`:
1. Δlogloss vs comparator ≤ −0.004 with CI upper < 0;
2. calibration slope in [0.85, 1.15] and |intercept| ≤ 0.10;
3. Δ < 0 for each of DF, MD and FW with n ≥ 1,000 (position stability);
4. Δ < 0 in both halves of the holdout season (temporal stability);
5. holdout N ≥ 5,000. Below that, the result is REPORT_ONLY with no verdict.

Otherwise **NOT_VALIDATED**: the null is recorded and the model is not rescued on these data.

`sot_2plus` is reported with the same metrics as a secondary result.

**MODERN_VALIDATED leads to Phase 3 (market comparison against Betfair player-SOT, A/B/C as for corners,
separately pre-registered before any price is inspected).** It is never directly a betting rule.
