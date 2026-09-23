# Cross-Market Research Status (probability-first view, 2026-09-23)

All numbers were computed by `scripts/run_v2_cross_market_probability_audit.py` from **existing frozen outputs**. No model
was refit and no threshold was chosen. "Top pick" = the most likely outcome of each event. Full tables:
`CROSS_MARKET_PROBABILITY_BANDS.csv`, `CROSS_MARKET_HIGH_PROBABILITY.csv`.

## Engines
| engine | estimator | events | top-pick accuracy (mean P) | holdout status | uncertainty available | context |
|---|---|---|---|---|---|---|
| Football 1X2 | proportional de-vigged closing consensus | 5,776 | 52.1% (50.9%) | yes (Gate 1, 2024/25) | band Wilson CI | none |
| Football O/U 2.5 | thin-panel market (2–3 books) | 4,640 | 57.2% (57.0%) | yes (Gate 1b) | band CI | none |
| Football BTTS | market-implied Poisson | 4,595 | 54.3% (54.3%) | yes (Phase 5, opened once) | band CI | none |
| Tennis Winner | Betfair price 30 min before start (2021–23) | 7,136 | **68.0% (68.8%)** | **no. Descriptive only; this is Workstream B discovery data** | band CI | none |
| Tennis Winner | Global Elo (sealed 2025 holdout) | 2,921 | 63.5% (66.2%) | yes, verdict PARTIAL | band CI | none |

## High-probability coverage (top pick ≥ threshold: share of events → predicted vs actual [95% CI])
| engine | ≥70% | ≥75% | ≥80% | ≥90% |
|---|---|---|---|---|
| Football 1X2 | 10.4% → 77.5 vs **79.9** [76.5, 82.9] | 6.4% → 80.6 vs **84.0** | 3.3% → 83.7 vs **88.3** [82.9, 92.1] | 3 events |
| Football O/U 2.5 | 2.8% → 73.0 vs 74.2 | 0.4% (n = 20) | 4 events | 0 |
| Football BTTS | 0.2% (n = 9) | 0 | 0 | 0 |
| **Tennis, Betfair market** | **41.9%** → 80.9 vs 81.5 | **30.2%** → 84.2 vs 84.8 | **20.7%** → 87.2 vs 88.0 [86.2, 89.5] | **6.4%** → 93.8 vs **96.3** |
| Tennis, Global Elo (holdout) | 34.3% → 79.8 vs **75.3** | 22.9% → 83.4 vs **78.8** | 14.3% → 86.9 vs **82.3** | 3.6% → 93.9 vs 91.5 |

## What this says
1. **Tennis is the natural home of high-probability predictions.** One market in five is priced ≥80%, and the Betfair
   market's bands from 65% to 90% are calibrated within ±0.6 pp on thousands of matches. Football goal markets almost
   never produce strong predictions; football 1X2 does only for heavy favourites.
2. **Market prices under-state strong favourites** (football 1X2 and tennis at 90%+). This fits proportional
   de-vigging's known favourite–longshot bias. It is the most important, cheapest probability research item: it
   touches every engine and every multi leg. Descriptive and in-sample, so it must be tested chronologically.
3. **Model-based tennis Elo is overconfident at the top** (86.9% priced vs 82.3% won). The market estimator is better, in
   line with every football result.
4. Uncertainty is band-level only. No engine yet produces a per-candidate interval, and no engine has any current-context input.

## Per-market record (Atlas fields; the Atlas JSON remains canonical)
| market | outcome status | best estimator | historical n | holdout | betting replay | live | multi eligibility | next |
|---|---|---|---|---|---|---|---|---|
| Football 1X2 | EXHAUSTED (model discovery) | consensus (de-vig method open) | 5,776 | done | done (zero qualified) | LIVE | candidate legs (favourites) after de-vig study | margin-removal study |
| Football O/U 2.5 | VALIDATED | consensus | 4,640 | done | BLOCKED (thin panel) | LIVE | rarely strong | none now |
| Football BTTS | VALIDATED, low-confidence | market-implied Poisson | 4,595 | done | BLOCKED (no odds) | available, not wired | effectively never (≤0.2% ≥70%) | paper-only wiring |
| Football AH | UNEXPLORED | — | ~5,800 (thin prices) | — | BLOCKED | available (spreads) | — | later |
| Tennis Winner (ATP) | **VALIDATED (V2-1 sealed 2024–25 holdout)** | Betfair market LTP | 12,202 (dev 7,136 + holdout 5,066) | done, slope 0.986; ≥80% 87.6 → 87.4% | open | partial via Odds API; Betfair Delayed key pending terms | strongest leg pool | live-source solution |


**Update 2026-09-23 (V2-1):** the tennis market engine was validated on the never-opened 2024–25 holdout. See `tennis/TENNIS_PREDICTION_ENGINE_DECISION.md`. De-vig study verdict C (retain proportional): `calibration/V2_1_CALIBRATION_REPORT.md`.
