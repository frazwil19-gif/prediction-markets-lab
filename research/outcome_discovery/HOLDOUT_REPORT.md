# Holdout Report -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22. Covers the 2025/26 season (3,390 candidates / 1,130 matches), explicitly labelled
per DATASET_AUDIT.md's honesty note: this is a chronological holdout for this cycle's own new
discovery process, but its aggregate performance under the 5 existing model architectures was
already computed and published by Gate 1/Phase 1/Phase 2 -- it is not a data source no prior
research has ever touched. Section 33's discipline ("do not repeatedly inspect the holdout") is
honoured in the narrow sense that no NEW winner/loser relationship discovered in this cycle was
inspected against holdout and then used to revise the discovery-stage finding -- the winner/loser
feature analysis simply cannot run on 2025/26 at all (see below), so there was nothing to
peek at and re-mine.

## What could and could not be evaluated on holdout

**Could**: every model's probability, realised outcome, and therefore top-pick accuracy,
probability-band calibration, and favourite/underdog/draw classification -- all present via the
predictions file for all 6 seasons including 2025/26.

**Could not**: the engineered-feature winner/loser analysis (Sections 6-9, 24). `cycle_002_
discovery_features.csv` does not cover 2025/26 (DATASET_AUDIT.md), so every `signed_*` feature is
`None` for holdout candidates. FEATURE_STABILITY.csv reports this explicitly as "DATA UNAVAILABLE"
for every one of the 11 features, not as a sign-disagreement/instability finding -- an earlier draft
of this script mislabelled this exact situation as UNSTABLE and was corrected before publication
(see the regression test `test_feature_stability_reports_missing_holdout_as_insufficient_data_not_
unstable` in `tests/unit/test_outcome_discovery_analysis.py`).

## Top-pick accuracy on holdout

| Model | Holdout accuracy | Discovery | Validation |
|---|---|---|---|
| Market | 48.67% | 52.42% | 52.89% |
| Elo+Poisson | 46.73% | 50.47% | 50.53% |
| Fundamentals | 47.79% | 49.84% | 50.09% |
| Market+Fundamentals | 47.52% | 51.80% | 52.62% |
| Ensemble | 48.67% | 51.98% | 53.02% |

**Every model, including the market, scores noticeably lower on the 2025/26 holdout than on either
prior partition** (market: -3.75 to -4.22 percentage points versus discovery/validation). Two
honest possibilities, neither confirmed here: (1) ordinary sampling noise from a smaller holdout
sample (1,130 matches vs ~2,250 per prior partition) -- a single-season top-pick-accuracy swing of a
few percentage points is well within what chance alone produces at this sample size; (2) a genuine
distributional shift in the 2025/26 season. **This cycle does not distinguish between these two
explanations** -- doing so honestly would require either a larger holdout sample (waiting for more
of the season, or for 2026/27) or a formal significance test, neither of which is fabricated here.
The relative ranking (market and ensemble tied for best, fundamentals/Elo+Poisson worst) is
unchanged from discovery/validation, which is the one thing this holdout result does confirm
without qualification.

## Draw prediction structurally never attempted

The market never selects draw as its single most likely outcome in any of the 5,631 matches pooled
(0 of 3,790+1,841 top picks are draw) -- true in every partition including holdout. This is an
inherent property of a well-calibrated 3-outcome market where the draw base rate (24.76% pooled,
1,394/5,631) is systematically lower than the spread between home and away probabilities in the
large majority of matches, not a holdout-specific finding.

## Betting overlay on holdout

See BETTING_OVERLAY_REPORT.md -- Backtest Phase 1's already-published, already-pushed result
(zero money-qualified bets across the full 2020/21-2025/26 dataset) already covers the 2025/26
holdout period in full; re-running the frozen-strategy harness on this subset alone was not done,
since a subset of a set with zero qualifying candidates cannot itself contain a qualifying
candidate. This is stated as a logical consequence of an existing, verified result, not assumed
without checking that Phase 1's own dataset genuinely included 2025/26 (confirmed: Phase 1's
`5,776 eligible matches` figure and Gate 1/Phase 2's `5,631` pooled OOS figure both span the full
2020/21-2025/26 range, per their own published checkpoints).
