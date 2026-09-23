# Phase V2-1 — Probability Calibration + Tennis High-Probability Engine: Return Checkpoint (2026-09-23)

Research only. **No production change, no threshold change, no API credits spent on odds** (only the free `/sports`
list), **no data bought.** Headline numbers were independently recomputed from the raw dataset with plain numpy.

**Workstream A: margin removal**
1. **Current method:** per-book proportional (q/B), then the mean across books (`probability/market_pipeline.py`).
2. **Alternatives tested:** additive, power, odds-ratio (Cheung), Shin. None has parameters fitted to outcomes.
3. **Football sample:** B365/BW/PS closing panel: dev 3,477 · validation 1,884 · 2025/26 confirmation 536 (plus a
   1,160-match B365+BW sensitivity). All-books panel: 5,800 closing and 5,798 opening.
4. **Tennis sample:** 12,202 ATP matches (dev 7,136, holdout 5,066).
5. **Chronology:** football dev 2020/21–22/23 → validation 23/24–24/25 → confirmation 25/26. Tennis dev 2021–23 → sealed 2024–25.
6. **Already exposed:** all football 2020/21–2024/25; football 2025/26 only as aggregate Gate 1 log loss; tennis 2021–23 market-vs-outcome.
7. **Genuinely untouched:** **tennis 2024–25 market-vs-outcome** (Workstream B never opened it), used as a sealed
   holdout and opened once. Football had none; 2025/26 is "least exposed" and declared as such.
8. **Calibration by method:** football slope (dev / val): multiplicative 1.06 / 1.09; power 1.00 / 1.02; additive
   1.00 / 1.02; Shin 1.02 / 1.04; odds-ratio 1.02 / 1.04. 2025/26: all 0.89–0.95. Tennis holdout: all 0.98–0.99.
9. **Brier:** football dev 0.5927 (multiplicative) vs 0.5925 (all others); tennis holdout 0.2025 for all methods.
10. **Log loss:** football dev 0.99280 vs 0.99241–0.99250; val 0.97205 vs 0.97119–0.97145; 2025/26 1.02624 vs
    1.02642–1.02685; tennis holdout 0.5883 for all. No difference has a CI excluding zero.
11. **High-probability calibration:** football ≥80%, proportional dev 83.6 → 86.3% (n = 117), val 84.2 → 94.2%
    (n = 69); power dev 85.3 → 86.2% (n = 152), val 85.0 → 88.7% (n = 106). Tennis: identical across methods.
12. **Best supported transformation:** none clearly. Power is the best-calibrated candidate on exposed football data.
13. **Calibration gate: C.** Differences are too small and uncertain; retain proportional. Recommendation: log power
    alongside it prospectively.

**Workstream B: tennis**
14. **Historical sample:** 12,202 ATP matches with fresh two-sided Betfair prices at T−30 min, 2021–2025.
15. **Seasons:** 2021 2,240 · 2022 2,415 · 2023 2,481 · 2024 2,620 · 2025 2,446.
16. **Surfaces (dev):** Hard 4,129 · Clay 2,163 · Grass 844. Holdout: Hard 2,978 · Clay 1,496 · Grass 592.
17. **Tours/levels:** ATP only. Slams, Masters, 500s, 250s, Finals/Davis Cup/Olympics. WTA not yet built.
18. **Favourite accuracy:** market top pick 67.9% dev and **68.2% holdout** (expected 68.3%).
19. **Strongest estimator:** Betfair market LTP (proportional).
20. **Brier:** 0.2025 (holdout).
21. **Log loss:** 0.5883 (holdout). Elo 0.6221, ranking 0.6361.
22. **Calibration:** intercept 0.045, slope **0.986 [0.918, 1.057]**. 9 of 10 bands within CI.
23–30. **Counts at each threshold (holdout, of 5,066):** ≥60% 3,496 · ≥65% 2,667 · ≥70% 2,021 · ≥75% 1,447 ·
    **≥80% 1,001** · ≥85% 590 · ≥90% 333 · ≥95% 125.
31. **Realised vs predicted:** ≥60% 73.8 vs 74.1 · ≥65% 78.1 vs 77.7 · ≥70% 80.3 vs 81.0 · ≥75% 84.2 vs 84.4 ·
    **≥80% 87.4 vs 87.6** · ≥85% 91.0 vs 91.2 · ≥90% 93.4 vs 94.0 · ≥95% 96.0 vs 96.8.
