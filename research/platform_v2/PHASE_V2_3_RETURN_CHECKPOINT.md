# Phase V2-3 — NBA Moneyline Outcome Prediction: Return Checkpoint (2026-09-24)

**Before anything else: a production incident, found and fixed this phase.** Since 22 Sep every scheduled workflow
(daily_scan, settlement_and_performance, tennis_prediction_board) has failed at "Run the test suite first". Two
Backtest-Phase-1 tests read gitignored `data/processed/football/*.csv`, which doesn't exist on a clean GitHub
checkout, so no real scans, settlements or tennis boards have run since then. The fix is `c4d7779` (those two tests
skip when the data is absent; a clean clone passes: 1,096 passed, 8 skipped). **It restarts everything once
pushed.** Lesson recorded: always run the suite on a clean clone before handing over. The placeholder
`weekly_report.yml`/`data_validation.yml` "failures" are pre-existing zero-job workflow files (noise, not failures of work).

1. **Data decision: B** — ready using free new data.
2. **Sources investigated:** repository (none), Betfair historical basketball (site blocked; manual download only),
   wippa-nba-data (GitHub), SBR scraper archive (GitHub), NBA Stats / Basketball-Reference / FiveThirtyEight / Kaggle / SBR site (all blocked by the allowlist).
3. **Selected:** wippa-nba-data (primary: results + OddsPortal average closing moneyline); SBR archive (Elo warm-up 2011–16 and a cross-check).
4. **Manual download:** none. 5. **Cost:** £0.
6. **Seasons:** 2016-17 → 2025-26 (plus 2011-12 → 2015-16 warm-up).
7. **Total games:** 12,825. 8. **Regular season:** 11,955. 9. **Playoffs:** 834 (+36 play-in).
10. **Missingness:** 0 odds missing. Pre-season/All-Star and junk rows excluded. Source cross-check: winners agree 99.8%, implied probabilities correlate 0.997.
11. **Historical odds:** one average closing price per side (no panel, no timestamps).
12. **Betfair historical:** not used (unreachable). An optional later exchange cross-check.
13. **Sports features:** scores and schedule only (no box scores reachable).
14. **Injuries/rosters:** unavailable historically. Explicit limitation.
15. **Leakage audit:** PASS (`nba/NBA_LEAKAGE_AUDIT.md`, 10 tests).
16. **Chronology:** development 2016-17 → 2021-22 · validation 2022-23 → 2023-24 · sealed holdout 2024-25 → 2025-26.
17–19. **Samples:** development 7,564 · validation 2,632 · holdout 2,629.
20. **Features:** Elo logit, rest difference, back-to-back flags, 7-day load, rolling-10 point differential and win %, season point differential, season game number, neutral flag.
21. **Strongest winner/loser differences:** market d 0.84, Elo 0.70, season point differential 0.65, rolling-10 point differential 0.58; away back-to-back 0.11.
22. **Stability:** strength features 6/6 seasons; home back-to-back unstable (3/6).
23. **Models:** market, Elo (grid-selected), regularised data logit, market+Elo stack.
24. **Best estimator:** market (OddsPortal average closing, proportional de-vig).
25–29. **Holdout:** accuracy **68.8%** (expected 69.0%) · Brier **0.1990** · log loss **0.5809** · AUC **0.754** · slope **1.046 [0.956, 1.137]**, 8/8 bands pass.
30–37. **Thresholds (share → pred/actual):** ≥60 73.3% 74.0/74.0 · ≥65 58.7% 76.8/77.1 · ≥70 44.0% 80.0/81.1 · ≥75 32.3% 82.7/83.0 ·
    **≥80 20.9% 85.5/87.5** · ≥85 11.1% 88.2/92.1 · ≥90 2.6% 91.6/98.5 · ≥95 0.1% (n = 2).
38. **Band table:** `nba/NBA_PROBABILITY_BANDS.csv` (summarised in `nba/NBA_RETURN_CHECKPOINT.md`).
39–41. **Cross-sport (sealed holdouts unless noted; share of events whose top pick ≥80%, predicted → actual):**

| engine | n | log loss | slope | ≥80% share | ≥80% pred → actual | ≥90% share |
|---|---|---|---|---|---|---|
| ATP Match Winner | 5,066 | 0.588 | 0.99 | 19.8% | 87.6 → 87.4 | 6.6% |
| WTA Match Winner | 4,339 | 0.597 | 0.98 | 17.7% | 86.9 → 87.0 | 5.0% |
| **NBA Moneyline** | **2,629** | **0.581** | **1.05** | **20.9%** | **85.5 → 87.5** | **2.6%** |
| Football 1X2 (descriptive, all seasons) | 5,776 | 3-way | 1.06–1.09 | 3.3% | 83.7 → 88.3 | ~0% |
| Football O/U 2.5 | 4,640 | 0.676 | ~1.0 | 0.1% | — | 0% |
| Football BTTS | 1,158 | 0.686 | 0.93 | 0% | — | 0% |
NBA matches tennis for 80%+ coverage and calibration, with fewer 90%+ outcomes and fewer events per day (≈8 games vs
tens of tennis matches), and it adds a genuinely independent sport.
42. **Context limitations:** no injuries or lineups. The validated closing price embeds late news that a morning scan won't see.
43. **Live NBA:** Odds API `basketball_nba` h2h, UK region, 1 credit per scan; season starts late October.
44. **Prospective-board readiness:** engine validated; adapter not built (it reuses the tennis pattern). Credit headroom is tight.
45. **Prediction decision: A** — a validated probability-engine candidate (not money-eligible; next is a prospective paper board).
46. **ATP prospective sample:** 0 predictions (no covered ATP event was active on the only manual run; the workflow has been blocked by the CI incident).
47. **WTA prospective sample:** 6 predictions, 0 settled. Too early to say anything.
48. **Atlas:** v1.5 (NBA added and validated; tennis prospective status; cross-sport table).
49. **Next family:** **Football Double Chance** (derived from the already-validated 1X2 consensus). Descriptively,
    on already-exposed data, the best DC selection is ≥80% in **32.6%** of matches (86.4% predicted vs 86.4% won,
    n = 1,885) and ≥90% in 8.4% (92.8 vs 94.5). No new data needed. It still needs its own pre-registered
    chronological test and a check of live DC price availability. Alternatives: NHL/MLB moneyline (SBR MLB/NHL
    2011–21 archives are reachable; recent seasons not yet sourced; lower high-P potential).
50. **Tests:** 1,104 local (clean clone: 1,096 passed + 8 skipped, because real-data tests skip).
51. **Files:** `research/platform_v2/nba/*`, `src/prediction_markets_lab/nba/*`, `tests/unit/test_nba_research.py`, `scripts/run_v2_3_nba_study.py`, `data/raw/basketball/SHA256SUMS`, Atlas, this checkpoint; CI fix in 2 test files.
52. **Commits:** `12561fc` (protocol) → `abc2b87` (dev results + frozen spec) → holdout opened → `c4d7779` (CI fix) → final V2-3 commit.
53. **Production impact:** the CI fix restores production. No production logic changed. 0 API credits.
54. **Needs Fraser:** (a) **push now** (restores all scheduled workflows), then optionally run daily_scan and
    tennis_prediction_board once by hand; (b) approve an NBA prospective paper board before the season (late
    October), including a credit-budget decision since football + tennis + NBA ≈ 480 of 500 in busy months;
    (c) approve Football Double Chance as the next research family.
