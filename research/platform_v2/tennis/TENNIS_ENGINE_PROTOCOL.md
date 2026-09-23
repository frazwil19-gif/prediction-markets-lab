# Phase V2-1 Workstream B — Tennis Match Winner Probability Engine: Pre-registration (2026-09-23, before any 2024–25 outcome was computed)

## Question
How well can we predict who wins an ATP match, especially in the high-probability region? This is not an
edge-hunting question. Workstream B's 13 edge families stay closed; none is re-tested.

## Population
ATP main-tour matches in TML-Database (`cycle_002_canonical_matches.csv`), excluding walkovers, linked to a Betfair
MATCH_ODDS market (`workstream_b_2021_2025_linkage.csv`, MATCHED only), where **both** runners have a last-traded
price at or before 30 minutes before the market's final scheduled start, each no older than 1 hour (the Workstream B
primary horizon and freshness cap, reused unchanged). The Betfair per-runner price series were re-extracted on
2026-09-23 from Fraser's untouched `data.tar` (SHA-256 of every source member recorded).

## Periods
| period | exposure | role |
|---|---|---|
| 2021–2023 | market prices vs outcomes studied (Workstream B discovery, V2 audit bands); Global Elo's training window | DEVELOPMENT (descriptive; re-verifies the 20.7% figure) |
| 2024 | market-vs-outcome **never computed** ("2024 development validation NOT OPENED"); Elo validation year | part of SEALED HOLDOUT |
| 2025 | market-vs-outcome **never computed**; Elo sealed holdout already opened once (Cycle 1, PARTIAL) | part of SEALED HOLDOUT |

The holdout (2024–2025, market-linked) is evaluated **once**, by a guarded script, after this file and
`HOLDOUT_SPEC.json` are committed.

## Estimators (all frozen; nothing new is fitted except the single pre-declared stack)
1. `market_mult`: two-runner LTP pair, multiplicative normalisation. This is the existing Workstream B market reference, unchanged.
2. `market_<method>`: the same pair under the Workstream A methods (additive, power, odds-ratio, Shin).
3. `elo_global`: frozen Global Elo (k = 32). 2021–23 values are in-sample (its training window), so they are reported but never used to rank it.
4. `ranking_baseline`: frozen ranking model (reported only).
5. `stack_market_elo`: logistic regression on [logit(market_mult), logit(elo_global)], fitted on 2021–2023, frozen, then evaluated on the holdout. It is the one justified combination (two independent frozen probabilities). Its 2021–23 Elo inputs are in-sample, and that bias works *against* the stack (it over-trusts Elo), so it is conservative for the question "does adding Elo help?".
No Elo recalibration is re-fitted: Cycle 1 already tested a training-fit recalibration (intercept 0.027, slope 0.978,
about identity) and found it did not help on 2024. That finding is cited, not repeated.

## Selection rule (holdout, mechanical)
Default strongest estimator = `market_mult`. Another estimator replaces it only if its holdout log loss is lower with a
paired-bootstrap 95% CI (seed 20260923, 2,000 resamples) excluding zero. Reported for every estimator: log loss, Brier,
AUC, top-pick accuracy, calibration intercept/slope, ECE, bands 50–54.9 … 90–94.9, 95%+, thresholds ≥55 … ≥95 with
expected vs actual wins and Wilson CIs, split by year and surface.

## Decision gate (per the operator brief §37)
- **A:** the market estimator is calibrated on the holdout (slope CI includes 1, and every band with n ≥ 200 is within its CI) **and** a live source is demonstrated.
- **B:** calibrated but no dependable live source yet.
- **C:** calibration fails on the holdout.
- **D:** new information is required.
