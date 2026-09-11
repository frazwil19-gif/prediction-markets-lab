# Stage 3B Final Report — Sealed 2024/25 Holdout Evaluation (Checkpoint 6)

**This is the final, one-shot Stage 3B result. Generated from
`data/interim/stage_3b_checkpoint6_holdout_metrics.json`, produced by
`scripts/run_stage_3b_checkpoint6_holdout_evaluation.py`, run exactly once
against the sealed 2024/25 season per
`research/cycles/CYCLE_001/results/FINAL_HOLDOUT_PROTOCOL.md` and
`reports/audits/STAGE_3B_PRE_HOLDOUT_FREEZE.json`. Do not hand-edit the
numbers below; do not re-run this script with different parameters.**

Data version: `cycle_001_v1.0.0-20260910T234139`. Trained on all 4
development seasons (2020_21-2023_24) as one final fold; evaluated once on
2024/25.

## 1. Coverage (matches the pre-registered expectation exactly)

1,160 matches, all 3 competitions (E0: 380, E1: 552, SC0: 228) — every
single one had usable closing-consensus market data, so full coverage
equals the common sample for every candidate, including naive (unlike the
development folds, where 34/3,480 matches lacked usable market data).

## 2. Pooled holdout metrics (N=1,160)

| Candidate | Log loss | Brier | Δ log loss (vs. market) | Δ Brier (vs. market) |
|---|---|---|---|---|
| **Market (Baseline 1)** | 0.9937 | 0.5931 | — | — |
| `market_elo` | 0.9937 | 0.5931 | 0.0000 | 0.0000 |
| `market_poisson` | 0.9937 | 0.5931 | 0.0000 | 0.0000 |
| `market_elo_poisson` | 0.9937 | 0.5931 | 0.0000 | 0.0000 |
| `elo_poisson` | 1.0107 | 0.6053 | +0.0169 | +0.0122 |
| Poisson (Model 2) | 1.0127 | 0.6071 | +0.0190 | +0.0140 |
| Elo (Model 1) | 1.0283 | 0.6175 | +0.0346 | +0.0243 |
| Naive frequency (Baseline 0) | 1.0703 | 0.6472 | +0.0766 | +0.0541 |

Calibrated on the training period (all 4 development seasons): Elo
`draw_margin = 100.0`; blend weights — `elo_poisson` 0.40 Elo / 0.60
Poisson; `market_elo`, `market_poisson`, `market_elo_poisson` all
calibrated to **100% market weight**, exactly reproducing the pattern
observed on every one of the 3 development folds (see BLEND_REPORT.md) —
this is not an artifact of any single fold, it replicates when refit on
the full 4-season training period too.

## 3. Paired bootstrap confidence intervals (vs. market, both methods, 95% CI, n_resamples=2000, seed=42)

| Candidate | Log loss Δ (block-by-date 95% CI) | Brier Δ (block-by-date 95% CI) |
|---|---|---|
| Naive | +0.0766 [+0.0549, +0.0991] | — |
| Elo | +0.0346 [+0.0226, +0.0475] | — |
| Poisson | +0.0190 [+0.0058, +0.0316] | — |
| `elo_poisson` | +0.0169 **[+0.0066, +0.0274]** | +0.0122 [+0.0055, +0.0193] |
| `market_elo` / `market_poisson` / `market_elo_poisson` | 0.0000 [0.0000, 0.0000] (identical to market by construction) | — |

`elo_poisson` — the one candidate on this list that is not simply a copy
of market — has a 95% CI **entirely above zero** on the holdout: market's
advantage replicates out-of-sample, not just on the development folds it
was checked against 3 times already.

## 4. Raw calibration (ECE, ↓ better; 5 equal-count bins)

| Model | Home ECE | Draw ECE | Away ECE |
|---|---|---|---|
| Market | 0.0212 | **0.0056** | 0.0149 |
| **`elo_poisson`** | 0.0305 | 0.0261 | **0.0143** |
| Elo | 0.0572 | 0.0135 | 0.0470 |
| Poisson | **0.0183** | 0.0305 | 0.0169 |

