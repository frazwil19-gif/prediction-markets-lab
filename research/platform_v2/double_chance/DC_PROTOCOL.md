# V2-4 Football Double Chance — Pre-registration (written and committed BEFORE any DC evaluation beyond the
# earlier descriptive note) — 2026-09-24

## Question
How reliable are Double Chance probabilities **derived from the frozen football 1X2 consensus** (no new model, no
tuning), and are the strong ones (≥80%) frequent, calibrated and stable enough to justify a prospective DC paper board?

## Estimator (frozen, no fitting)
Per-book proportional (multiplicative) de-vig; consensus = mean of per-book probabilities (the production
`football_1x2.market_consensus` method). DC probabilities: P(1X) = pH + pD, P(X2) = pD + pA, P(12) = pH + pA. No
recalibration (the 1X2 slope of ~1.06–1.09 is **reported, not corrected**).

## Events
Each of 1X, X2, 12 for each match is a **separate binary event** (3 per match; they are dependent, so the confidence
intervals below treat matches, not events, as the resampling unit). The operational view is the **best DC selection
per match** (the argmax, one per match).

## Data and periods (all EXPOSED: these seasons were used for 1X2 validation and the V2-1 de-vig study)
Primary panel: closing odds B365/BW/PS (the V2-1 primary panel), 2020/21–2025/26, E0/E1/SC0.
Sensitivity panels: all-books closing and all-books opening (2020/21–2024/25), odds-ratio and Shin de-vig on the primary
panel. Periods: development 2020/21–2022/23 · validation 2023/24–2024/25 · confirmation 2025/26 (least exposed).
**No untouched historical data exists locally.** The only untouched data is 2026/27 (in progress). It is only reachable
from GitHub runners, so it is sealed below and not read in this phase.

## Metrics
Binary log loss, Brier, AUC, calibration intercept and slope (logit) with a 1,000-resample match-level bootstrap CI (seed
20260924). Bands 50–54.9 … 95%+ and thresholds ≥60, ≥65 … ≥95 (count, share of matches, mean predicted, expected vs
actual, Wilson 95% and 99.5%). Splits: league × season at ≥80; selection type (1X = home-side, X2 = away-side, 12).

## Decision gate (applied to validation + confirmation; the development period is descriptive only)
- **A**: slope CI includes 1 AND every band with n ≥ 200 has mean predicted inside the realised rate's 99.5% Wilson
  interval AND ≥80 share ≥ 15% of matches in every season. **Because the data are exposed, A = "validated on exposed
  data; prospective/sealed confirmation required", never money-eligible.**
- **B**: exactly one of the calibration criteria holds.
- **C**: both calibration criteria fail.
- **D**: data limits prevent the test.
- Live price availability is reported separately and does not change the probability grade.

## Sealed holdout (pre-registered, not opened in this phase)
E0/E1/SC0 2026/27 matches dated 2026-08-01 → 2026-12-31, from football-data.co.uk closing B365/BW/PS, same estimator and
metrics, opened once after 2027-01-03 by a guarded script (HOLDOUT_SPEC.json + .sha256). Pass = the same A criteria.
Expected size ≈ 600 matches (≈190 ≥80 picks), which is low power: the holdout is a check, not a discovery tool.

## Things that will not be done
No tuning of thresholds on the results, no recalibration, no market-inefficiency claim, no stakes.
