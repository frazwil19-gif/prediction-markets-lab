# Phase 5 — BTTS Development / Validation Report

Expanding walk-forward, evaluation seasons 2021/22, 2022/23, 2023/24 (each trained only on earlier seasons).
Common set = matches every model scores: **n = 3,437** (of 3,480). Validation = 2023/24 alone (n = 1,125).
Base rate on the common set: 51.1% YES.

## Development pooled (common set)
| model | params | log loss | Brier | AUC | accuracy | bal. acc | cal. intercept / slope | ECE |
|---|---|---|---|---|---|---|---|---|
| naive | 1 | 0.6956 | 0.2512 | 0.526* | 48.9% | 50.0% | — | 4.1% |
| data_logit | 30 | 0.6964 | 0.2515 | 0.528 | 52.2% | 52.5% | 0.07 / **0.39** | 3.4% |
| poisson_goal | 0 | 0.7024 | 0.2543 | 0.528 | 51.7% | 51.9% | 0.07 / **0.26** | 5.3% |
| **market_implied_poisson** | 0 | **0.6867** | **0.2468** | **0.560** | **53.7%** | 53.8% | 0.04 / **1.06** | **1.2%** |
| market_implied_poisson_recal | 2 | 0.6883 | 0.2476 | 0.559 | 53.4% | 53.8% | 0.12 / 1.12 | 2.8% |
| market_implied_plus_data | 31 | 0.6931 | 0.2499 | 0.548 | 53.7% | 53.9% | 0.08 / 0.56 | 3.0% |
| *market_implied_poisson_opening* (sensitivity) | 0 | 0.6875 | 0.2472 | 0.553 | 53.2% | 53.2% | 0.03 / 1.06 | 1.0% |

\*naive AUC is above 0.5 only because its constant changes between folds.

Paired bootstrap (log-loss difference vs market_implied_poisson; 2,000 resamples, seed 20260922). **Every alternative is
worse, with the 95% CI excluding zero**: naive +0.0089 [0.0051, 0.0130], data_logit +0.0097 [0.0044, 0.0149],
poisson_goal +0.0157 [0.0101, 0.0215], recalibrated +0.0016 [0.0003, 0.0030], market+data +0.0064 [0.0021, 0.0106].

**Selected estimator (mechanical, pre-registered rule): `market_implied_poisson`.** It is the lowest-log-loss model, and
it already has the minimum number of fitted parameters (zero).

## Validation 2023/24 only
market_implied_poisson: log loss 0.6776, Brier 0.2423, AUC 0.591, accuracy 56.9%. Ranking unchanged. Base rate jumped
to 54.8%, and the naive model (trained on older, lower-scoring seasons) fell to 45.2% accuracy. This non-stationarity
hurts every model that learns a level from history. The market-derived estimator carries the current level in its prices.

## What the data says about BTTS
- **Pre-match separation is weak.** The strongest discovery-period feature is the market-implied BTTS probability itself
  (Cohen's d 0.15, univariate AUC 0.54). The best *data* features (away shots, away SOT, away goals for) are at d ≈ 0.07–0.09.
  Nothing reaches d = 0.2.
- **Stability:** 22 of 44 inspected features were STABLE from discovery to validation, 11 WEAKENED and 11 SIGN_FLIP.
  Home team scoring rate, for example, flipped from −0.08 to +0.18. The 2020/21 empty-stadium season is a plausible
  confounder. `FEATURE_STABILITY.csv` has the full table.
- **Fitted data models overfit.** Calibration slopes of 0.26–0.56 mean their confident predictions are too confident.
  That includes the goal model and market+data. This is the same failure mode the 1X2 fundamentals model showed.
- **Market still dominates, even for a market we had no direct BTTS prices for.** Goal expectations implied by 1X2 and
  O/U prices beat every model built from historical stats.

## Deviations from pre-registration
None in the models or rule. Two implementation fixes were made before any result was read, and neither is a
methodology change: calibration intercept/slope is reported as undefined for a constant-probability model, where the
fit is singular, and a guard was added for zero-shrinkage division.
