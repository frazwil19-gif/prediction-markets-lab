# NBA Moneyline — Result (Phase V2-3)

Order of evidence (git): `12561fc` data audit + protocol + code (no outcome statistics) → `abc2b87` development/validation
results + frozen `HOLDOUT_SPEC.json` (SHA-256 `fd22f616…3341`) + guarded script → holdout opened once
(`HOLDOUT_RESULTS.json`; a second run printed `REFUSED`).

## Development / validation (fitted on development only)
Elo selected from the grid: K = 15, home advantage 50 (the grid's lower edge, recorded, not extended), margin-of-victory
multiplier on, carry-over 0.75. Validation 2022-23 → 2023-24 (n = 2,632): market log loss 0.6048, slope 1.01; Elo
0.6300; data_logit 0.6265; stack 0.6049.

## Sealed holdout 2024-25 → 2025-26 (n = 2,629; home win rate 55.0%)
| estimator | log loss | Brier | AUC | top-pick acc. (expected) | cal. slope |
|---|---|---|---|---|---|
| **market (OddsPortal average closing, proportional)** | **0.5809** | **0.1990** | **0.754** | **68.8% (69.0%)** | **1.046 [0.956, 1.137]** |
| stack market + Elo | 0.5810 (Δ +0.0001 [−0.0004, +0.0006]) | 0.1990 | 0.754 | 68.9% | 1.067 |
| data_logit (Elo + schedule + form) | 0.6015 (Δ +0.021 [+0.013, +0.028]) | 0.2074 | 0.732 | 67.7% | 1.071 |
| Elo | 0.6082 (Δ +0.027 [+0.019, +0.035]) | 0.2103 | 0.723 | 66.8% | 1.068 [0.959, 1.182] |

**Prediction gate: A — validated probability-engine candidate.** The slope CI includes 1, and all 8 bands with
n ≥ 200 are inside their 99.5% intervals. The best estimator is the market. Unlike tennis, NBA Elo is *not*
overconfident (slope 1.07), but it is clearly less informative.

## High-probability coverage (holdout, market top pick)
| threshold | n | share | mean P | expected | actual | rate [95% CI] |
|---|---|---|---|---|---|---|
| ≥55% | 2,301 | 87.5% | 71.3% | 1,640.0 | 1,651 | 71.8% [69.9, 73.6] |
| ≥60% | 1,926 | 73.3% | 74.0% | 1,424.5 | 1,425 | 74.0% [72.0, 75.9] |
| ≥65% | 1,543 | 58.7% | 76.8% | 1,185.7 | 1,190 | 77.1% [75.0, 79.1] |
| ≥70% | 1,156 | 44.0% | 80.0% | 924.3 | 937 | 81.1% [78.7, 83.2] |
| ≥75% | 848 | 32.3% | 82.7% | 701.2 | 704 | 83.0% [80.3, 85.4] |
| **≥80%** | **550** | **20.9%** | **85.5%** | **470.4** | **481** | **87.5% [84.4, 90.0]** |
| ≥85% | 291 | 11.1% | 88.2% | 256.8 | 268 | 92.1% [88.4, 94.7] |
| ≥90% | 68 | 2.6% | 91.6% | 62.3 | 67 | 98.5% [92.1, 99.7] |
| ≥95% | 2 | 0.1% | 95.5% | 1.9 | 2 | — |

Bands (pred → actual): 50–54.9 52.7 → 48.2 · 55–59.9 57.5 → 60.3 · 60–64.9 62.4 → 61.4 · 65–69.9 67.5 → 65.4 ·
70–74.9 72.4 → 75.6 · 75–79.9 77.4 → 74.8 · 80–84.9 82.5 → 82.2 · 85–89.9 87.2 → 90.1 · 90–94.9 91.5 → 98.5
(n = 66) · 95%+ n = 2. At the very top the market *understated* favourites on the holdout (85%+: 88.2 → 92.1),
but in development it slightly *overstated* them (≥85%: 88.5 → 87.7). The direction is not stable, so this is a
monitoring item and no correction is applied.
Subgroups (≥80%): 2024-25 88.2% vs 85.3%, 2025-26 86.7% vs 85.8%; regular season 87.7% (n = 528); playoffs and
play-in 81.8% (n = 22). Away favourites ≥80% won 93.3% (n = 165) vs home favourites 84.9% (n = 385). The latter is a
hypothesis only (not pre-registered).

## Limitations
One averaged closing price (no book panel, no timestamps); no box scores; **no historical injuries or lineups**;
OddsPortal dates are offset +1 day (consistent); playoffs are a small sample. The validated number is a *closing*
price, so a live board must address timing (`NBA_LIVE_COMPATIBILITY.md`).
