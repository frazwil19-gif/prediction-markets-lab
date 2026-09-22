# Leakage Audit -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22. Reviewed against `docs/DATA_LEAKAGE_RULES.md`, the same standard every prior
cycle's leakage audit has used this project.

## Inputs used and their leakage status

**Model probabilities** (all 5 architectures): inherited unchanged from Gate 1, which was itself
leakage-audited at build time (2026-09-18) -- every rolling feature shifted correctly, market
consensus built from pre-match odds only, expanding walk-forward folds never trained on a match
being predicted. This cycle adds no new model-fitting step, so no new leakage surface is
introduced by the predictions themselves.

**Engineered features** (elo_gap, rolling diffs): sourced from `cycle_002_discovery_features.csv`,
itself leakage-audited when built (Cycle 2, 2026-09-15/16) -- every rolling window uses only
matches strictly before the one being featured (e.g. to feature Match 10, rolling form uses Matches
1-9, never Match 10). This cycle does not recompute these features, only reads and re-signs them
(home-perspective value kept as-is for the home candidate, negated for the away candidate, negated
absolute value for the draw candidate) -- a re-labelling operation, not a new feature computation,
so it introduces no new leakage risk.

**Target label** (`outcome`): the realised full-time result, used only as the dependent variable
being predicted, never as an input feature. Confirmed by direct code inspection of
`build_candidates()` in `src/prediction_markets_lab/research/outcome_discovery_analysis.py` --
`target` is computed from `m["outcome"]` and stored separately from every `signed_*` feature
column; no feature-construction code path reads `outcome`.

## New leakage risks specifically checked for this cycle

**Favourite/underdog assignment** (Sections 8-9): defined from `model_0_market` probabilities,
which are themselves pre-match closing consensus (already leakage-audited in Gate 1). No post-match
information (e.g. actual margin of victory) enters this assignment.

**Discovery/validation/holdout partitioning**: strictly by season boundary
(2020/21-2022/23 / 2023/24-2024/25 / 2025/26), matching the same season-ordering already used and
audited in Gate 1 and every prior football cycle. No match crosses a partition boundary based on
anything other than its season.

**Conditional market analysis** (Section 24): buckets candidates by their own pre-match market
probability, then compares already-realised outcomes within that bucket -- this is descriptive
analysis of already-completed matches, not a live decision process, so no forward-looking
information is required or used.

## Explicitly NOT done in this cycle (and why that's correct, not an omission)

No new rolling-window computation was performed -- all engineered features are read verbatim from
an already-audited file. No new model was fit -- all probabilities are read verbatim from an
already-audited file. This minimises the surface area for a *new* leakage bug to be introduced,
consistent with the project's "reuse, don't rebuild" discipline (§7 of the master directive) when a
component has already been validated.

## Verdict

No leakage found in this cycle's construction. The one substantive limitation is not a leakage risk
but a **data-coverage** one: 2025/26 candidates have no engineered-feature join available (feature
values are `None`, not leaked or fabricated), a gap flagged explicitly in DATASET_AUDIT.md and
FEATURE_STABILITY.csv rather than silently worked around.
