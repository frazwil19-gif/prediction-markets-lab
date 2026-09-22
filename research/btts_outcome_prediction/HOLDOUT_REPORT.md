# Phase 5 — BTTS Sealed Holdout Report (2024/25, opened once)

Protocol: `HOLDOUT_PROTOCOL.json`, SHA-256 `d574fee1…790a`, committed in `e8bb4d0` **before** opening. Train
2020/21–2023/24, evaluate 2024/25. n = 1,158 (common set), base rate 53.2% YES. A second opening attempt was
refused by the script guard.

| model | log loss | Brier | AUC | accuracy | cal. intercept / slope | ECE |
|---|---|---|---|---|---|---|
| naive | 0.6934 | 0.2501 | 0.500 | 46.8% | — | 3.4% |
| data_logit | 0.7007 | 0.2537 | **0.496** | 50.4% | 0.13 / **−0.14** | 4.2% |
| poisson_goal | 0.6893 | 0.2480 | 0.562 | 55.0% | 0.15 / 0.70 | 4.6% |
| **market_implied_poisson (selected)** | 0.6857 | 0.2463 | 0.563 | **55.9%** | 0.06 / **0.93** | 1.7% |
| market_implied_poisson_recal | 0.6856 | 0.2462 | 0.563 | 55.4% | 0.06 / 0.87 | 1.6% |
| market_implied_plus_data | 0.6970 | 0.2517 | 0.532 | 53.9% | 0.11 / 0.26 | 4.5% |
| market_implied_poisson_opening | 0.6853 | 0.2461 | 0.561 | 55.2% | 0.04 / 0.99 | 1.5% |

Bootstrap vs selected: naive worse, +0.0077 [0.0006, 0.0145]. data_logit worse, +0.0151 [0.0078, 0.0222].
market+data worse, +0.0114 [0.0064, 0.0167]. poisson_goal +0.0036 [−0.0042, 0.0120], recalibrated −0.0000
[−0.0006, 0.0005] and opening −0.0003 [−0.0028, 0.0022] are **statistically indistinguishable** from the selected model.

## Verdict
- **The selected estimator is confirmed on unseen data.** It beats naive, data-only and market+data with CIs excluding zero,
  and it stays well calibrated (slope 0.93, ECE 1.7%).
- **The data-only model has no holdout skill** (AUC 0.496, negative calibration slope). The historical-stats BTTS model
  is REJECTED.
- The opening-price variant is as good as closing on the holdout. The estimator is therefore deployable from
  scan-time prices.
- Honesty caveat, carried from Phases 2–4: 2024/25 raw data was used by earlier 1X2/OU2.5 cycles. It is blind for
  BTTS-specific relationships only.
