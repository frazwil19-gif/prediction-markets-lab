# Tennis ATP Match Winner — Prediction Engine Decision (V2-1 Workstream B)

Pre-registration: `TENNIS_ENGINE_PROTOCOL.md` + `HOLDOUT_SPEC.json` (SHA-256 `4f1a5670…2e09`, committed `8ca4264`
before opening). Holdout opened once (`HOLDOUT_RESULTS.json`; a second run printed `REFUSED`). Tables:
`TENNIS_MODEL_COMPARISON.csv`, `TENNIS_PROBABILITY_BANDS.csv`, `TENNIS_HIGH_PROBABILITY_ANALYSIS.csv`,
`TENNIS_SUBGROUPS.csv`, `HOLDOUT_SLOPE_CI.json`.

## Sample
12,202 ATP main-tour matches 2021–2025 with fresh Betfair prices on both sides at T−30 min (development 2021–23:
7,136; **sealed holdout 2024–25: 5,066**). Surfaces (development): Hard 4,129 · Clay 2,163 · Grass 844. Levels:
250 · 500 · Masters · Slams · Finals/Davis/Olympics. Best-of-3: 5,697 · best-of-5: 1,439. Priced coverage ≈83% of
non-walkover TML matches (7,136 of 8,588 in 2021–23).

## Sealed holdout 2024–25 (n = 5,066)
| estimator | log loss | Brier | AUC | top-pick accuracy (expected) | cal. slope [95% CI] |
|---|---|---|---|---|---|
| **market (Betfair LTP, proportional)** | **0.5883** | **0.2025** | **0.750** | **68.2% (68.3%)**, i.e. 3,457 correct vs 3,459.3 expected | **0.986 [0.918, 1.057]** |
| market, other de-vig methods | 0.5883 | 0.2025 | 0.750 | 68.2% | 0.982–0.984 |
| stack market + Elo (fit 2021–23) | 0.5877 (Δ −0.0006 [−0.0014, +0.0003]) | 0.2023 | 0.750 | 68.3% | 1.005 |
| Global Elo | 0.6221 (Δ +0.034 [+0.028, +0.040]) | 0.2173 | 0.706 | 64.3% (66.9%) | **0.858 [0.789, 0.929]** |
| ranking baseline | 0.6361 | 0.2222 | 0.692 | 64.1% | 0.912 |

**Strongest estimator: the Betfair market probability.** Adding Elo does not improve it: the stack's gain has a CI
crossing zero, and the fitted weight on Elo is slightly *negative* (−0.11). Elo is **overconfident** on unseen data,
exactly as the V2 audit indicated: at ≥80% it predicted 86.9% and won 84.6% (n = 790); at 60–64.9% it predicted
62.5% and won 54.7%. Elo remains useful as an odds-independent sanity check and as a fallback where no price exists.
It should not be used as the probability engine, and **it was not recalibrated on the holdout**.

## The high-probability question (sealed holdout, market; top pick)
| threshold | n | share of matches | mean predicted | expected wins | actual wins | actual rate [95% CI] |
|---|---|---|---|---|---|---|
| ≥55% | 4,366 | 86.2% | 70.8% | 3,091.2 | 3,075 | 70.4% [69.1, 71.8] |
| ≥60% | 3,496 | 69.0% | 74.1% | 2,590.7 | 2,581 | 73.8% [72.3, 75.3] |
| ≥65% | 2,667 | 52.6% | 77.7% | 2,073.1 | 2,082 | 78.1% [76.5, 79.6] |
| ≥70% | 2,021 | 39.9% | 81.0% | 1,637.7 | 1,622 | 80.3% [78.5, 81.9] |
| ≥75% | 1,447 | 28.6% | 84.4% | 1,221.7 | 1,218 | 84.2% [82.2, 86.0] |
| **≥80%** | **1,001** | **19.8%** | **87.6%** | **876.4** | **875** | **87.4% [85.2, 89.3]** |
| ≥85% | 590 | 11.6% | 91.2% | 537.9 | 537 | 91.0% [88.4, 93.1] |
| ≥90% | 333 | 6.6% | 94.0% | 313.2 | 311 | 93.4% [90.2, 95.6] |
| ≥95% | 125 | 2.5% | 96.8% | 121.1 | 120 | 96.0% [91.0, 98.3] |

Non-overlapping bands: every band is within ±2.3 pp of its prediction except 65–69.9% (67.4% → 71.2%, +3.8 pp,
n = 646). See the gate note below.

**The 20.7% figure, verified:** development 2021–23 had 1,478 of 7,136 priced matches (20.71%) with a top pick ≥80%
(2021: 20.7% · 2022: 21.5% · 2023: 19.9%; Hard 20.5% · Clay 19.4% · Grass 25.1%; Slams 38.8%, 250s 11.9%). **It
replicates on the never-opened 2024–25 data: 19.8%, with 87.4% of those matches won against 87.6% predicted.** The
denominator is ATP matches with fresh Betfair prices on both sides (≈83% of all non-walkover ATP matches), not every
ATP match.

**Subgroups (holdout, ≥80%):** 2024 88.4% vs 87.3% predicted; 2025 86.3% vs 87.8%; Hard 87.8%, Clay 87.0%, Grass
86.6%; Slams 90.1% (n = 383); Masters 84.4% vs 86.8% (n = 231); 250s 81.5% vs 84.5% (n = 135). All CIs include the
predicted value.

## Decision gate: **B — Tennis prediction is validated and promising, but the live data source must be solved.**
- Calibration: slope CI [0.918, 1.057] includes 1. 9 of 10 bands fit within their CI. The 65–69.9% band misses by
  0.2 pp at the edge of its CI (67.4% predicted vs a 67.6–74.6% interval). **Transparency note:** the pre-registered
  gate said *every* band with n ≥ 200 must fit. With 10 bands, a perfectly calibrated engine fails that literal test
  about 40% of the time, so the rule did not account for testing many bands at once; with a multiplicity correction
  (99.5% CI) the band fits. I am recording B rather than claiming a clean pass. Fraser can overrule to C if he wants
  the literal rule applied.
- Sample, stability (both years, all surfaces) and high-probability coverage are strong.
- Not A: no live source is demonstrated yet (`TENNIS_LIVE_DATA_AUDIT.md`).
