# Football Cycle 2 -- Formal Hypothesis Phase: Development Checkpoint

Answers the operator's 2026-09-17 21-point return list in full, for the
formal pre-registration and development test of H-FB2-001 and
H-FB2-002.

## 1. Exact H-FB2-001 specification

Full A-W specification:
`HYPOTHESIS_PREREGISTRATION_H-FB2-001_H-FB2-002.md`, section 3.
Summary: Dominant-Side Mispricing, derived from BEH-009. Population:
every E0/E1/SC0 match, 2020/21-2024/25, with non-missing 1X2 opening
fair probabilities, AH opening line and fair probabilities (both
sides), and full-time goals. Primary estimand: mean SIGNED AH pricing
residual for the pre-match favourite's own side
(`1{favourite covers} - favourite_cover_probability`), restricted to
the top quartile of favourite strength (recomputed on the combined
development corpus). Two-sided hypothesis (direction not assumed).

## 2. Exact H-FB2-002 specification

Full A-W specification: same document, section 4. Summary: SOT
Differential x Extreme-Favourite Price Band, derived from BEH-004.
Population: every E0/E1/SC0 match, 2020/21-2024/25, with non-missing
1X2 opening home-win probability and both teams' leakage-safe rolling-
last-10 SOT-for figures. Primary estimand: within the top quintile
(index 4) of 1X2 opening home-win probability, the home-win-rate
difference between the top and bottom half of the quintile's own
rolling SOT differential (home minus away). One-sided hypothesis
(positive direction pre-registered).

## 3. Hypothesis Registry entries

Both added to `research/hypotheses/hypothesis_registry.csv`:

| hypothesis_id | linked_behaviour_id | status after this checkpoint | priority |
|---|---|---|---|
| H-FB2-001 | BEH-009 | REJECTED | P1 |
| H-FB2-002 | BEH-004 | BACKTESTING | P2 |

Both validated against the existing `Hypothesis` pydantic schema
(`schemas.py`) and every status transition validated against
`HYPOTHESIS_STATUS_TRANSITIONS` via
`hypothesis_validation.validate_hypothesis_status_transition` before
being written (DEFINED -> REJECTED for H-FB2-001; DEFINED -> BACKTESTING
for H-FB2-002 -- both are allowed transitions).

## 4. Commit proving pre-registration preceded testing

Commit `4757031` ("Football Cycle 2: pre-register H-FB2-001 (BEH-009)
and H-FB2-002 (BEH-004)") introduces the pre-registration document, the
registry rows (status DEFINED, no results yet), and the tested
`football_cycle2_development.py` module -- with zero development-test
scripts or results in the same or any earlier commit. The development-
test scripts (`run_h_fb2_001_development_test.py`,
`run_h_fb2_002_development_test.py`) and their results are introduced
only in the next commit, after `4757031`, per this checkpoint's own
commit log (see point 20).

## 5. Exact development dataset and sample sizes

Both scripts read the frozen `cycle_002_discovery_features.csv`
(5,800 rows total, all five seasons 2020/21-2024/25 combined, per
`CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md`'s finding that no genuine
sealed OOS survives inside this corpus). After each hypothesis's own
missing-data exclusions:

- H-FB2-001: 5,776 of 5,800 rows eligible (24 excluded, missing AH or
  goals fields). Extreme-favourite top quartile: n=1,159. Non-extreme
  rest: n=3,419.
- H-FB2-002: 5,735 of 5,800 rows eligible (65 excluded, missing SOT
  rolling history -- almost entirely each team's first ~10 matches in
  the dataset, exactly as expected from the leakage-safe rolling
  design). Price quintile 4 (top 20%): n=1,147.

## 6. H-FB2-001 primary result

Mean signed AH pricing residual, extreme-favourite top quartile
(n=1,159): **-0.0080**, 95% CI **[-0.0374, +0.0213]** -- includes zero.

## 7. H-FB2-002 primary result

Home-win-rate difference (high vs low SOT differential), price
quintile 4 (n=1,147): **+0.0999**, 95% CI **[+0.0511, +0.1557]** --
excludes zero, positive as pre-registered. High-SOT-diff half home-win
rate 0.747 vs low-SOT-diff half 0.647.

## 8. Directional pricing-error estimates

- H-FB2-001: the signed residual is small and near zero (-0.008),
  meaning extreme favourites cover the Asian Handicap at almost exactly
  the rate the market's own fair probability implies -- on average,
  NEITHER systematically over- NOR under-priced. This directly answers
  the operator's item-4 concern: the discovery-phase unsigned ECE gap
  (0.049 discovery / 0.031 gap vs rest) reflected elevated DISPERSION
  around a roughly-correct average, not a directional, tradable pricing
  error. Confirmed on the full development corpus: unsigned ECE remains
  elevated (extreme 0.054 vs rest 0.016) even though the signed mean is
  near zero -- both facts are true simultaneously, and only the signed
  one bears on whether an edge exists.
- H-FB2-002 has no direct AH/odds-pricing-error interpretation (see
  spec item D) -- it is a predictive-information-beyond-price finding,
  not a mispricing-direction finding. It says: within the strongest-
  home-favourite matches, a team materially outshooting its typical
  level (by SOT) wins about 10 percentage points more often than an
  otherwise-similarly-priced team that is not -- information the 1X2
  opening price alone does not appear to fully capture.

## 9. Confidence intervals

Given in points 6-7 above; both 95% percentile bootstrap, seed=42,
2,000 resamples.

## 10. Season stability

- H-FB2-001 (extreme quartile signed residual by season): 2020/21
  -0.0088, 2021/22 -0.0052, 2022/23 -0.0173, 2023/24 +0.0174, 2024/25
  -0.0310. Same sign (negative) as the pooled estimate in 4 of 5
  seasons -- clears the minimum stability bar (item N, >= 3 of 5) on
  sign alone, but every individual season's own CI includes zero (all
  n=196-274, all CIs span roughly +/-0.06 to +/-0.10) -- there is no
  season in which this effect is independently significant.
