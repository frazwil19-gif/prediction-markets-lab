# Phase V2-3 — NBA Moneyline Outcome Prediction: Pre-registration (2026-09-24, before any outcome-linked statistic)

## Question
How accurately can we predict which NBA team wins, and does NBA have a large, well-calibrated high-probability
region? This is not a market-beating question.

## Exposure before this protocol
Only availability counts, stage counts, and a *label and price agreement* cross-check between the two sources
(winner agreement 99.8%, implied-probability correlation 0.997). No relationship between any feature or price and the
outcome was computed. **Every season 2016-17 → 2025-26 is untouched for prediction purposes.**

## Data (free, GitHub-hosted; no manual download; SHA-256 in `data/raw/basketball/SHA256SUMS`)
- Primary: `wippa-studios/wippa-nba-data` (MIT). OddsPortal results + **average closing decimal moneyline odds**
  across the bookmakers OddsPortal lists, 2016-17 → 2025-26.
- Warm-up and cross-check: `flancast90/sportsbookreview-scraper` (MIT). SBR results + closing moneylines 2011-12 → 2021-22.
  Results before 2016-17 are used only to warm up Elo.
- Declared caveats: OddsPortal dates run +1 day versus US dates for 97% of games (a consistent timezone offset, so
  rest/back-to-back counts are unaffected); one "average closing" price, no book-level panel or timestamps; no box
  scores, no injuries or lineups. Features are derived from scores and schedule only.

## Eligibility (fixed)
Regular season, play-in and playoffs included; pre-season and All-Star excluded. Overtime is valid (winner counts).
Postponed or cancelled games don't appear (no result row). No ties exist. The 2020 bubble (30 Jul – 11 Oct 2020) is
flagged `neutral` (no home advantage in Elo; a feature for other models). Games without odds are excluded from
model comparison (0 in the primary source) but still update Elo and rolling features.

## Chronology (fixed)
| role | seasons |
|---|---|
| Elo warm-up only | 2011-12 → 2015-16 (SBR results) |
| DEVELOPMENT (discovery, parameter choice, fitting) | 2016-17 → 2021-22 |
| VALIDATION (reported; not used for choosing) | 2022-23 → 2023-24 |
| **SEALED HOLDOUT (opened once)** | **2024-25 → 2025-26** |
Final fitted models for the holdout are refitted on development+validation with the hyperparameters frozen from
development.

## Features (home minus away unless noted; all from strictly earlier games; a team plays at most once per date)
rest days (capped at 5) for each side · back-to-back flag for each side · games in the previous 7 days for each side ·
rolling last-10 point differential · rolling last-10 win % · season-to-date point differential per game (shrunk with 5
pseudo-games at 0) · season game number (min of the two) · neutral flag · pre-game Elo home-win logit.

## Estimators (pre-declared)
1. `market`: two-way proportional de-vig of the average closing odds (the project standard).
2. `elo`: Elo with carry-over 0.75·R + 0.25·1505 per new season. Grid chosen on development log loss: K ∈ {10, 15, 20,
   25} × home advantage ∈ {50, 75, 100} Elo points × margin-of-victory multiplier ∈ {off, 538-style
   ((MOV+3)^0.8)/(7.5+0.006·winner Elo edge)}.
3. `data_logit`: L2 logistic regression (standardised, L2 = 1.0) on the features above (includes the Elo logit).
4. `stack_market_elo`: logistic on [logit(market), logit(elo)].
Default estimator = market. Another replaces it only if its holdout log loss is lower with a paired-bootstrap 95% CI
(seed 20260924, 2,000 resamples) excluding zero.

## Reporting
Log loss, Brier, AUC, top-pick accuracy (expected vs actual), calibration intercept/slope with a 1,000-sample
bootstrap CI, bands 50–54.9 … 95%+, thresholds ≥55 … ≥95 (count, share, mean P, expected vs actual, Wilson CI), and
splits by season, regular vs playoffs, and home vs away pick. Discovery (development only): home-win vs home-loss
means and Cohen's d per feature, with per-season stability.

## Decision gates
Data gate: A (existing) / B (free new) / C (low-cost needed) / D (insufficient). Prediction gate: **A validated
candidate** if the selected estimator's holdout slope CI includes 1 and every band with n ≥ 200 has its predicted mean
inside the realised rate's 99.5% Wilson interval; **B** if calibrated on one criterion only; **C** if both fail;
**D** if data limits prevent the test.
