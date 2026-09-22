# Phase 5 — Football BTTS Outcome Prediction + Probability-Engine Consolidation: Return Checkpoint

2026-09-22. Production untouched. Every number below was independently re-derived from `predictions_*.csv` + raw goals.

1. **Matches:** 5,800.
2. **Seasons:** 2020/21–2024/25. 2025/26 is not in the feature pipeline (a known shared gap).
3. **Competitions:** E0 (1,900), E1 (2,760), SC0 (1,140).
4. **BTTS YES base rate:** 50.5%. By season: 45.6 / 49.1 / 49.7 / 55.0 / 53.2%.
5. **BTTS NO base rate:** 49.5%.
6. **Pre-match features:** 19 Gate-1b fundamentals, 10 new shrunk rolling scoring / clean-sheet / BTTS-rate features,
   failed-to-score rates, Poisson λ, market-implied λ, history depth, season stage, promoted flag, Elo gap and
   volatility. `DATASET_SCHEMA.md`.
7. **Historical BTTS odds:** none. Zero columns across all 18 raw files.
8. **Live BTTS:** available. Odds API `btts`, per-event endpoint, 1 credit/event, 9 UK books including Betfair Exchange (live probe).
9. **Leakage audit:** PASS. Features are computed per date before that date's results are added; train-before-eval is
   asserted; the holdout stage is hash-gated and single-open. `LEAKAGE_AUDIT.md`, 33 new tests.
10. **Split:** discovery 2020/21–2022/23 → dev walk-forward on 2021/22–2023/24 (validation = 2023/24) → sealed holdout 2024/25.
11. **Strongest YES/NO differences:** market-implied P(BTTS) (d 0.15, AUC 0.54), weaker team's market λ (d 0.13), then
    away shots, SOT and goals-for (d 0.07–0.09). **All small: BTTS barely separates pre-match.**
12. **Feature stability:** 22 STABLE, 11 WEAKENED, 11 SIGN_FLIP of 44. `FEATURE_STABILITY.csv`.
13. **Models tested:** naive, data_logit, poisson_goal, market_implied_poisson, its recalibrated version,
    market_implied + data, and an opening-price sensitivity.
14. **Market-only (true BTTS prices):** not available historically, so not fabricated. The market-derived proxy
    (market_implied_poisson) is the best model.
15. **Data-only:** dev log loss 0.6964 (worse than naive's 0.6956); holdout 0.7007, AUC 0.496. **REJECTED.**
16. **Goal/Poisson:** dev 0.7024 (overconfident, slope 0.26); holdout 0.6893 (tied with the selected model, CI crosses 0).
17. **Combined (market-implied + data):** dev 0.6931; holdout 0.6970. Worse than market-implied alone (CI excludes 0).
18. **Best supported estimator:** **market_implied_poisson** (pre-registered mechanical selection, confirmed on the holdout).
19. **Brier:** 0.2468 dev / 0.2463 holdout.
20. **Log loss:** 0.6867 dev / 0.6857 holdout (naive 0.6956 / 0.6934).
21. **AUC:** 0.560 dev / 0.563 holdout.
22. **Accuracy (top pick):** 53.7% dev / 55.9% holdout.
23. **Calibration:** intercept/slope 0.04/1.06 dev, 0.06/0.93 holdout; ECE 1.2% / 1.7%.
24. **Probability bands:** within about ±4.5 pp in every band with n ≥ 100 (both sides). Predictions span only 0.31–0.72. `ERROR_ANALYSIS.md`.
25. **≥60%:** dev 238 at 62.8% predicted → 66.8% actual; holdout 117 at 63.2% → **63.2%** [54.2, 71.4].
26. **≥65%:** dev 38 → 81.6%; holdout 26 → 61.5% [42.5, 77.6]. Too thin to trust.
27. **≥70%:** 5 dev / 4 holdout. Uninformative.
28. **≥75%:** zero predictions.
29. **≥80%:** zero predictions.
30. **High-probability error analysis:** no characteristic separated errors. The pre-registered "exclude E1" filter
    **failed** on the holdout. An early-season weakness showed on the holdout only (47%, n = 17) and is a hypothesis, not a filter.
31. **Sealed holdout:** opened once, selected estimator confirmed. `HOLDOUT_REPORT.md`.
32. **BTTS probability prediction:** **VALIDATED as calibrated but LOW-CONFIDENCE.** The probabilities are trustworthy,
    but the market rarely offers a strong BTTS view.
33. **Historical betting overlay:** BLOCKED_BY_HISTORICAL_DATA.
34. **Betting result:** not honestly possible, so none reported.
35. **Probability vs betting architecture:** formalised in `PROBABILITY_ENGINE_ARCHITECTURE.md` §1–2.
36. **Consensus-price findings (1X2 closing, 17,400 candidates):** including the priced book makes V1's EV
    *conservative* (−0.66 pp vs leave-one-out), not inflated. Claimed EV of +2.6 to +3.4% did not show up as
    realised return (−1.9% to +1.4%, all CIs cross 0). Backing every best price returns −2.9% [−5.2, −0.5]. A sharp
    reference (Pinnacle probability vs other books' price) is the only construction pointing positive, and it is
    unproven. Recommendations R1–R4 are design only.
37. **Live validation requirements:** per-scan raw per-bookmaker quotes, event id, kickoff, line, estimator
    id/version, three EV references, decision, closing snapshot, result, CLV. BTTS fetched only for money-window
    fixtures behind a credit guard (+120–170 credits/month). Architecture §4.
38. **Research Atlas:** v1.1. BTTS is VALIDATED (outcome) / BLOCKED (replay). A "best available probability estimator"
    table was added, and new fields were added to every market (JSON + MD).
39. **Next market recommendation:** **Football Asian Handicap, Stage A.** The market-implied λ machinery built here
    extends directly to AH lines (and team totals / correct score), live AH is a cheap featured market (`spreads`),
    and thin historical AH prices exist. Tennis only with genuinely new information. **Operational priority comes
    before the next market, though** (see 44).
40. **Tests:** 1,015 / 1,015 passed (982 + 33 new).
41. **Files:** new: `src/prediction_markets_lab/research/btts_outcome_prediction.py`,
    `scripts/run_phase5_btts_outcome_prediction.py`, `scripts/run_phase5_consensus_price_independence_analysis.py`,
    `tests/unit/test_btts_outcome_prediction.py`, `research/btts_outcome_prediction/*`. Changed:
    `research/multi_market_expansion/RESEARCH_ATLAS.{md,json}`. Derived and uncommitted:
    `data/processed/football/phase5_btts_canonical_dataset.csv`.
42. **Commits:** `e8bb4d0` (pre-registration + dev + frozen protocol, before the holdout), then the Phase 5
    completion commit (see `git log`).
43. **Production impact:** none. No change to `decisions/`, `config/`, the scan, workflows, ledgers, thresholds or staking.
44. **Recommended next action:** approve and implement **live raw-quote preservation** (Phase 3 recommendation, still
    unbuilt). Include the three EV references (R1) and BTTS quotes for money-window fixtures only, as a
    **paper-only** market. Every live day not logged is lost evidence, and the betting stage, not the probability
    stage, is now the binding constraint. Start AH Stage A after that.