- H-FB2-002 (quintile-4 diff by season): 2020/21 +0.105, 2021/22
  +0.003, 2022/23 +0.098, 2023/24 +0.092, 2024/25 +0.105 -- positive in
  **5 of 5** seasons. Individual-season CIs are wider (n=197-262 each)
  and mostly touch or include zero at the season level (expected at
  this per-season sample size), but the POOLED direction and rough
  magnitude are consistent across every season except 2021/22, which is
  merely small and inconclusive (point estimate +0.003), not reversed.

## 11. Competition stability

- H-FB2-001 (extreme quartile signed residual by competition): E0
  -0.0353 (n=566), E1 +0.0157 (n=283), SC0 +0.0201 (n=310) -- signs
  disagree across competitions. Excluding E0 alone flips the pooled
  sign from negative to positive (+0.0180). This fails the single-
  competition-independence check outright: `single_competition_independent = false`.
- H-FB2-002 (quintile-4 diff by competition): E0 +0.110 (n=533, CI
  [0.028, 0.193] excludes zero), E1 +0.032 (n=370, CI includes zero),
  SC0 +0.115 (n=244, CI [0.008, 0.213] excludes zero) -- all three
  positive. Excluding any single competition leaves the pooled estimate
  positive and CI-excluding-zero in every case (excluding E0: +0.078,
  CI [0.010, 0.153]; excluding E1: +0.127, CI [0.065, 0.191]; excluding
  SC0: +0.078, CI [0.018, 0.140]). `single_competition_independent = true`.

## 12. Robustness/fragility findings

- H-FB2-001: using a top-quintile (20%) cut instead of the frozen
  quartile (25%) gives essentially the same near-zero result (-0.0020,
  CI [-0.0338, +0.0296]) -- consistent null, not an artefact of the
  exact 25% cut.
- H-FB2-002: a quartile-based (25%) cut instead of the frozen quintile
  (20%) gives a slightly LARGER effect (+0.118, CI [0.070, 0.163]) --
  robust to this perturbation, if anything strengthens with a slightly
  broader "extreme favourite" definition. A last-5-match SOT window
  instead of last-10 gives a smaller but still CI-excluding-zero effect
  (+0.062, CI [0.009, 0.114]) -- the effect is not an artefact of the
  specific 10-match window, though it is somewhat weaker with a shorter
  window.
- **A genuine, honestly reported inconsistency for H-FB2-002**: the
  secondary continuous-correlation diagnostic (Pearson r between SOT
  differential and the market's own pricing residual, within quintile
  4) is essentially zero (r=0.021, n=1,147) -- it does NOT corroborate
  the strength of the primary median-split result. This is flagged as
  an open question about the underlying mechanism (the effect may be
  concentrated at the extremes of the SOT-differential distribution
  rather than linear across it, which a median split can detect and a
  linear correlation can mask), not resolved here, and not used to
  either rescue H-FB2-001 or downgrade H-FB2-002's mechanical verdict
  -- the pre-registered primary metric is what the verdict is based on.

## 13. All negative/adverse evidence

- H-FB2-001's entire primary result is adverse to the hypothesis (see
  points 6, 8, 11) -- reported in full, not minimised.
- H-FB2-002's competition-level E1 result (n=370, point estimate +0.032,
  CI includes zero) is weaker than E0/SC0 -- reported as-is; it does
  not reverse sign, but it is not independently significant.
- H-FB2-002's 2021/22 season result (point estimate +0.003) is
  essentially flat, not a strong replication that year specifically --
  reported as-is.
- H-FB2-002's correlation-diagnostic inconsistency (point 12) is
  reported in full as an unresolved question, not hidden.

## 14. DEVELOPMENT-PROMOTE/PARTIAL/REJECT for each

- **H-FB2-001: DEVELOPMENT-REJECT.**
- **H-FB2-002: DEVELOPMENT-PROMOTE.**