32. **Confidence intervals:** ≥80% [85.2, 89.3] · ≥90% [90.2, 95.6] · ≥95% [91.0, 98.3]. Full tables in the CSVs.
33. **20.7% verified:** exactly 1,478 of 7,136 (20.71%) in dev. Holdout replication: 1,001 of 5,066 (**19.8%**).
    The denominator is priced matches (≈83% of non-walkover ATP matches).
34. **Elo:** overconfident on unseen data (slope 0.858 [0.789, 0.929]). At ≥80% it predicted 86.9% and won 84.6%
    (n = 790); at 60–64.9% it predicted 62.5% and won 54.7%. Not recalibrated on the holdout. The earlier training-fit
    recalibration (≈ identity) had already failed to help in 2024.
35. **Market high-probability behaviour:** calibrated through 95%+. Strongest in Slams (≥80%: 90.1% won, n = 383).
    250s run slightly hot (81.5% vs 84.5%, CI includes the prediction).
36. **Combination:** market + Elo stack Δ log loss −0.0006 [−0.0014, +0.0003], Elo weight −0.11. **No improvement.**
37. **ATP/WTA:** ATP validated. WTA has free data available (TML WTA CSVs, and WTA markets already inside `data.tar`); not built.
38. **Live sources:** The Odds API (tournament keys: Slams, Masters, some 500s, incl. `betfair_ex_uk`); Betfair
    Delayed key (all tennis, 1–180 s delay); paid aggregators (not evaluated).
39. **Free/paid:** Odds API free tier (in use) · Betfair Delayed free (terms described as dev/testing) · Betfair Live
    one-off fee (£299 or £499 cited; unverified).
40. **Recommended live source:** Stage 1 is The Odds API for covered tournaments (the Slams and Masters hold 61% of
    ≥80% predictions). Stage 2 is the Betfair Delayed key after Fraser confirms the terms and a CI login test.
41. **Prospectively ready?** The probability engine is ready; the feed is not.
42. **Tennis gate: B.** Validated and promising; live source must be solved. This includes a transparent note that
    the literal "every band" rule is missed by 0.2 pp in one of 10 bands.
43. **Prediction Board:** hierarchical rule: exclude invalid → PREDICTION_VALID/PAPER_ONLY → rank by P → break ties by
    uncertainty, band support, kickoff. The engine's unseen-data hit rate is shown beside every P. No odds, EV or
    stakes on the board. `DAILY_OUTPUTS_SPEC.md`.
44. **Multi implications:** three tiers (PREDICTION_VALID / SINGLE_ELIGIBLE / MULTI_ELIGIBLE). Standalone odds may sit
    below the payout floor for multi legs. Value is reported but is not a leg criterion (operator §31). Tennis is the
    leg pool: 11.6% of matches ≥85%. Same-day cross-match independence is untested.
45. **Next family:** **WTA Match Winner.** Zero data cost (the archive is already on the Mac, TML is free), a strong
    high-probability prior, and it shares the ATP live-source solution. Basketball stays second (no data in repo).
46. **Atlas:** v1.3. ATP validated (gate B), WTA entry added, de-vig study status recorded, per-market calibration method status.
47. **Tests:** **1,077 / 1,077** passing (1,015 + 62 new).
48. **Files:** `research/margin_removal_methods.py`, `research/probability_reliability.py` (+ tests),
    `scripts/run_v2_1_margin_removal_study.py`, `scripts/build_v2_tennis_market_dataset.py`,
    `scripts/run_v2_1_tennis_holdout.py`, `research/platform_v2/calibration/*`, `research/platform_v2/tennis/*`,
    `data/interim/v2_tennis_market_dataset.csv` (force-added: the rebuild inputs live in an ephemeral VM), Atlas,
    `DAILY_OUTPUTS_SPEC.md`, `MULTI_ENGINE_SPEC.md`, `CROSS_MARKET_RESEARCH_STATUS.md`.
49. **Commits:** `8ca4264` (protocols, holdout spec, dev study; **before** the holdout was opened) plus the completion commit (see `git log`).
50. **Production impact:** none.
51. **Recommended next action (needs Fraser):** decide the tennis live source. (a) Approve Stage 1: a research-only
    Odds API tennis adapter that writes a **paper Prediction Board** for covered tournaments at about 2 credits per
    tournament per scan. (b) Check whether you are comfortable using a Betfair Delayed key as a standing personal feed,
    or would rather ask Betfair. (c) Approve WTA Stage A on the data already on your Mac. (a) and (c) can run in parallel.
