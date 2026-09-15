# Tennis Cycle 1 -- 2025 Sealed Holdout Report

*Generated 2026-09-15T22:14:14.923919+00:00*

**This is the ONE-TIME evaluation described in TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md.** Run exactly once, against the frozen specification, with the verdict below produced mechanically by `classify_holdout_result` -- not read off by eye. No retrying, threshold-loosening, or silent model change followed seeing these numbers.

## 0. Seal and scope

- Frozen model: Global Elo, k_factor=32.0 (re-derived from training-only data as a consistency check -- matches the frozen value of 32.0: True)
- Training/calibration seasons: [2021, 2022, 2023]
- Validation season (already reported elsewhere): 2024
- Sealed holdout season (evaluated here, for the first time): 2025
- Holdout coverage: N=2921 total matches in 2025; Global Elo scores 2921 (full coverage -- Elo scores every match); ranking baseline scores 2859 (usable-ranking matches only); common sample for the primary comparison: N=2859.

## 1. Global Elo -- 2025 metrics (full coverage)

| n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |
|---|---|---|---|---|---|---|
| 2921 | 0.6325 | 0.2216 | 0.6925 | 0.0556 | 0.8130 | 0.0329 |

## 2. Ranking baseline -- 2025 metrics (usable-ranking matches only)

| n | Log loss | Brier | AUC | Calib. intercept | Calib. slope | ECE |
|---|---|---|---|---|---|---|
| 2859 | 0.6399 | 0.2234 | 0.6897 | 0.0664 | 0.8627 | 0.0215 |

## 3. Primary comparison (common sample, paired bootstrap)

delta (Global Elo log loss - ranking baseline log loss) = -0.0088, 95% CI [-0.0202, 0.0016] (n=2859, 2000 resamples, seed=20260915)

Negative delta means Global Elo has the lower (better) log loss. A CI excluding zero means the gap is unlikely to be sampling noise -- this is still a predictive-performance statement only, not a betting-edge claim (see section 6).

## 4. Mechanical verdict

# VERDICT: PARTIAL

Reason: primary-comparison CI includes zero: any favourable point estimate is not statistically conclusive at this sample size

This verdict was produced by `classify_holdout_result` applied to the numbers in sections 1-3 above, per the frozen, mutually exclusive rule in TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md section 9. It was not chosen by reading the numbers and picking the closest-sounding label.

## 5. Subgroup diagnostics (Global Elo, full 2025 coverage) -- DIAGNOSTIC ONLY

These were pre-registered as reporting-only in the freeze (section 6). Per the freeze's process (section 11), an interesting pattern here is recorded as a FUTURE HYPOTHESIS -- NOT VALIDATED and does NOT change the verdict above.

### By surface

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| Hard | 1845 | 0.6314 | 0.2213 | 0.5119 | 0.5095 |
| Clay | 781 | 0.6400 | 0.2252 | 0.5075 | 0.5442 |
| Grass | 295 | 0.6191 | 0.2139 | 0.4852 | 0.5119 |

### By tourney_level

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| 250 | 826 | 0.6627 | 0.2344 | 0.5158 | 0.5278 |
| M | 769 | 0.6561 | 0.2315 | 0.5093 | 0.5085 |
| 500 | 507 | 0.6125 | 0.2130 | 0.5073 | 0.5227 |
| G | 505 | 0.5543 | 0.1883 | 0.4961 | 0.5228 |
| D | 250 | 0.6770 | 0.2412 | 0.4967 | 0.4800 |
| A | 49 | 0.6105 | 0.2111 | 0.5173 | 0.6122 |
| F | 15 | 0.3962 | 0.1228 | 0.5974 | 0.6667 |

### By best_of

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| 3 | 2401 | 0.6489 | 0.2286 | 0.5112 | 0.5177 |
| 5 | 520 | 0.5567 | 0.1893 | 0.4934 | 0.5250 |

### By rank_gap (usable-ranking matches only)

| Level | n | Log loss | Brier | Mean predicted P(a) | Observed freq |
|---|---|---|---|---|---|
| (-0.001, 0.268] | 572 | 0.6781 | 0.2426 | 0.5033 | 0.5315 |
| (0.268, 0.584] | 572 | 0.6865 | 0.2467 | 0.5084 | 0.5105 |
| (0.584, 0.969] | 571 | 0.6591 | 0.2334 | 0.5192 | 0.5324 |
| (0.969, 1.481] | 572 | 0.5949 | 0.2032 | 0.5251 | 0.5385 |
| (1.481, 5.857] | 572 | 0.5371 | 0.1789 | 0.4847 | 0.4895 |

## 6. What this result does and does not establish

This holdout tests only whether Global Elo's PREDICTIVE performance generalises out of sample to a period never touched during model selection. It does NOT establish a betting edge, positive EV, market outperformance, CLV, or tradeability, whatever the verdict above is -- that requires historical market prices (Workstream B) and a full EV/CLV/liquidity/cost analysis on top of predictive skill.

## 7. Next step, per the freeze's process

Do not modify the model. Report why the evidence is inconclusive and identify the cleanest genuinely untouched additional validation route without using 2025 for development.
