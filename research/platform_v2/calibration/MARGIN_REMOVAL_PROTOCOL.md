# Phase V2-1 Workstream A — Margin-Removal Calibration Protocol (pre-registered 2026-09-23, before any method result)

## Question
Which established margin-removal method turns bookmaker prices into probabilities that best match real outcome
frequencies on data not used to choose it? The question is not which method creates bets or favours favourites.

## Current production pipeline (audited)
`probability/market_pipeline.compute_market_consensus`: for each bookmaker, decimal odds → raw implied q = 1/odds →
overround B = Σq → **proportional (multiplicative) de-vig p = q/B** → consensus = mean across accepted bookmakers of
each book's p (complete markets only). `research/margin_removal_methods.multiplicative` is asserted identical to
production in tests.

## Methods compared (zero parameters fitted to outcomes)
multiplicative (production), additive, power, odds-ratio (Cheung), Shin. Same aggregation rule (mean over books).

## Data and exposure classification
| set | seasons / years | exposure | role |
|---|---|---|---|
| Football 1X2, E0/E1/SC0 | 2020/21–2022/23 | fully exposed (Stage 3B, Gate 1, Backtest Phase 1, V2 audit bands) | DEVELOPMENT |
| Football 1X2 | 2023/24–2024/25 | exposed the same way | VALIDATION (not a holdout) |
| Football 1X2 | 2025/26 (raw files, 1,140+ matches) | proportional consensus used for Gate 1 aggregate log loss; **never used for band calibration or method comparison** | LEAST-EXPOSED CONFIRMATION (declared as not fully sealed) |
| Tennis Betfair LTP, ATP | 2021–2023 | exposed (Workstream B discovery, V2 audit bands) | DEVELOPMENT |
| Tennis Betfair LTP, ATP | 2024–2025 | price coverage audited; **price-vs-outcome never computed** (Workstream B: "NOT OPENED") | SEALED HOLDOUT, opened once, jointly with Workstream B |

Primary football panel: B365, BW, PS closing (the three books present in every season including 2025/26), so the
panel is constant across periods. Sensitivity: every book in `cycle_001_bookmaker_markets_full.csv` (2020/21–2024/25),
and opening prices. Tennis: the two runners' last-traded prices 30 minutes before the scheduled start (the Workstream B
primary horizon), both fresh.

## Metrics
Primary: log loss (3-way for football, binary for tennis). Also: Brier, calibration intercept/slope (pooled outcome
candidates), ECE, and fixed probability bands 50–54.9 … 90–94.9, 95%+ with Wilson 95% CIs; threshold table
≥55 … ≥95%.

## Decision rule (mechanical)
Let D = mean log-loss difference (method − multiplicative), with a match-level paired bootstrap 95% CI
(2,000 resamples, seed 20260923).
- **B (alternative better → prospective paper validation):** a method has D < 0 with CI excluding zero on DEVELOPMENT
  **and** on VALIDATION, and does not worsen on the confirmation set (point estimate ≤ 0). If several qualify, choose
  the lowest validation log loss.
- **C (too small / uncertain → retain):** no method meets B, but some method has D < 0 on both periods with a CI that
  includes zero.
- **A (proportional best supported):** multiplicative has the lowest log loss on development and validation.
- **D (insufficient evidence):** the periods disagree in sign, or samples are too small.
The tennis holdout is reported under the same rule as corroboration. No production change follows from any outcome
without Fraser's approval.

## Explicitly not done
No method chosen for favourite size. No post-hoc correction fitted to outcomes (for example, isotonic boosting of
favourites). No betting or EV metric.
