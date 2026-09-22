# Phase 5 — Football BTTS: Pre-registration (written BEFORE any model result existed)

Date: 2026-09-22. Author: Claude (research engineer). Operator: Fraser.

This file is committed alongside the results. It was written before the development
stage was run; any later deviation is recorded in `VALIDATION_REPORT.md` under "Deviations".

## Target
`btts_yes = 1` if home goals >= 1 AND away goals >= 1, else 0. `P(NO) = 1 - P(YES)` by construction.

## Data
`data/processed/football/cycle_002_discovery_features.csv` (E0/E1/SC0, 2020/21–2024/25, 5,800 matches),
unchanged. No new acquisition. Historical BTTS bookmaker odds do NOT exist in football-data.co.uk, so
a true BTTS "market-only" model (Model A) and "BTTS market + data" (Model C) are NOT buildable historically.

## Chronological design
- Discovery (effect sizes, feature exploration): 2020/21, 2021/22, 2022/23.
- Development model comparison: expanding walk-forward, evaluation seasons 2021/22, 2022/23, 2023/24
  (each fold trains only on strictly earlier seasons). 2023/24 alone = VALIDATION.
- SEALED HOLDOUT: 2024/25, train on 2020/21–2023/24, evaluated EXACTLY ONCE after `HOLDOUT_PROTOCOL.json`
  is frozen and hashed. Caveat carried from Phases 2–4: 2024/25 raw data was used by earlier 1X2/OU2.5
  cycles, so it is blind for BTTS-specific relationships only, not for the dataset as a whole.

## Pre-declared model set (no others will be selectable)
| key | description | fitted params |
|---|---|---|
| naive | training-set BTTS base rate | 1 |
| data_logit | L2 logistic (L2=1.0, standardised on train) on 19 Gate-1b fundamentals + 10 new rolling scoring/clean-sheet/BTTS-rate features | 30 |
| poisson_goal | project's existing leakage-safe `PoissonRatingBook` lambdas, BTTS = (1-e^-λh)(1-e^-λa), no fitting | 0 |
| market_implied_poisson | λh, λa solved from CLOSING de-vigged 1X2 consensus + closing OU2.5 probability, then independent-Poisson BTTS, no fitting. Labelled MARKET-DERIVED, NOT a BTTS market price | 0 |
| market_implied_poisson_recal | logistic recalibration of logit(market_implied_poisson), fitted on train only | 2 |
| market_implied_plus_data | logistic on logit(market_implied_poisson) + data_logit's 29 features | 31 |

Sensitivity only (never selectable): `market_implied_poisson_opening` (same, OPENING prices) — live scans happen
between open and close, so the deployable number sits between these two.

## Selection rule (mechanical)
On the development pooled set restricted to matches every model can score (common set):
1. Lowest pooled log loss wins.
2. If another model with FEWER fitted parameters has a paired-bootstrap 95% CI (seed 20260922, 2,000 resamples)
   for its log-loss difference vs the winner that includes zero, the simpler model is selected instead.
3. The selected estimator, its calibration procedure, feature list and hyperparameters are frozen in
   `HOLDOUT_PROTOCOL.json` before the holdout is opened.

## Reported regardless of result
Brier, log loss, AUC, accuracy, balanced accuracy, calibration (fixed 10 bands + intercept/slope), probability
bands 50–54.9 … 80%+ for YES and NO separately with Wilson 95% CIs, top-prediction accuracy by season and
competition, thresholds P>=0.60/0.65/0.70/0.75/0.80. No money threshold, EV floor, odds floor or stake is
used or tuned anywhere in this phase.

## Error analysis
Correct vs incorrect high-probability (>=0.60 on the picked side) predictions on development data are compared on
pre-declared characteristics: season stage, team history depth, newly-promoted status, |Elo gap|, competition,
scoring-rate volatility. Any filter suggested is written into the holdout protocol and tested once on the holdout;
it is not accepted without that.
