# Poisson Model Report (Stage 3B, Model 2)

**Generated from `data/interim/stage_3b_checkpoint3_metrics.json`, produced by
`scripts/run_stage_3b_checkpoint3_poisson.py`. Do not hand-edit the numbers
below without regenerating from that script.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Development seasons: 2020_21, 2021_22, 2022_23, 2023_24.
Sealed holdout (2024_25) not read.

## Model definition

Classic independent-Poisson attack/defence model (Maher 1982-style), tracked
**per competition** (unlike Elo — goal-scoring rates differ substantially
between e.g. the Premier League and the Scottish Premiership, and there is
no natural way to carry a goals-based rate across leagues; a team new to a
competition, including a promoted team, starts at the league-average ratio).

For home team i, away team j, competition-specific league averages
`avg_home`/`avg_away`:

    lambda_home = avg_home * attack_home(i) * defence_away(j)
    lambda_away = avg_away * attack_away(j) * defence_home(i)

Then `P(home)`/`P(draw)`/`P(away)` sum independent-Poisson scoreline mass
over a truncated 15×15 grid, renormalised (truncated mass
verified > 0.99998 for realistic and unusually one-sided lambdas — see
`test_truncation_error_is_negligible_for_realistic_lambdas`).

Each team ratio is shrunk toward 1.0 (an average team) by
`shrinkage_matches=4` pseudo-observations — simple,
closed-form regularisation so a team with 0-2 observed matches (most
importantly a team new to the competition) is not driven by a tiny sample.
League averages themselves fall back to fixed defaults
(`1.5`/`1.1` goals) before any matches exist in that
competition, or in the degenerate edge case of an exactly-zero computed
average.

No time-decay weighting, no Dixon-Coles low-score correlation adjustment, no
joint maximum-likelihood fit — deliberately simple, per project
instructions (do not add complexity without evidence).

## Data note: goals were rejoined from the frozen raw CSVs

`cycle_001_matches_full.csv` never carried full-time goal counts (only FTR).
This script reconstructs each match's `match_id` from the same frozen raw
source CSVs using the identical construction the acquisition script itself
uses (`ingestion.match_identity.build_match_id`), and joins FTHG/FTAG back
on by that match_id — reading no new external data, only the same 15
already-hash-verified raw files. All 3480 development matches joined successfully
(verified by a dedicated integration test against the real frozen dataset).

## Per-fold results (common sample — Poisson and market scored on the identical match-ID set)

| Fold | Evaluates | N (common) | Poisson log loss | Poisson Brier | Market log loss | Market Brier | Δ log loss (Poisson-market) | Δ Brier (Poisson-market) |
|---|---|---|---|---|---|---|---|---|
| train_through_2020_21_eval_2021_22 | 2021_22 | 1159 | 1.0241 | 0.6140 | 0.9848 | 0.5875 | 0.0393 | 0.0264 |
| train_through_2021_22_eval_2022_23 | 2022_23 | 1160 | 1.0106 | 0.6045 | 0.9895 | 0.5907 | 0.0211 | 0.0138 |
| train_through_2022_23_eval_2023_24 | 2023_24 | 1127 | 0.9940 | 0.5922 | 0.9570 | 0.5659 | 0.0370 | 0.0263 |

Delta convention: `delta = poisson_metric - market_metric`. Positive in every
row — the market beats Poisson on every individual development fold.

## Pooled result (all 3 development folds combined, common sample N=3446)

- Poisson log loss: **1.0097**
- Poisson Brier score: **0.6037**
- Market log loss (same common sample): 0.9773
- Market Brier (same common sample): 0.5815
- **Δ log loss (Poisson − market): 0.0324** (positive = market wins)
- **Δ Brier (Poisson − market): 0.0221** (positive = market wins)

## Comparison against Baseline 0, Baseline 1, and Elo

| | Log loss | Brier |
|---|---|---|
| Naive frequency (Baseline 0) | 1.0689 | 0.6467 |
| Elo (Model 1) | 1.0233 | 0.6133 |
| **Poisson (this report, Model 2)** | 1.0097 | 0.6037 |
| Market (Baseline 1) | 0.9773 | 0.5815 |

(All four rows use the same 3,446-row common sample and the same 3
development folds, so this ranking is directly comparable.)

## Interpretation

Poisson clears both the naive floor and Elo — a second, independent sanity
check passing: goal-based attack/defence modelling captures more information
than either doing nothing or rating-based win/loss modelling alone, which is
the expected ordering from football-analytics literature (goal-scoring rates
carry more granular information than match results alone). It still does not
close the gap to the market on any development fold, individually or
pooled. No significance testing yet.

Per the Stage 3B baseline order, Model 3 (blends) comes next -- but only if
Elo and/or Poisson individually justify inclusion by adding something a
market-aware blend can actually use. Both are now candidates; a
market-inclusive blend (Market + Elo, Market + Poisson, Market + Elo +
Poisson) is the real test of whether either adds anything *beyond* what the
market already prices in.
