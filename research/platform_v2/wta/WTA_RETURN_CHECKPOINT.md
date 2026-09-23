# WTA Match Winner — Research Result (Phase V2-2 Workstream B)

Order of evidence (git): `95f91cc` data audit + protocol + holdout spec + dataset → `dd2ecd0` holdout script →
holdout opened once (`HOLDOUT_RESULTS.json`; a second run printed `REFUSED`). WTA had never been analysed before, so
2024–25 was a genuinely untouched holdout.

## Data
TennisCourtLog WTA results (tour level; 2018–20 Elo warm-up only) + Fraser's Betfair archive. Evaluated: 10,352
matches with fresh two-sided Betfair prices at T−30 min (development 2021–23: 6,013; **holdout 2024–25: 4,339**).
Holdout surfaces: Hard 2,766 · Clay 1,029 · Grass 544. Levels: Slams 912 · 1000 1,336 · 500 843 · 250 1,168 ·
other 80. Retirements kept with the official winner; walkovers excluded.

## Sealed holdout 2024–25 (n = 4,339)
| estimator | log loss | Brier | AUC | top-pick acc. (expected) | cal. slope [95% CI] |
|---|---|---|---|---|---|
| **Betfair market (proportional)** | **0.5967** | **0.2063** | **0.738** | **66.8% (67.8%)** | **0.979 [0.900, 1.063]** |
| other de-vig methods | 0.5967 | 0.2063 | 0.738 | 66.8% | 0.975–0.978 |
| market + Elo stack | 0.5961 (Δ −0.0006 [−0.0018, +0.0006]) | 0.2060 | 0.739 | 66.9% | 0.969 |
| Global Elo (k = 32) | 0.6309 (Δ +0.034 [+0.027, +0.041]) | 0.2207 | 0.697 | 64.0% (67.1%) | **0.805 [0.725, 0.881]** |

**Best estimator: Betfair market.** The pre-registered calibration rule **passed**: the slope CI includes 1, and all
8 bands with n ≥ 200 fit their 99.5% interval. Elo is overconfident (≥80%: 86.1% predicted vs 81.3% won), and the
stack gives no gain (Elo weight −0.17).

## High-probability coverage (holdout, market top pick)
| threshold | n | share | mean P | expected wins | actual | actual rate [95% CI] |
|---|---|---|---|---|---|---|
| ≥60% | 2,967 | 68.4% | 73.5% | 2,182.1 | 2,167 | 73.0% [71.4, 74.6] |
| ≥65% | 2,263 | 52.2% | 77.0% | 1,741.8 | 1,750 | 77.3% [75.6, 79.0] |
| ≥70% | 1,704 | 39.3% | 80.1% | 1,365.0 | 1,364 | 80.0% [78.1, 81.9] |
| ≥75% | 1,191 | 27.4% | 83.4% | 993.6 | 991 | 83.2% [81.0, 85.2] |
| **≥80%** | **768** | **17.7%** | **86.9%** | **667.2** | **668** | **87.0% [84.4, 89.2]** |
| ≥85% | 430 | 9.9% | 90.4% | 388.8 | 393 | 91.4% [88.4, 93.7] |
| ≥90% | 217 | 5.0% | 93.5% | 202.8 | 203 | 93.5% [89.5, 96.1] |
| ≥95% | 59 | 1.4% | 96.6% | 57.0 | 59 | 100% [93.9, 100] |

Bands (holdout, predicted → actual): 50–54.9 52.7 → 50.3 · 55–59.9 57.6 → 55.8 · 60–64.9 62.5 → 59.2 · 65–69.9 67.4 →
69.1 · 70–74.9 72.4 → 72.7 · 75–79.9 77.2 → 76.4 · 80–84.9 82.4 → 81.4 · 85–89.9 87.3 → 89.2 · 90–94.9 92.3 → 91.1 ·
95%+ 96.6 → 100. The lower bands run slightly optimistic (−2 to −3 pp), within the multiplicity-aware CIs.
Development (2021–23, 6,013) agrees: ≥80% is 18.5% of matches, 86.4% predicted vs 88.5% won.

## Stability flags (reported, not acted on)
- By year, ≥80%: 2024 won 91.0% vs 86.8% predicted (n = 356); **2025 won 83.5% vs 86.9% (n = 412, CI 79.6–86.8,
  just excluding the prediction).** The years diverge in opposite directions; the pooled holdout is on target.
- By surface, ≥80%: Clay 90.5% (n = 200), Hard 87.3% (n = 473), **Grass 77.9% vs 86.4% (n = 95, CI 68.6–85.1).** A
  hypothesis for prospective monitoring only; not a filter.

## ATP vs WTA (sealed 2024–25 holdouts)
| | ATP | WTA |
|---|---|---|
| sample | 5,066 | 4,339 |
| log loss / Brier | 0.5883 / 0.2025 | 0.5967 / 0.2063 |
| calibration slope [CI] | 0.986 [0.918, 1.057] | 0.979 [0.900, 1.063] |
| top-pick accuracy | 68.2% | 66.8% |
| share ≥80% (pred → actual) | 19.8% (87.6 → 87.4) | 17.7% (86.9 → 87.0) |
| share ≥90% | 6.6% (94.0 → 93.4) | 5.0% (93.5 → 93.5) |
| year stability at ≥80% | 88.4 / 86.3 | 91.0 / 83.5 (wider swing) |
| surface consistency at ≥80% | 86.6–87.8 across surfaces | 77.9 (grass, n = 95) – 90.5 |
| tournament consistency | Slams strongest (90.1); 250s slightly hot (81.5 vs 84.5) | 250s 91.4, Slams 85.8, 1000s 86.8, 500s 85.8 |
| verdict | engine validated | **engine validated. WTA becomes the second tennis probability engine** |

ATP is slightly sharper and more stable, and WTA is slightly noisier. Both produce a large, well-calibrated
high-probability region.
