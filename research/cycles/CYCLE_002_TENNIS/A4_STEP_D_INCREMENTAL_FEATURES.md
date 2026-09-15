# Cycle 2 Tennis -- Workstream A4 Step D: Incremental Feature Models

*Generated 2026-09-15T21:10:51.530817+00:00*

**PREDICTIVE PERFORMANCE ONLY -- NO BETTING EDGE ESTABLISHED.** No price/odds data of any kind is used. A4 baselines A-C are FROZEN (see A4_BASELINE_RESULTS.md) and not modified here; Global Elo is the accepted primary odds-independent benchmark every feature below is tested against.

- Training/calibration seasons: [2021, 2022, 2023]
- Validation season: 2024
- Sealed holdout season: 2025 -- **never loaded by this script**
- Global Elo k_factor (recalibrated identically to A4): 32.0
- Multiple-testing policy: Bonferroni correction across 3 pre-registered families -- each CI below is reported at the 98.3333% level (per-comparison alpha = 0.05/3), not a naive 95%, so that the FAMILY of three tests holds at 95% overall.
- Promotion rule: a feature is promoted only if its bootstrap CI for (Elo+feature log loss - Elo-only log loss) lies ENTIRELY below zero at the corrected level above. A correctly-signed coefficient or a favourable raw win-rate difference is not sufficient.

## Results by family

### 1. Recent form beyond Global Elo

Feature column(s): `rolling_win_pct_diff_a_minus_b` -- coverage n_train=7409, n_validation=2844

- Elo-only log loss: 0.6226
- Elo+feature log loss: 0.6226
- Delta (augmented - baseline): 0.0000, Bonferroni-corrected 98.33% CI [-0.0002, 0.0003]
- Fitted coefficient(s) on new feature(s): {'rolling_win_pct_diff_a_minus_b': 0.066827}
- **Verdict: NOT PROMOTED (null or negative result)**

Stability (2024 first vs second half):

| Half | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| first_half_2024 | 1422 | 0.6128 | 0.6128 | 0.0000 |
| second_half_2024 | 1422 | 0.6324 | 0.6324 | 0.0001 |

Stability by surface:

| Surface | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| Hard | 1645 | 0.6216 | 0.6217 | 0.0001 |
| Clay | 896 | 0.6266 | 0.6265 | -0.0001 |
| Grass | 303 | 0.6161 | 0.6164 | 0.0003 |

Stability by best-of format:

| Best of | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| 3 | 2345 | 0.6393 | 0.6393 | -0.0000 |
| 5 | 499 | 0.5441 | 0.5444 | 0.0004 |

### 2. Surface-specific form beyond Global Elo

Feature column(s): `rolling_win_pct_surface_diff_a_minus_b` -- coverage n_train=6439, n_validation=2639

- Elo-only log loss: 0.6213
- Elo+feature log loss: 0.6210
- Delta (augmented - baseline): -0.0003, Bonferroni-corrected 98.33% CI [-0.0014, 0.0009]
- Fitted coefficient(s) on new feature(s): {'rolling_win_pct_surface_diff_a_minus_b': 0.290495}
- **Verdict: NOT PROMOTED (null or negative result)**

Stability (2024 first vs second half):

| Half | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| second_half_2024 | 1320 | 0.6314 | 0.6306 | -0.0008 |
| first_half_2024 | 1319 | 0.6112 | 0.6115 | 0.0002 |

Stability by surface:

| Surface | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| Hard | 1582 | 0.6220 | 0.6216 | -0.0004 |
| Clay | 822 | 0.6219 | 0.6217 | -0.0002 |
| Grass | 235 | 0.6147 | 0.6149 | 0.0002 |

Stability by best-of format:

| Best of | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| 3 | 2181 | 0.6377 | 0.6376 | -0.0002 |
| 5 | 458 | 0.5430 | 0.5422 | -0.0008 |

### 3. Congestion/rest beyond Global Elo

Feature column(s): `rest_diff_a_minus_b, congestion_diff_a_minus_b` -- coverage n_train=8066, n_validation=2975

- Elo-only log loss: 0.6236
- Elo+feature log loss: 0.6227
- Delta (augmented - baseline): -0.0009, Bonferroni-corrected 98.33% CI [-0.0052, 0.0038]
- Fitted coefficient(s) on new feature(s): {'rest_diff_a_minus_b': -0.002085, 'congestion_diff_a_minus_b': 0.041662}
- **Verdict: NOT PROMOTED (null or negative result)**

Stability (2024 first vs second half):

| Half | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| second_half_2024 | 1488 | 0.6326 | 0.6316 | -0.0011 |
| first_half_2024 | 1487 | 0.6146 | 0.6138 | -0.0008 |

Stability by surface:

| Surface | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| Hard | 1712 | 0.6227 | 0.6217 | -0.0010 |
| Clay | 946 | 0.6284 | 0.6280 | -0.0004 |
| Grass | 317 | 0.6140 | 0.6123 | -0.0018 |

Stability by best-of format:

| Best of | n | Baseline log loss | Augmented log loss | Delta |
|---|---|---|---|---|
| 3 | 2460 | 0.6401 | 0.6390 | -0.0011 |
| 5 | 515 | 0.5445 | 0.5447 | 0.0002 |

## Summary and next candidate model

No feature family was promoted at the Bonferroni-corrected level. This is reported as a clean null result, per the standing 'a clean null result is acceptable' directive -- it is not reframed as a near-miss or retried with a looser threshold. Global Elo alone remains the cycle's odds-independent candidate model pending any newly pre-registered feature.

Calibration (raw vs. a simple forward-safe recalibration) has deliberately not been investigated yet -- per the operator's instruction, that follows model selection, not before it, to avoid tuning calibration to chase a better headline log loss.

2025 remains completely sealed and unexamined by this script.
