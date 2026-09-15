# Cycle 2 Tennis -- Workstream A4 Baseline Results (A, B, C)

*Generated 2026-09-15T20:27:50.916293+00:00*

**PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.** No price/odds data of any kind is used anywhere in this report; see reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md for the separate, still-open search for a usable historical-odds source.

## 1. Scope and split

- Training/calibration seasons: [2021, 2022, 2023] (n=8588)
- Validation season: 2024 (n=3055)
- Sealed holdout season: 2025 -- **never loaded by this script** (excluded at the CSV read itself, plus an assertion immediately after)
- Models: (A) ranking-only baseline, (B) global Elo, (C) surface Elo -- independent standalone predictors, not blended
- Retirements included without special handling (documented simplification). Walkovers already excluded upstream by Workstream A2.
- Ranking baseline excludes matches with an unranked player (never imputed); both Elo models score every match.

## 2. Headline validation-season metrics

| Model | Coverage n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |
|---|---|---|---|---|---|---|---|
| A. Ranking baseline | 3002 | 0.6361 | 0.2219 | 0.6923 | -0.0069 | 0.8991 | 0.0226 |
| B. Global Elo | 3055 | 0.6248 | 0.2188 | 0.6991 | 0.0205 | 0.8749 | 0.0242 |
| C. Surface Elo | 3055 | 0.6334 | 0.2224 | 0.6886 | 0.0251 | 0.8197 | 0.0353 |

A well-calibrated model has calibration intercept ~= 0 and slope ~= 1. The naive floor for log loss is ln(2) ~= 0.6931 (always predicting 0.5).

### Calibrated k_factor

- Global Elo: k_factor = 32.0
- Surface Elo: k_factor = 48.0
- Candidates searched: [16.0, 24.0, 32.0, 40.0, 48.0, 64.0]

## 3. Common-sample comparison (matches all three models can score)

The ranking baseline only covers matches where both players are ranked, so comparing models on their own full-coverage samples is not apples-to-apples. This section restricts ALL THREE models to that common, ranking-usable subset.

| Model | Common-sample n | Log loss | Brier |
|---|---|---|---|
| A. Ranking baseline | 3002 | 0.6361 | 0.2219 |
| B. Global Elo | 3002 | 0.6239 | 0.2183 |
| C. Surface Elo | 3002 | 0.6329 | 0.2221 |

## 4. Paired bootstrap uncertainty (common sample, log loss delta)

**B. Global Elo vs A. Ranking baseline** (n=3002, 2000 resamples): delta = -0.0122, 95% CI [-0.0230, -0.0017]

**C. Surface Elo vs B. Global Elo** (n=3002, 2000 resamples): delta = 0.0090, 95% CI [0.0011, 0.0175]

Negative delta means the first-named model has the lower (better) log loss. A CI excluding zero means the gap is unlikely to be sampling noise -- this is still a predictive-performance statement only, not a betting-edge claim.

## 5. Subgroup diagnostics (global Elo, full validation coverage)

### By surface

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| Hard | 1759 | 0.6238 | 0.2180 | 0.4983 | 0.5094 |
| Clay | 972 | 0.6303 | 0.2216 | 0.4929 | 0.5021 |
| Grass | 324 | 0.6134 | 0.2148 | 0.5060 | 0.4630 |

### By tourney_level

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| 250 | 986 | 0.6558 | 0.2317 | 0.5052 | 0.5071 |
| M | 691 | 0.6358 | 0.2230 | 0.4908 | 0.4573 |
| G | 505 | 0.5327 | 0.1798 | 0.4912 | 0.5168 |
| 500 | 433 | 0.6269 | 0.2193 | 0.4925 | 0.5173 |
| D | 259 | 0.6652 | 0.2378 | 0.4987 | 0.5560 |
| A | 103 | 0.6812 | 0.2428 | 0.5203 | 0.5049 |
| O | 63 | 0.4984 | 0.1675 | 0.5125 | 0.5397 |
| F | 15 | 0.5628 | 0.1911 | 0.3934 | 0.2000 |

### By best_of

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| 3 | 2535 | 0.6416 | 0.2259 | 0.4981 | 0.4990 |
| 5 | 520 | 0.5426 | 0.1842 | 0.4938 | 0.5173 |

### By rank_gap (usable-ranking matches only)

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| (5.999999999999994e-05, 0.273] | 601 | 0.6798 | 0.2433 | 0.5028 | 0.5092 |
| (0.273, 0.563] | 600 | 0.6942 | 0.2503 | 0.5000 | 0.5233 |
| (0.563, 0.923] | 600 | 0.6595 | 0.2334 | 0.5056 | 0.5083 |
| (0.923, 1.5] | 600 | 0.5987 | 0.2051 | 0.4897 | 0.4700 |
| (1.5, 7.995] | 601 | 0.4873 | 0.1597 | 0.4860 | 0.4942 |

## 6. What this does and does not show

- This compares three PREDICTIVE models against each other on match outcomes. None of it is compared to a market price, because no verified historical-odds source is connected yet (see the odds-source audit doc). A model beating the ranking baseline here says nothing about whether it would beat a bookmaker's line.
- Not yet built (Workstream A4 step D, next): incremental feature models testing recent form, surface-specific form, and congestion/rest as information ADDED BEYOND these rating-based baselines, per the pre-registered candidates in research/cycles/CYCLE_002_TENNIS/EXPLORATORY_ANALYSIS.md section 9.
- No hyperparameter search beyond the small predeclared k_factor grid above -- per the explicit instruction to build robust baselines, not optimise for their own sake.
- 2025 is completely unexamined by this script. It remains a sealed holdout for whatever model is eventually selected as the cycle's primary candidate.
