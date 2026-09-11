# Market Baseline Report (Stage 3B, Baseline 1)

**Generated from `data/interim/stage_3b_checkpoint1_metrics.json`, produced by
`scripts/run_stage_3b_checkpoint1_baselines.py`. Do not hand-edit the numbers
below without regenerating from that script.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Development seasons: 2020_21, 2021_22, 2022_23, 2023_24.
Sealed holdout (2024_25) not read.

## Method and classification

Price timing used: **closing** consensus from
`cycle_001_consensus_full.csv` (per-bookmaker margin removed via
`probability.margin_removal`, cross-bookmaker median via
`probability.consensus` — unchanged from Stage 3A methodology).

Classification (see `STAGE_3B_PLAN.md` §6): this is a
**`market_predictive_benchmark (NOT historically_executable_entry_price)`**. It is a valid, strong
benchmark for predictive comparison. It must **not** be read as a price this
project could have traded against historically — no timing/execution
evidence exists for it. Renormalised to sum to exactly 1.0 before scoring
(median-per-outcome consensus deviates from 1.0 by up to 1.18%, median
0.13% — see `reports/audits/CURRENT_STATE_AUDIT.md` Update 4 — this is
expected behaviour of a per-outcome median, not a computation defect).

## Per-fold results (common sample — naive and market scored on the identical match-ID set)

| Fold | Evaluates | N (common) | Market log loss | Market Brier | Naive log loss | Naive Brier | Δ log loss (naive-market) | Δ Brier (naive-market) |
|---|---|---|---|---|---|---|---|---|
| train_through_2020_21_eval_2021_22 | 2021_22 | 1159 | 0.9848 | 0.5875 | 1.0756 | 0.6513 | 0.0907 | 0.0638 |
| train_through_2021_22_eval_2022_23 | 2022_23 | 1160 | 0.9895 | 0.5907 | 1.0662 | 0.6448 | 0.0767 | 0.0541 |
| train_through_2022_23_eval_2023_24 | 2023_24 | 1127 | 0.9570 | 0.5659 | 1.0648 | 0.6440 | 0.1078 | 0.0782 |

Delta convention: `delta = naive_metric - market_metric`. Positive in every
row above — the market beats the naive baseline on every single development
fold, consistently.

## Pooled result (all 3 development folds combined, common sample N=3446)

- Market log loss: **0.9773**
- Market Brier score: **0.5815**
- Naive log loss (same common sample): 1.0689
- Naive Brier (same common sample): 0.6467
- **Δ log loss (naive − market): 0.0916** (positive = market wins)
- **Δ Brier (naive − market): 0.0652** (positive = market wins)

## Coverage note

Naive-baseline full coverage is 3480 matches;
the naive-vs-market common sample is 3446 matches
(34 matches
lack a usable closing consensus — insufficient bookmaker coverage below the
configured minimum, not a data defect). All comparisons above use only the
common-sample number, never the full-coverage number, per
`STAGE_3B_PLAN.md` §7.

## Interpretation

The market closing consensus is a materially stronger predictor than the
naive frequency baseline on every development fold (no uncertainty
quantification yet — paired bootstrap CIs are a Checkpoint 4 deliverable,
not computed here). This sets the real bar for Elo/Poisson/blend: those
models must be compared against **this** market benchmark, not against the
naive floor, to answer the Stage 3B research question (do they add
information *beyond the market*, not merely beyond doing nothing).
