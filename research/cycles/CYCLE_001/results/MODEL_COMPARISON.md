# Model Comparison (Stage 3B, Checkpoints 1-4 consolidated)

**Consolidates `NAIVE_BASELINE_REPORT.md`, `MARKET_BASELINE_REPORT.md`,
`ELO_MODEL_REPORT.md`, `POISSON_MODEL_REPORT.md`, `BLEND_REPORT.md`, and
`CALIBRATION_REPORT.md` into one comparison table. Do not hand-edit; source
numbers are in `data/interim/stage_3b_checkpoint{1,2,3,4}_metrics.json`.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Development seasons: 2020_21,
2021_22, 2022_23, 2023_24, pooled across the 3 walk-forward folds. Sealed
holdout (2024_25) not read by any script referenced here. **This is a
development-fold comparison only — it is not the final Stage 3B verdict**,
which requires the sealed holdout evaluation (Checkpoints 5-6, not yet
started).

## Common-sample comparison rule

Per `STAGE_3B_PLAN.md` §7, every number below uses the identical N=3,446
match-ID common sample (`eligible_consensus_model == True` and a usable
closing consensus present), so every row is directly comparable to every
other row. (Naive-baseline full coverage is 3,480 matches — see
`NAIVE_BASELINE_REPORT.md` — but that full-coverage number is never mixed
into this table.)

## Full ranking (log loss, lower is better)

| Rank | Model | Log loss | Brier | Δ log loss (vs. market) | Δ Brier (vs. market) | 95% bootstrap CI on Δ log loss (block-by-date) |
|---|---|---|---|---|---|---|
| 1 | **Market (Baseline 1)** | 0.9773 | 0.5815 | — | — | — |
| 1= | `market_elo_poisson` | 0.9773 | 0.5815 | 0.0000 | 0.0000 | [0.0000, 0.0000] (identical to market) |
| 1= | `market_elo` | 0.9773 | 0.5815 | 0.0000 | 0.0000 | [0.0000, 0.0000] (identical to market) |
| 1= | `market_poisson` | 0.9773 | 0.5815 | 0.0000 | 0.0000 | [0.0000, 0.0000] (identical to market) |
| 2 | `elo_poisson` (Model 3, fundamentals-only blend) | 1.0035 | 0.5995 | +0.0262 | +0.0180 | [0.0189, 0.0335] |
| 3 | Poisson (Model 2) | 1.0097 | 0.6037 | +0.0324 | +0.0221 | [0.0243, 0.0403] |
| 4 | Elo (Model 1) | 1.0233 | 0.6133 | +0.0460 | +0.0318 | [0.0355, 0.0563] |
| 5 | Naive frequency (Baseline 0) | 1.0689 | 0.6467 | +0.0916 | +0.0652 | not bootstrapped (Checkpoint 1 predates the bootstrap module; point estimate only) |

Delta convention: `delta = candidate_metric - market_metric`; negative would
mean the candidate beats market, positive means market wins. Every
non-degenerate candidate's CI lies entirely above zero — the market's lead
over Elo, Poisson, and their blend is statistically clear, not just a point
estimate, under both match-level and block-by-date paired bootstrap
resampling (see `BLEND_REPORT.md` for both methods side by side; they agree
closely throughout).

## Calibration ranking (Expected Calibration Error, lower is better; see `CALIBRATION_REPORT.md` for full detail)

| Model | Home ECE | Draw ECE | Away ECE |
|---|---|---|---|
| Market | 0.0219 | 0.0204 | **0.0058** |
| **`elo_poisson`** | **0.0130** | 0.0155 | 0.0128 |
| Elo | 0.0542 | **0.0106** | 0.0605 |
| Poisson | 0.0278 | 0.0128 | 0.0240 |

Discrimination (log loss/Brier) and calibration are different questions and
do not rank models identically: `elo_poisson` is the best-calibrated
model-based candidate on 2 of 3 outcomes despite not having the lowest log
loss among non-market candidates by a wide margin, because blending
corrects a specific, large, one-directional bias in Elo's away-outcome
predictions (see `CALIBRATION_REPORT.md`).

## What each stage of sophistication bought

- Naive → Elo: uses actual match results (not just aggregate H/D/A rates) →
  log loss improves from 1.0689 to 1.0233 (Δ = -0.0456, a real gain from
  rating-based modelling).
- Elo → Poisson: uses actual goal counts, not just win/draw/loss →
  log loss improves further to 1.0097 (Δ = -0.0136) and, separately,
  Poisson's away-outcome calibration is materially better than Elo's
  (ECE 0.0240 vs. 0.0605).
- Poisson → `elo_poisson` blend: combining both fundamentals models (weights
  calibrated per-fold on training data only) improves log loss to 1.0035
  (Δ = -0.0062 vs. Poisson alone) and calibration further still (home ECE
  0.0130, away ECE 0.0128 — both better than either individual component).
- `elo_poisson` → market-inclusive blends: **zero further gain.** The
  exhaustive grid search puts 100% of the weight on market in every fold —
  once market is available as a candidate weight, no admixture of Elo or
  Poisson reduces in-sample log loss at all.

The pattern is coherent and monotonic exactly as expected from
market-efficiency reasoning: each added piece of real football information
narrows the gap to the market, but none of it is additive on top of what the
market consensus already prices in.

## Current honest verdict (development folds only)

No model or blend built in Stage 3B has beaten the market's closing
consensus on the development folds, and the market's advantage over every
fundamentals-only candidate is statistically confirmed (CIs entirely above
zero). This trends toward a **market dominates / null result** classification
for "beyond-market" predictive signal, but per the predeclared protocol this
is provisional until the sealed 2024/25 holdout is opened exactly once
(Checkpoint 6) — development-fold results, however clean, are not
themselves the final answer, and no development-fold finding should be used
to justify redesigning the holdout evaluation now that the pattern is
visible (that would itself be a form of leakage into the "final answer").

## Remaining before a final Stage 3B verdict

- `FINAL_HOLDOUT_PROTOCOL.md` (Checkpoint 5): written and committed before
  the 2024/25 season is read by any script.
- A `STAGE 3B PRE-HOLDOUT FREEZE` commit, locking every development-fold
  decision (model specs, blend weights methodology, bootstrap methodology)
  before the holdout is touched.
- Checkpoint 6: open the sealed holdout exactly once, score every model/
  blend candidate above against it, and issue the final Stage 3B verdict
  (`STAGE_3B_FINAL_REPORT.md`) — one of STRONG SIGNAL / WEAK-UNCERTAIN
  SIGNAL / MARKET DOMINATES-NULL RESULT / INVALID.