## 15. Mechanical reason for each classification

Both computed by
`prediction_markets_lab.research.development_verdict.classify_development_result`
(12 unit tests), never judged manually:

- H-FB2-001: "primary CI does not exclude zero in the pre-registered
  direction" (first-order REJECT clause -- the sign-stability and
  single-competition checks were not even reached, since the CI
  condition alone is disqualifying).
- H-FB2-002: "primary CI excludes zero in the pre-registered direction,
  sign is stable across seasons, the sample-size floor is met in every
  reported season, and no single competition drives the pooled effect"
  -- all four PROMOTE conditions independently verified true.

## 16. Frozen proposed 2025/26 sealed-OOS protocol

`FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md`, written and committed in the
same commit as this checkpoint. Covers H-FB2-002 only (H-FB2-001 is
closed, no OOS test needed under this hypothesis ID). Specifies: data
source (Football-Data.co.uk, unchanged), competitions (E0/E1/SC0),
season (2025/26, full or partial with an explicit cutoff-date rule),
eligibility/exclusions (identical to development), primary metric
(the frozen quintile-4 median-split, reused unchanged), uncertainty
method (bootstrap, seed=42, n=2000), a proposed mechanical PASS/PARTIAL/
FAIL rule (stricter than the development-phase PROMOTE/PARTIAL/REJECT
rule -- a CI touching zero is FAIL, not PARTIAL, since this is a
one-shot test), minimum N (100), a small-sample fallback rule (any
top-quintile sample below 100 is PARTIAL regardless of CI, never PASS),
and an explicit no-retuning rule. **This protocol is proposed, not yet
implemented as code, and not yet authorised for execution** -- per the
operator's explicit "we will review the frozen specification before
authorising acquisition" instruction.

## 17. Confirmation 2025/26 was NOT downloaded/read/inspected

Confirmed. No file under any `2025_26` path was created, read, or
referenced by any script or command in this entire phase. The only
data touched throughout was the existing, already-frozen
`cycle_002_discovery_features.csv` (2020/21-2024/25).

## 18. Whether either hypothesis justifies consuming the sealed OOS

**H-FB2-002 alone** justifies proceeding to the sealed-OOS stage, per
its DEVELOPMENT-PROMOTE classification. **H-FB2-001 does not** -- it is
closed as a development-phase REJECT and will not consume any part of
the 2025/26 sealed OOS. Per the operator's own decision tree (section
12 of the instruction), because at least one hypothesis reached
DEVELOPMENT-PROMOTE, this checkpoint **stops here** rather than
acquiring 2025/26 -- that acquisition awaits explicit authorisation
after this checkpoint and the sealed-OOS protocol (point 16) have been
reviewed.

## 19. Tests passing

694/694. Breakdown: 662 at the end of the discovery checkpoint (commit
`1e257ce`), +15 for `football_cycle2_development.py`'s initial
functions (committed in `4757031`, before any development test ran),
+5 more for `bootstrap_ci_mean_diff`/`pearson_correlation` added for
H-FB2-002, +12 for `development_verdict.py` = 694. Full suite run
twice during this phase (once after the pre-registration commit, once
after the development-test commit), both green.

## 20. Commits/docs created

- Commit `4757031`: pre-registration (this checkpoint's point 4).
- This checkpoint's own commit (introduced immediately after
  `4757031`): `football_cycle2_development.py`'s additional two
  functions (`bootstrap_ci_mean_diff`, `pearson_correlation`) and their
  tests; `development_verdict.py` and its 12 tests;
  `run_h_fb2_001_development_test.py`,
  `run_h_fb2_002_development_test.py`; their JSON results
  (`h_fb2_001_development_test_results.json`,
  `h_fb2_002_development_test_results.json`, gitignored alongside every
  other cycle's interim data outputs); the updated
  `hypothesis_registry.csv` rows; `FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md`;
  and this document.

## 21. Exact next decision gate

Two independent decisions await Fraser/the operator:

1. **Whether to authorise implementing and then executing the sealed
   2025/26 OOS protocol (point 16) for H-FB2-002** -- this requires (a)
   acquiring 2025/26 Football-Data.co.uk files for E0/E1/SC0 (free,
   same source, zero new cost), (b) implementing the proposed
   PASS/PARTIAL/FAIL classifier as tested code, committed BEFORE the
   data is touched, exactly as Tennis Cycle 1's freeze/seal-check
   discipline required, and (c) running the one-shot evaluation.
2. **H-FB2-001 is closed** (DEVELOPMENT-REJECT) -- no further action
   requested unless Fraser/the operator wants a materially different
   re-specification registered as a new hypothesis ID (not a re-run of
   H-FB2-001 itself).

Everything else remains on HOLD per standing instructions: xG, weather,
injuries, new leagues, Betfair football, paid data, BEH-008 formal
testing, new football behaviour discovery, Cricket, paper trading, live
betting.
