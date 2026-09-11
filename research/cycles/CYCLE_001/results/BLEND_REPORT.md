# Blend Report (Stage 3B, Model 3)

**Generated from `data/interim/stage_3b_checkpoint4_metrics.json`, produced by
`scripts/run_stage_3b_checkpoint4_blends_and_uncertainty.py`. Do not hand-edit
the numbers below without regenerating from that script.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Development seasons: 2020_21, 2021_22, 2022_23, 2023_24.
Sealed holdout (2024_25) not read.

## Predeclared comparison matrix run in this checkpoint

Market-only, Elo-only, and Poisson-only are already evaluated in Checkpoints
1-3 and are **not** recomputed here (pooled numbers are recomputed on this
script's own common sample purely so every number in this report comes from
one consistent pass, not as a new baseline). The 4 genuinely new
combinations, justified because both Elo and Poisson individually already
beat the naive floor (the predeclared bar for progressing past single
components):

| Combo | Components |
|---|---|
| `elo_poisson` | Elo + Poisson (fundamentals-only, no market) |
| `market_elo` | Market + Elo |
| `market_poisson` | Market + Poisson |
| `market_elo_poisson` | Market + Elo + Poisson |

## Method

Each combo's weights are calibrated **per walk-forward fold, on that fold's
training period only**, via an exhaustive predeclared grid search (step =
0.1 across all components summing to 1.0 — 11 candidates for a 2-component
blend, 66 for the 3-component blend), minimising log loss on training data,
then scored on that fold's evaluation-season common sample. Weights are
never hand-tuned and never fit on evaluation data.

## Calibrated blend weights per fold

| Fold | Evaluates | `elo_poisson` (elo/poisson) | `market_elo` (market/elo) | `market_poisson` (market/poisson) | `market_elo_poisson` (market/elo/poisson) |
|---|---|---|---|---|---|
| train_through_2020_21_eval_2021_22 | 2021_22 | 0.30 / 0.70 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 / 0.00 |
| train_through_2021_22_eval_2022_23 | 2022_23 | 0.30 / 0.70 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 / 0.00 |
| train_through_2022_23_eval_2023_24 | 2023_24 | 0.40 / 0.60 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 / 0.00 |

**Headline finding: every combo that includes "market" as a component
calibrates to 100% market weight, on training data, in every one of the 3
folds.** At this grid resolution (step = 0.1), no positive weight on Elo or
Poisson ever reduces in-sample log loss once market is available as an
option. This is a genuine result of the exhaustive grid search, not a bug —
verified by a dedicated regression test
(`test_stage_3b_checkpoint4_blends.py::test_full_run_against_real_frozen_dataset_is_internally_consistent`)
that locks in the fact that a market-inclusive blend can never score worse
than pure market (since the 100%-market corner is always a candidate in the
grid).

Only `elo_poisson` (no market available to dominate the search) produces a
genuinely mixed blend, favouring Poisson over Elo (60-70% Poisson weight in
every fold) — consistent with Poisson beating Elo on both log loss and Brier
individually (Checkpoints 2 and 3).

## Pooled results (all 3 development folds combined, common sample N=3,446)

| Model | Log loss | Brier | Δ log loss (vs. market) | Δ Brier (vs. market) |
|---|---|---|---|---|
| Market (Baseline 1) | 0.9773 | 0.5815 | — | — |
| Elo (Model 1) | 1.0233 | 0.6133 | +0.0460 | +0.0318 |
| Poisson (Model 2) | 1.0097 | 0.6037 | +0.0324 | +0.0221 |
| **`elo_poisson`** | **1.0035** | **0.5995** | **+0.0262** | **+0.0180** |
| `market_elo` | 0.9773 | 0.5815 | 0.0000 | 0.0000 |
| `market_poisson` | 0.9773 | 0.5815 | 0.0000 | 0.0000 |
| `market_elo_poisson` | 0.9773 | 0.5815 | 0.0000 | 0.0000 |

Delta convention: `delta = candidate_metric - market_metric`; negative means
the candidate beats market, positive means market wins, 0.0000 means the
calibrated blend degenerated to pure market (see above).

`elo_poisson` closes part of the gap to market relative to either
fundamentals-only model alone (Δ log loss 0.0262, vs. 0.0460 for Elo alone
and 0.0324 for Poisson alone) — ensembling genuinely helps, it just isn't
enough to close the gap entirely.

## Paired bootstrap confidence intervals (vs. market, pooled, both methods, 95% CI, n_resamples=2000, seed=42)

| Candidate | Log loss Δ (match-level 95% CI) | Log loss Δ (block-by-date 95% CI) | Brier Δ (match-level 95% CI) | Brier Δ (block-by-date 95% CI) |
|---|---|---|---|---|
| Elo | 0.0460 [0.0358, 0.0561] | 0.0460 [0.0355, 0.0563] | 0.0318 [0.0246, 0.0386] | 0.0318 [0.0243, 0.0388] |
| Poisson | 0.0324 [0.0242, 0.0402] | 0.0324 [0.0243, 0.0403] | 0.0221 [0.0159, 0.0284] | 0.0221 [0.0158, 0.0287] |
| `elo_poisson` | 0.0262 [0.0190, 0.0331] | 0.0262 [0.0189, 0.0335] | 0.0180 [0.0131, 0.0228] | 0.0180 [0.0128, 0.0229] |
| `market_elo` / `market_poisson` / `market_elo_poisson` | 0.0000 [0.0000, 0.0000] (identical to market by construction) | — | — | — |

Every CI for a non-market-degenerate candidate lies entirely **above** zero
(both bounds positive) for both metrics and both resampling methods — the
market's advantage over Elo, Poisson, and `elo_poisson` is not just a point
estimate, it is a stable, statistically clear gap under both an i.i.d.
match-level resample and a same-day block resample. The two resampling
methods agree closely throughout (no case where block-by-date meaningfully
widens or shifts the interval relative to match-level), suggesting same-day
correlation is not materially distorting the naive match-level CIs here.

## Interpretation

The predeclared blend matrix answers its own question cleanly: **fundamentals
(Elo, Poisson) contain real, combinable signal — blending them closes part
of the gap to market — but none of that signal is incremental once the
market's own consensus is already an input.** This is the expected result
from market-efficiency reasoning (a liquid consensus of many bookmakers
already prices in most publicly-available statistical signal) and is
consistent with the ordering established across Checkpoints 1-4: naive <
Elo < Poisson < `elo_poisson` < market, with market's lead over every
fundamentals-only candidate confirmed statistically significant by paired
bootstrap.

No model or blend in Stage 3B has beaten the market on the development
folds. Per the predeclared plan, this is itself a valid and complete
scientific answer to the Stage 3B research question — the honest, current
verdict trends toward **market dominates / null result** for
information-content beyond the market, pending the sealed 2024/25 holdout
(Checkpoint 6), which is the actual final test and has not been touched.
