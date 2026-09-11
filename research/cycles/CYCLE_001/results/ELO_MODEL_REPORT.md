# Elo Model Report (Stage 3B, Model 1)

**Generated from `data/interim/stage_3b_checkpoint2_metrics.json`, produced by
`scripts/run_stage_3b_checkpoint2_elo.py`. Do not hand-edit the numbers below
without regenerating from that script.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Development seasons: 2020_21, 2021_22, 2022_23, 2023_24.
Sealed holdout (2024_25) not read.

## Model definition

Standard two-outcome Elo rating update (win=1/draw=0.5/loss=0 expected-vs-actual
score, base-10/400 logistic curve), tracked **globally per team** (not
per-competition, so a promoted/relegated team's rating carries continuity
rather than resetting — this project's documented, deliberately simple
answer to promoted-team initialisation). Fixed hyperparameters (literature
defaults, not fit to this dataset):

| Parameter | Value |
|---|---|
| initial_rating | 1500 |
| k_factor | 20 |
| home_advantage | 100 rating points |
| season_reversion_fraction | 0.25 |

**3-way probability construction** (see `models/football_elo.py` module
docstring for full derivation): the rating UPDATE above never sees a draw
probability. The separate 3-way PREDICTION output uses one additional
parameter, `draw_margin`, applied symmetrically around the rating edge:
`P(home) = expected_score(edge - draw_margin)`,
`P(home-or-draw) = expected_score(edge + draw_margin)`,
`P(draw) = P(home-or-draw) - P(home)`, `P(away) = 1 - P(home-or-draw)`.
This guarantees all three probabilities sum to exactly 1 and are
non-negative by construction, with no separately-fitted draw model.

`draw_margin` is the one parameter genuinely calibrated per fold — via grid
search over a predeclared set (25, 50, 75, 100, 125, 150, 175, 200
rating points), minimising **in-sample log loss on that fold's training
seasons only** (never the evaluation season). All 3 folds independently
selected **100** — comfortably
inside the candidate range, not at either boundary, so there is no sign the
grid needs widening.

## Per-fold results (common sample — Elo and market scored on the identical match-ID set)

| Fold | Evaluates | Draw margin | N (common) | Elo log loss | Elo Brier | Market log loss | Market Brier | Δ log loss (Elo-market) | Δ Brier (Elo-market) |
|---|---|---|---|---|---|---|---|---|---|
| train_through_2020_21_eval_2021_22 | 2021_22 | 100 | 1159 | 1.0414 | 0.6265 | 0.9848 | 0.5875 | 0.0565 | 0.0390 |
| train_through_2021_22_eval_2022_23 | 2022_23 | 100 | 1160 | 1.0154 | 0.6082 | 0.9895 | 0.5907 | 0.0259 | 0.0175 |
| train_through_2022_23_eval_2023_24 | 2023_24 | 100 | 1127 | 1.0130 | 0.6049 | 0.9570 | 0.5659 | 0.0560 | 0.0390 |

Delta convention: `delta = elo_metric - market_metric`. Positive in every row
— the market beats Elo on every individual development fold.

## Pooled result (all 3 development folds combined, common sample N=3446)

- Elo log loss: **1.0233**
- Elo Brier score: **0.6133**
- Market log loss (same common sample): 0.9773
- Market Brier (same common sample): 0.5815
- **Δ log loss (Elo − market): 0.0460** (positive = market wins)
- **Δ Brier (Elo − market): 0.0318** (positive = market wins)

## Comparison against Baseline 0 (naive frequency)

| | Log loss | Brier |
|---|---|---|
| Naive frequency (Baseline 0, `NAIVE_BASELINE_REPORT.md`) | 1.0689 | 0.6467 |
| **Elo (this report)** | 1.0233 | 0.6133 |
| Market (Baseline 1, `MARKET_BASELINE_REPORT.md`) | 0.9773 | 0.5815 |

(Naive figures above are the common-sample numbers from Checkpoint 1's
pooled run, which used the identical fold definitions and an almost
identical common sample — 3,446 vs Elo's 3,446 rows to the match, since both
scripts apply the same `eligible_consensus_model` filter.)

## Interpretation

Elo clears the naive floor by a wide margin (log loss 1.023 vs. 1.069) and
does capture real predictive signal — this is a meaningful sanity check
passing: Elo is not broken, and adds real information over having no
football-specific model at all. It does **not** yet close the gap to the
market (1.023 vs. 0.977), on every development fold individually and
pooled. No significance testing yet (paired bootstrap CIs are a later
checkpoint) — the gap here is large enough relative to the naive-vs-market
gap that it is very unlikely to be pure noise, but this report does not
claim that formally.

This is consistent with the Stage 3B research question being open, not
settled: a single fundamental model (Elo alone, no market information) is
expected to underperform a market that aggregates many bookmakers' pricing
information. The more interesting test is still ahead — Poisson (Model 2),
and then whether a **market-aware** blend (Market + Elo, Market + Poisson,
Market + Elo + Poisson) can add anything incremental *beyond* what the
market alone already captures.
