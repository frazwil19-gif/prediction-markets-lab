# Phase 5 — BTTS Probability-Band, High-Probability & Error Analysis

Estimator: `market_implied_poisson`. Full tables for every model: `PROBABILITY_BANDS.csv`,
`HIGH_PROBABILITY_ANALYSIS.csv`, `TOP_PREDICTION_PERFORMANCE.csv` (development), and the `HOLDOUT_*.csv` equivalents.

## Headline: BTTS almost never produces a strong prediction
Estimated P(YES) spans only **0.31–0.72**. The market itself rarely sees BTTS as far from a coin flip. Only **6.9%**
of development matches and **10.1%** of holdout matches have a picked side at ≥60%. **No match reached 75%**, on either
side, in 4,595 evaluated matches.

## Probability bands — when it says X%, how often does it happen?
| side | band | dev n | dev predicted → actual | holdout n | holdout predicted → actual [95% CI] |
|---|---|---|---|---|---|
| YES | 50–54.9% | 986 | 52.3% → 51.9% | 420 | 52.4% → 56.9% [52.1, 61.6] |
| YES | 55–59.9% | 392 | 57.0% → 58.2% | 202 | 57.1% → 55.4% [48.6, 62.1] |
| YES | 60–64.9% | 136 | 62.1% → 65.4% | 72 | 62.0% → 63.9% [52.4, 74.0] |
| YES | 65–69.9% | 28 | 67.0% → 89.3% | 21 | 66.6% → 61.9% [40.9, 79.2] |
| YES | 70–74.9% | 5 | 70.9% → 40.0% | 4 | 71.2% → 50.0% |
| YES | 75%+ | 0 | — | 0 | — |
| NO | 50–54.9% | 1,373 | 52.4% → 51.7% | 305 | 52.2% → 51.1% [45.6, 56.7] |
| NO | 55–59.9% | 448 | 56.8% → 52.9% | 114 | 56.9% → 57.9% [48.7, 66.6] |
| NO | 60–64.9% | 64 | 61.4% → 60.9% | 19 | 62.0% → 63.2% [41.0, 80.9] |
| NO | 65%+ | 5 | 66.0% → 80.0% | 1 | 66.3% → 100% |

Across every band with n ≥ 100, calibration error stays within about ±4.5 pp. The 65–69.9% YES band ran hot in
development (89%, n = 28) and did not repeat on the holdout (62%, n = 21). That is small-sample noise, not a
reliable pocket.

## Thresholds (either side, top pick)
| threshold | dev n | dev predicted → actual [95% CI] | holdout n | holdout predicted → actual [95% CI] |
|---|---|---|---|---|
| ≥ 0.60 | 238 | 62.8% → 66.8% [60.6, 72.5] | 117 | 63.2% → 63.2% [54.2, 71.4] |
| ≥ 0.65 | 38 | 67.4% → 81.6% [66.6, 90.8] | 26 | 67.3% → 61.5% [42.5, 77.6] |
| ≥ 0.70 | 5 | 70.9% → 40.0% | 4 | 71.2% → 50.0% |
| ≥ 0.75 | 0 | — | 0 | — |
| ≥ 0.80 | 0 | — | 0 | — |

**The ≥60% predictions are reliable. They happen about as often as stated (holdout: 63.2% predicted, 63.2% actual).
The ≥65% region is too thin to trust. Above 70% the question can't be answered, because such predictions don't exist.**

## Top-prediction performance (pick the more likely side)
Development 53.7% correct (1,846 / 3,437) at 54.2% mean confidence. By season: 53.1% / 51.2% / 56.9%. By competition:
E0 55.9%, E1 52.7%, SC0 52.7%. Holdout **55.9% correct (647 / 1,158) at 54.7% mean confidence**, 13.6 more correct
than expected. By competition: E0 56.1%, E1 56.2%, SC0 54.8%.

## Winner/loser error analysis (≥60% picks)
Development (n = 238, 66.8% correct): no characteristic separated wrong from right picks with non-overlapping CIs.
The largest gap was competition (E0 71.2% vs E1 56.3%). Season stage, history depth, newly-promoted teams, Elo
mismatch and goal-difference volatility showed nothing consistent.

The one filter pre-registered for holdout testing was "exclude E1 picks". It **failed**: holdout E1 picks were 65.2%
correct (n = 23) and the rest 62.8% (n = 94), the opposite direction. **Rejected; no reliability filter is accepted.**
Holdout also showed early-season (≤6 matches) picks at 47.1% (n = 17) vs 66.0% later. That was not pre-registered,
so it is recorded only as a hypothesis for prospective monitoring.
