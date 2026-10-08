# Historical Decision Replay / Bet-Characteristics Audit — PRE-REGISTRATION

Date: 2026-10-01. Committed before any financial result of this study is computed.
Directive: "BOUNDED RESEARCH TASK — HISTORICAL DECISION REPLAY / BET CHARACTERISTICS AUDIT".

This task is read-only research. Production is frozen at master `f4720b4`. The following are not changed:
* engines, estimators and holdouts;
* bsv2-4 gates and pcard-1 grades;
* paper and league states, credits and staking.

No paper selection is written. No result of this study changes any production rule.

## 1. Data (all already held; nothing purchased)
| Engine | Source | P | Prices | Outcomes |
|---|---|---|---|---|
| ATP / WTA match winner | `data/interim/v2_{tennis,wta}_market_dataset.csv` (Betfair BASIC LTP, frozen engine `p_a_market_multiplicative`) | frozen engine, T−30 LTP | tennis-data.co.uk closing: B365 (UK book), PS, BFE (2025 only). SHA-256 per V2-6D | tennis-data winner, linked by the V2-6D matcher |
| Football 1X2 E0/E1/SC0 | football-data.co.uk per-book (`cycle_001_*_full`, `h_fb2_002_sealed_oos_2025_26_*`), 2020/21–2025/26 | median-of-books de-vig, ≥ 3 books, same snapshot (the live estimator's construction) | per book at two snapshots: `opening` (pre-closing collection) and `closing` | FTR |
| Football 1X2 N1/D1/F1 + others | xgabora Matches.csv (V2-18 pin) | Bet365 single-book de-vig (V2-18) | Bet365 + MaxH/D/A aggregate | FTR |
| NBA moneyline | wippa (OddsPortal) average closing ML, 2016-17 → 2025-26 (19-20/20-21 absent) | de-vig of the average (= frozen engine source) | average closing only | score |

## 2. Price-evidence classes (fixed here)
* **A — EXECUTABLE-LIKE:** a timestamped, executable quote at decision time. **None of our historical data qualifies.**
* **B — SAME-TIME PROXY:** football E0/E1/SC0 `opening` snapshot. P and price come from the same pre-closing
  collection. Executable UK books are B365, WH, BW, and BF with 5% commission. There is no exact timestamp, and
  collection is typically 1–3 days before kick-off, so bsv2's ≤ 24h horizon gate is **not evaluable**.
  **This is the primary financial evidence.**
* **C — CLOSING PROXY:**
  * football E0/E1/SC0 `closing` snapshot (same construction);
  * tennis BFE-close de-vig P vs B365 close (2025, exchange-derived like the frozen engine, aligned);
  * tennis PS-close de-vig P vs B365 close (aligned; a reference estimator, **not** the frozen engine).

  These are closing-efficiency evidence, not decision-time execution.
* **D — NOT REPLAYABLE:**
  * tennis frozen T−30 P vs B365 close (timing-misaligned; V2-6D proved outcome leakage, spurious +21%);
  * NBA (only an average closing price exists, so EV = −margin by construction);
  * xgabora Max columns (a cross-book aggregate, not an identifiable executable quote);
  * Bet365-vs-own-de-vig (EV = −margin by construction).

  Class D rows enter **no** financial conclusion.

## 3. Frozen rules replayed
* **bsv2-4 PAPER_BET:** P ≥ 0.50, net EV ≥ 2%, odds ≥ 1.33. One selection per (event, selection) at the best-net-EV
  executable book.
  * The horizon and price-age gates are not evaluable (no timestamps).
  * The spread gate is not evaluable (no back/lay).

  All three are documented as limitations.
* **pcard-1 grade:**
  * A = EV(P − 1·σ) > 0;
  * B = PAPER_BET otherwise;
  * A+ is impossible, because no engine has the evidence state;
  * C = WATCH (not staked).
* **σ:**
  * football: the production `football_sigma` band SE;
  * tennis: the production `calibration_se` band SE only. The live σ also adds the exchange half-width, which does not
    exist historically, so the σ used here is a lower bound.

## 4. Analyses (all pre-specified)
1. **Probability replay per engine:**
   * metrics: N, mean P, win rate, expected vs actual wins, Brier, log loss, calibration slope/intercept;
   * season-by-season;
   * P bands <60, 60–65, 65–70, 70–75, 75–80, 80–85, 85–90, 90+ (favourite side);
   * longest run of failed P ≥ 0.70 predictions in chronological order.
2. **Decision replay (classes B, C):** a reconstructed bet table (CSV, research only) with every field the directive
   lists. Qualifiers and non-qualifiers are kept separate.
3. **Characteristics:** by sport, league, P band, odds band (<1.20, 1.20–1.32, 1.33–1.49, 1.50–1.74, 1.75–1.99, 2.00+),
   EV band (<0, 0–2, 2–4, 4–6, 6–10, 10%+), uncertainty-adjusted EV sign, season, evidence class.
   * Metrics: N, win rate, expected win rate, calibration error, average odds, expected EV, ROI with 2,000-draw
     bootstrap 95% CI (seed 20261001), max drawdown, longest losing streak.
4. **Threshold sensitivity (DIAGNOSTIC ONLY):**
   * grid: odds floor {1.20, 1.25, 1.30, 1.33, 1.40, 1.50} × EV {0, 1, 2, 3, 5%} × P {0.60 … 0.90} × σ multiplier
     {0, 0.5, 1, 1.645};
   * per cell: N, ROI, CI and per-season sign.
   * Multiple-testing note: 6 × 5 × 7 × 4 = 840 cells. With this many cells, at least one "significant" cell is
     expected by chance. **No cell is selected or recommended.** The reading is limited to monotonicity, broad
     stability and adequate N.
5. **Counterfactual rejects:** ROI and calibration of P ≥ 0.50 favourites rejected *only* by the odds floor, *only* by
   the EV floor, *only* by grade-A uncertainty, versus accepted.
6. **Bankroll:**
   * bankrolls £30 / £50 / £100;
   * policies: 0.5%, 1%, 2% fraction, and ⅛ Kelly (cap 2%);
   * minimum stake £0.10 (bookmaker) / £1 (exchange);
   * per-bet cap 5% and daily cap 10% (bsv2 block);
   * chronological replay of class B qualifiers (primary) and class C (secondary).
   * Stress test (not a policy): flat £3 / £5, with the percentage-of-bankroll implied.
   * Resampling: 10,000 chronological-order Monte Carlo paths with outcomes drawn from P (model-based, "if calibrated"),
     plus a bootstrap of realised P&L. Ruin = bankroll below the minimum stake.
7. **Live-readiness answers A–I.** If the evidence warrants a money-eligibility review, the output is a
   *SMALL-STAKES MONEY-ELIGIBILITY REVIEW CANDIDATE* — never an activation.

## 5. Pre-stated expectations (from V2-6H / V2-6D, so the reader can judge surprise)
* Football at bsv2-1 qualified **8** closing bets in 6 seasons, with ROI indistinguishable from 0.
* Tennis aligned closing value was 0.2–1 per 100 favourites, with ROI ≈ 0.
* Backing all favourites lost 2.6–4.1%.

The expectation is therefore **small N, no detectable edge, strong calibration**. A different result will be checked
for leakage before it is reported.

Outputs: `research/platform_v2/decision_replay/` (REPORT.md, RESULTS.json, bet tables, grids).
Script: `scripts/decision_replay.py`.
