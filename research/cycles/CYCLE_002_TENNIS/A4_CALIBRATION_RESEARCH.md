# Cycle 2 Tennis -- Global Elo Calibration Research

*Generated 2026-09-15T21:41:18.637583+00:00*

**PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.** No price/odds data is used. This investigates ONE simple, pre-specified, forward-safe calibration method for Global Elo (the accepted odds-independent candidate model), fit on training data only and applied unchanged to validation -- never the reverse.

- Training seasons: [2021, 2022, 2023] (calibration parameters fit here only)
- Validation season: 2024 (calibration applied out-of-sample, evaluated here)
- Sealed holdout: 2025 -- **never loaded by this script**
- Global Elo k_factor: 32.0
- Decision rule (stated before running): adopt calibration only if the paired-bootstrap 95% CI for (calibrated log loss - raw log loss) lies entirely below zero. Otherwise: CALIBRATION = NONE.

## Fitted calibration parameters (from training data only)

- intercept = 0.0267
- slope = 0.9783
These are close to identity (intercept~=0, slope~=1): Global Elo is already close to well-calibrated ON ITS OWN TRAINING PERIOD. This is a different number from A4's validation-season calibration slope (0.8749) -- that overconfidence pattern shows up only on 2024, so a correction fit purely on 2021-2023 has little reason to fix it, and (see below) largely doesn't. That is exactly the honest, forward-safe outcome this test is designed to expose, not a bug.

## Validation-season comparison: raw vs. calibrated

| Variant | n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |
|---|---|---|---|---|---|---|---|
| raw | 3055 | 0.6248 | 0.2188 | 0.6991 | 0.0205 | 0.8749 | 0.0242 |
| calibrated | 3055 | 0.6244 | 0.2186 | 0.6991 | -0.0034 | 0.8943 | 0.0231 |

AUC is identical for both by construction: a monotonic logit-linear recalibration cannot change rank ordering, only the scale of the probabilities.

**Paired bootstrap** (n=3055, 2000 resamples): delta (calibrated - raw) = -0.0004, 95% CI [-0.0009, 0.0001]

## Decision: CALIBRATION = NONE (raw Global Elo probabilities are used unchanged)

The CI does not exclude zero (or excludes it in the wrong direction), so per the pre-stated decision rule, calibration is NOT adopted. Raw Global Elo output is used unchanged going forward, despite its mild overconfidence -- forcing a correction that doesn't demonstrably help out-of-sample would be curve-fitting to one validation season.
