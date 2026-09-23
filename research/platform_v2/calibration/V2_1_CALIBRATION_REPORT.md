# Phase V2-1 Workstream A — Margin-Removal Calibration Report (2026-09-23)

Protocol: `MARGIN_REMOVAL_PROTOCOL.md` (pre-registered; committed in `8ca4264` with the results). Code:
`research/margin_removal_methods.py` (5 methods; `multiplicative` is asserted identical to production),
`scripts/run_v2_1_margin_removal_study.py`. Tables: `MARGIN_REMOVAL_RESULTS.csv`, `MARGIN_REMOVAL_BOOTSTRAP.csv`,
`HIGH_PROBABILITY_CALIBRATION.csv` (bands), `HIGH_PROBABILITY_THRESHOLDS.csv`, `PANEL_SIZES.json`,
`CONFIRMATION_2025_26_TWO_BOOK_SENSITIVITY.json`. Tennis holdout: `../tennis/`.

## 1. Current production method (audited)
Decimal odds → q = 1/odds per bookmaker → overround B = Σq → **p = q/B (proportional)** → consensus = mean of
per-book p across accepted books. Nothing else is applied.

## 2. Log loss by method (lower is better; Δ vs multiplicative with 95% CI)
| data | n | multiplicative | additive | power | odds-ratio | Shin |
|---|---|---|---|---|---|---|
| Football dev 2020/21–22/23 (B365/BW/PS closing) | 3,477 | 0.99280 | −0.00039 [−0.0012, +0.0004] | −0.00036 [−0.0012, +0.0004] | −0.00029 [−0.0008, +0.0002] | −0.00033 [−0.0009, +0.0002] |
| Football validation 2023/24–24/25 | 1,884 | 0.97205 | −0.00073 [−0.0018, +0.0004] | −0.00086 [−0.0020, +0.0004] | −0.00065 [−0.0013, +0.0001] | −0.00060 [−0.0014, +0.0003] |
| Football 2025/26 confirmation (least exposed) | 536 | 1.02624 | +0.00029 | +0.00061 | +0.00042 | +0.00018 |
| Football 2025/26, B365+BW (sensitivity, n = 1,160) | 1,160 | 1.01735 | +0.00010 | +0.00041 | +0.00023 | +0.00003 |
| Tennis Betfair LTP dev 2021–23 | 7,136 | 0.58215 | −0.00003 | −0.00005 | −0.00004 | −0.00005 |
| **Tennis sealed holdout 2024–25** | 5,066 | 0.5883 | +0.00001 [−0.0001, +0.0001] | +0.00001 [−0.0002, +0.0002] | +0.00000 | −0.00002 [−0.0001, +0.0001] |

All-books and opening-price sensitivities (football) give the same picture: every alternative is −0.0002 to −0.0005
better than multiplicative, and every CI includes zero.

## 3. Calibration (pooled outcome candidates: intercept / slope; slope > 1 = probabilities too compressed toward the middle)
| data | multiplicative | power | additive | Shin | odds-ratio |
|---|---|---|---|---|---|
| Football dev | 0.040 / **1.062** | −0.003 / **0.996** | 0.000 / 1.001 | 0.010 / 1.016 | 0.013 / 1.020 |
| Football validation | 0.057 / **1.088** | 0.012 / **1.019** | 0.016 / 1.024 | 0.026 / 1.041 | 0.029 / 1.045 |
| Football 2025/26 (536) | −0.033 / 0.949 | −0.073 / 0.889 | −0.070 / 0.894 | −0.061 / 0.908 | −0.059 / 0.911 |
| Tennis holdout | 0.045 / 0.986 | 0.045 / 0.983 | 0.045 / 0.984 | 0.045 / 0.982 | 0.045 / 0.984 |

## 4. High-probability region (football, top pick; predicted mean → actual [Wilson 95% CI])
| threshold | dev multiplicative | dev power | validation multiplicative | validation power |
|---|---|---|---|---|
| ≥70% | n = 331: 77.6 → 79.8 [75.1, 83.7] | n = 375: 79.0 → 78.1 | n = 232: 77.6 → 81.5 [76.0, 85.9] | n = 267: 78.9 → 82.4 |
| ≥80% | n = 117: 83.6 → 86.3 [78.9, 91.4] | n = 152: 85.3 → 86.2 | n = 69: 84.2 → **94.2** [86.0, 97.7] | n = 106: 85.0 → 88.7 [81.2, 93.4] |
| ≥85% | n = 36: 86.9 → 88.9 | n = 76: 88.0 → 86.8 | n = 24: 87.9 → 100 | n = 44: 89.0 → 95.5 |
| ≥90% | 1 | n = 15: 91.7 → 93.3 | 1 | n = 18: 91.7 → 100 |

2025/26 has only 5 (multiplicative) or 11 (power) matches at 80% or above, so the numbers there are uninformative.

## 5. Interpretation
- **Football:** multiplicative de-vig makes 1X2 probabilities slightly too flat. Calibration slope is 1.06–1.09 in both
  exposed periods, so favourites are understated and longshots overstated. Power and additive remove most of this
  (slope ≈ 1.00–1.02) and give strong favourites higher, better-matched probabilities in development and validation.
  **But the log-loss gain is tiny** (−0.0004 to −0.0009, never significant). On the least-exposed season (2025/26) the
  direction reverses: multiplicative is slightly better, and every method is overconfident (slope 0.89–0.95) that
  season. The 4.6-point favourite gap in the V2 audit is therefore partly real (a method effect of about 1–2 points at
  80%+) and partly sampling noise and season variation.
- **Tennis:** the method is irrelevant. Betfair last-traded prices carry almost no margin (median two-runner book sum
  1.0017), so all five methods agree to about 0.0001 log loss, including on the sealed holdout. The tennis market's
  strong calibration comes from the exchange price itself, not from de-vigging.

## 6. Decision gate: **C — differences too small / uncertain; retain the current (proportional) method.**
No method meets rule B (CI excluding zero in both development and validation), and the least-exposed confirmation
season reverses the sign. Recommended, not implemented: **log `power` alongside `multiplicative` prospectively** in
the future Prediction Board (zero cost, no decision change). It is the best-calibrated candidate on the exposed data,
and prospective data is the only fresh test left for football. Production is unchanged.
