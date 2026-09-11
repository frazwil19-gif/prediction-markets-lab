# Naive Baseline Report (Stage 3B, Baseline 0)

**Generated from `data/interim/stage_3b_checkpoint1_metrics.json`, produced by
`scripts/run_stage_3b_checkpoint1_baselines.py`. Do not hand-edit the numbers
below without regenerating from that script.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Development seasons: 2020_21, 2021_22, 2022_23, 2023_24.
Sealed holdout (2024_25) not read.

## Method

Expanding, per-competition H/D/A frequency from strictly-earlier matches in
the same competition only, Laplace `alpha=1.0` smoothing.
See `models/football_naive_frequency.py` and
`research/cycles/CYCLE_001/STAGE_3B_PLAN.md` §5.

## Per-fold results (full coverage — every evaluation match, market data not required)

| Fold | Evaluates | N | Log loss | Brier |
|---|---|---|---|---|
| train_through_2020_21_eval_2021_22 | 2021_22 | 1160 | 1.0758 | 0.6514 |
| train_through_2021_22_eval_2022_23 | 2022_23 | 1160 | 1.0662 | 0.6448 |
| train_through_2022_23_eval_2023_24 | 2023_24 | 1160 | 1.0656 | 0.6446 |

## Pooled result (all 3 development folds combined, N=3480)

- Log loss: **1.0692**
- Brier score: **0.6470**
- Reference point: a uniform 1/3-1/3-1/3 prediction on every match scores
  log loss = ln(3) ≈ 1.0986 and Brier = 2/3 ≈ 0.6667 on any dataset. The
  naive baseline (1.069 / 0.647) is only marginally better than uniform —
  expected, since simple historical H/D/A frequency captures the general
  home-field-advantage skew in football but essentially nothing team- or
  fixture-specific.

## Purpose and interpretation

This is a sanity floor, not a target. Its purpose is answering: "does a
model that uses real football information (Elo, Poisson) at least beat
doing no modelling at all?" A model that cannot clear ~1.069 log loss /
~0.647 Brier on these same development folds would indicate a defect in
that model, not a finding about football being unpredictable — the market
(see `MARKET_BASELINE_REPORT.md`) demonstrates there is substantially more
extractable structure than this naive floor captures.