Elo's away-outcome miscalibration bias, documented in
`CALIBRATION_REPORT.md` from the development folds (ECE 0.0605 there),
**replicates on the holdout** (ECE 0.0470 here) — the same real,
directional defect, not a development-fold coincidence. Unlike on the
development folds, `elo_poisson`'s calibration on the holdout is not
uniformly the best of the three model-based candidates (Poisson's home ECE
and market's draw ECE both beat it here) — with only 1,160 holdout matches
against 3,446 development matches, single-sample calibration comparisons
are noisier; the directional pattern (blending helps away-outcome
calibration specifically, where Elo's defect lives) still holds.

## 5. Replication check against the development folds

| | Development (N=3,446) | Holdout (N=1,160) |
|---|---|---|
| Market log loss | 0.9773 | 0.9937 |
| Elo Δ vs. market | +0.0460 | +0.0346 |
| Poisson Δ vs. market | +0.0324 | +0.0190 |
| `elo_poisson` Δ vs. market | +0.0262 | +0.0169 |
| Market-inclusive blends | 100% market weight | 100% market weight (replicated) |

Every ranking and every qualitative finding from Checkpoints 1-4 replicates
on the sealed holdout: naive < Elo < Poisson < `elo_poisson` < market, in
that order, every time. The absolute size of the market's advantage is
somewhat SMALLER on the 2024/25 holdout than on the development folds
(`elo_poisson`'s gap shrinks from +0.0262 to +0.0169, roughly a third
smaller) — consistent with ordinary season-to-season variation, not
evidence the underlying pattern is different; the gap's CI is still
entirely above zero.

## 6. Verdict — reported transparently, including a genuine ambiguity discovered only at this step

The frozen rubric (`FINAL_HOLDOUT_PROTOCOL.md` §5) is applied to "the
best-performing non-market candidate on the holdout, by pooled log loss."
This produces a mechanical ambiguity the protocol did not anticipate:
**three of the eight predeclared candidates (`market_elo`,
`market_poisson`, `market_elo_poisson`) are numerically IDENTICAL to
market**, because their blend weights calibrated to 100% market on the
training data (see §2). Python's `min()` breaks this three-way tie (and
the tie with market itself) by candidate-list order, mechanically selecting
`market_elo` as "the best non-market candidate" with a log-loss delta of
exactly 0.0000 and a bootstrap CI of exactly [0.0000, 0.0000].

Applying the frozen rubric literally and mechanically to that selection:

> **Best candidate: `market_elo`. Delta ≈ 0.0000 (|delta| < 0.005). Per
> §5's rule, this is classified WEAK-UNCERTAIN SIGNAL.**

This is not being silently overridden or re-run — the rubric was
pre-committed specifically so a result could not be reclassified after the
fact, and this is its literal output. But it is reported here alongside
the honest caveat that a candidate identical to market by construction is
not a substantive "signal" of any kind, weak or otherwise — it is a tie,
and the rubric's wording did not anticipate that the best-scoring
non-market candidate could be a candidate with zero actual daylight from
market.

**The substantively meaningful comparison — the only candidate on the
predeclared list that is not simply a copy of market — is `elo_poisson`.**
Applying the identical rubric to `elo_poisson` specifically: its delta is
+0.0169 (positive — market wins) and its 95% CI [+0.0066, +0.0274] lies
entirely above zero. Per §5's own criteria, this is
**MARKET DOMINATES / NULL RESULT** — the same classification the
development folds already pointed toward across all of Checkpoints 1-4,
now replicated on data that has never been looked at until this exact run.

## 7. Overall Stage 3B conclusion

No genuinely distinct model or blend — Elo, Poisson, or their combination —
beat the market's closing consensus on either the development folds or the
sealed holdout. The market-inclusive blends did not add anything either;
they simply rediscovered the market, every single time asked. This is a
clean, internally consistent, twice-confirmed (development + holdout) null
result for "does public historical match/goal data, modelled by
transparent statistical methods, contain predictive information beyond
what a liquid bookmaker consensus already prices in" — and per
`FINAL_HOLDOUT_PROTOCOL.md` §6, a clean null result is a complete and valid
outcome of this project, not a failure requiring further development-fold
iteration.

**Stage 3B is closed.** The holdout was opened exactly once, per the frozen
protocol; no parameter was retuned afterward; no candidate was added or
removed after seeing the result. Any further work on this question — a
genuinely new information source (team news, weather, referee assignments,
line-movement/CLV data with real execution timing, player-level data) or a
materially different modelling approach — would constitute a new research
cycle (Cycle 2) with its own pre-registration, not a continuation of Cycle
1.

Any staking, EV-threshold, or execution-strategy work remains explicitly
out of scope (unchanged from `STAGE_3B_PLAN.md` §1) and is not implied or
justified by anything in this report — this project has not yet
established that it has an edge to stake against.
