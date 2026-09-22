# Dataset Audit -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22 (second research-direction instruction of the day, following Phase 3's data
expansion audit). This cycle reframes the primary research question per the operator's explicit
correction: predict outcomes first (calibration, top-pick accuracy, win rate by probability band),
evaluate betting value second. See the master research directive's forthcoming entry for full
context; this document covers Section 5's dataset-audit requirement.

## Data sources used (audited before any new acquisition, per standing project discipline)

**Predictions (target + 5 model architectures' probabilities)**:
`research/probability_model_v2/per_match_predictions_gate1_reproduction.csv` -- Gate 1's own
chronological, walk-forward, leakage-safe out-of-sample predictions (2026-09-18, extended for
export in Phase 2, 2026-09-22). 5,631 matches, pooled across 5 expanding walk-forward folds
covering all 6 seasons (2020/21 through 2025/26). Columns: match_id, competition_code, season,
outcome (realised result: "home"/"draw"/"away"), and each of 5 models' P(home)/P(draw)/P(away):
model_0_market (de-vigged multi-bookmaker consensus), model_1_elo_poisson_blend (the frozen
Stage-3B blend), model_2_fundamentals (Gate 1's 9-feature multinomial logistic regression),
model_3_market_fundamentals (market+fundamentals combined), model_4_ensemble (the calibrated
blend-weight-search ensemble).

**These predictions are REUSED, not refit**, per this project's standing "do not repeat exhausted
research" discipline (§7 of the master directive) -- Gate 1 already fit and chronologically
validated exactly these architectures. This cycle performs new descriptive/discovery analysis on
their existing, already-published outputs, not a new model-fitting exercise.

**Engineered pre-match features**: `data/processed/football/cycle_002_discovery_features.csv` --
163 columns of leakage-safe rolling-window features (last-5/last-10 goals/shots/SOT/corners/cards,
home/away-context splits, conversion rate, points-per-game, Elo ratings and gap, market
opening/closing probabilities). **Covers only 2020/21-2024/25** (5,800 raw match rows) -- the
2025/26 sealed-OOS season's separate acquisition
(`h_fb2_002_sealed_oos_2025_26_*.csv`) carries raw matches/results/consensus but not this
engineered-feature table. This is a real, stated scope limit of this cycle's feature-level
analysis (Sections 6-9, 24), not a hidden gap -- see LEAKAGE_AUDIT.md and FEATURE_STABILITY.csv.

## Candidate dataset construction

For every one of the 5,631 matches, three candidate rows were created (home/draw/away), each with
`target = 1` if that side occurred and `0` otherwise. Total: **16,893 candidates** (5,631 x 3),
matching the same construction Phase 2's disagreement-band analysis already used for a different
purpose. Of these, 5,631 are winners (one per match, by construction) and 11,262 are losers.

## Chronological partitioning

Per the instruction's explicit requirement for a discovery/validation/sealed-holdout split (not
Gate 1's expanding walk-forward), seasons were partitioned:

- **DISCOVERY** (2020/21, 2021/22, 2022/23): 6,753 candidates (2,251 matches)
- **VALIDATION** (2023/24, 2024/25): 6,750 candidates (2,250 matches)
- **HOLDOUT** (2025/26): 3,390 candidates (1,130 matches)

**Honesty note, carried forward from Phase 2's own equivalent finding**: this is NOT a genuinely
blind holdout in the strictest sense. Gate 1's walk-forward already used every one of these seasons
as an out-of-sample test fold at some point, and this project has already published pooled
aggregate metrics (log loss, Brier, calibration) covering all of them, including 2025/26. What IS
genuinely new here is the specific winner/loser feature-level relationships this cycle mines --
those have never been extracted or reported before, so discovery-vs-validation replication (both
using the engineered-feature file) is a real and informative test. True prospective confirmation of
any of this cycle's findings, on data no prior research has touched at all, would require the
2026/27 season once enough of it accumulates -- named explicitly here rather than pretending the
current split provides that.

## Competitions and period

E0 (Premier League), E1 (Championship), SC0 (Scottish Premiership), 2020/21-2025/26. Same coverage
already audited in every prior cycle this season (Backtest Phase 1, Phase 2, Phase 3).
