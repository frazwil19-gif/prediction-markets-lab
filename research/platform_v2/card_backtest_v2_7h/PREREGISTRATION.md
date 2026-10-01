# V2-7H Historical Betting-Card Backtest: Pre-registration

**Written 2026-09-30, before any V2-7H result is computed.** The only numbers seen at this point are:
- the data inventory in `DATA_INVENTORY.json` (counts and coverage only);
- results published earlier in V2-6H, V2-6D and V2-7 Phase 1, which are cited as prior findings.

This study is research only. It does not touch production, the V2-7 prospective logger, bsv2-3, the frozen engines or any threshold.
Nothing is purchased, and no odds are manufactured. The only exception is §6, which uses **synthetic** prices that are labelled as
such and never used for profitability claims.

The prospective V2-7 stream is frozen and stays independent. Nothing from this study is written into it or used to change it.

## 0. Evidence labels (always used in reporting)
- **PROB** — probability validation only.
- **ASOF-FB** — football per-book prices at the pre-closing snapshot, with P from the same snapshot. This is the only
  decision-time price set we hold. Multi prices are **INDICATIVE MULTI PRICES**.
- **CLOSE-DIAG** — a closing-price diagnostic in which P and price come from the same closing snapshot:
  - football: consensus close vs a book's close;
  - tennis: Pinnacle-close de-vig (a reference estimator, not the frozen engine) vs the Bet365 close, after the V2-6D validity screen.
- **SYNTH** — synthetic prices, O = 1 / (p·(1+m)) for m ∈ {0, 0.05}. These describe risk and variance properties only. **They are never
  evidence of profit.**
- **Never used:** the frozen tennis T−30 P paired with any closing bookmaker price. This is the V2-6D misalignment.

## 1. Legs (unchanged frozen estimators; favourite side, P ≥ 0.50)
| sport | P (decision snapshot) | periods: development / holdout |
|---|---|---|
| ATP | Betfair LTP T−30, multiplicative | 2021–2023 / 2024–2025 |
| WTA | same | 2021–2023 / 2024–2025 |
| NBA | average closing, proportional | 2016-17 → 2023-24 (19-20 and 20-21 absent) / 2024-25, 2025-26 |
| Football 1X2 | consensus median, ≥ 3 books; closing for PROB, pre-closing for ASOF-FB | 2020/21–2023/24 / 2024/25, 2025/26 |

- A day is the UTC calendar date of the start time; for football and NBA, the match date.
- A group is the tennis tournament or the football competition.
- **Every holdout has already been opened by earlier phases.** Holdout results are labelled "previously exposed holdout", not
  pristine. Rule parameters are set on development data only.

## 2. Card universes
- **U1 (primary, calibration).** Within each sport-day, legs are ordered by sha256("v2-7h|" + event) and partitioned into
  consecutive disjoint k-tuples, k ∈ {1, 2, 3}.
  - Any card where one participant appears twice is dropped and counted (dependence rule: distinct events and distinct participants only).
  - There are no same-match parlays.
  - Each leg is used once per k, so cards within a k have no leg overlap.
- **U2 (secondary, overlap).** All within-day distinct-event combinations, k = 2 and 3. Calibration is computed exactly, in the large only,
  via elementary symmetric polynomials. This is used to show raw count, distinct leg sets and effective n.
- **Cross-sport (exploratory only).** For each date, one leg from each of two sports is paired in hash order. Calibration only.

## 3. Primary analyses (the only confirmatory claims)
- **P1. Joint calibration in the large** (realised − predicted) per sport × k ∈ {1, 2, 3} on U1:
  - reported for development and holdout separately;
  - 95% CI from a 2,000-resample bootstrap clustered by day, seed 20260930;
  - family: 4 sports × 3 k = 12 holdout tests, Holm-adjusted at α = 0.05.
  - **Decision rule.** "Calibrated" requires the Holm test not to reject **and** a CI half-width ≤ 2.0 pp (doubles) or ≤ 3.0 pp (trebles).
    If the test does not reject but the CI is wider, the result is **INCONCLUSIVE (imprecise)**.
- **P2. Independence of distinct events.**
  - Statistic: the mean within-day pairwise residual product E[(y_i − p_i)(y_j − p_j)]. Under calibration, this equals the error of
    P_joint = p_i·p_j for a double.
  - Reported per sport, for all pairs, same-group pairs and cross-group pairs, with a day-clustered CI. Holm across 4 sports.
  - Also reported: the daily-favourite-loss dispersion index (Phase 1 A2 reproduction).
- **P3. Equal-capital comparison** (§6) for the pre-declared strategy S1 (HIGH_P) under SYNTH m = 0 in each sport, and for S6
  (POS_EV) under ASOF-FB. Both use holdout and development separately. The primary stake is 1%.

Everything else is **exploratory** and labelled so.

## 4. Calibration reporting (all universes)
- **Metrics:** n cards, distinct leg sets, distinct events, distinct days; mean predicted and realised; bias with CI; CI half-width;
  minimum detectable deviation (2·SE_cluster); logistic recalibration slope and intercept (y ~ a + b·logit p, bootstrap CI) where
  n ≥ 200; Brier, climatology Brier and Brier skill; log loss; cluster effective n = ȳ(1−ȳ) / Var_boot(ȳ).
- **Card-probability bands:** < 0.50, 0.50–0.65, 0.65–0.80, ≥ 0.80. Also 5-pp bands, each flagged SPARSE when n < 200.
- **Leg thresholds (singles):** ≥ 0.70, 0.75, 0.80, 0.85, 0.90.
- **No band is called validated after the fact.** Only P1 cells are confirmatory.
- **Tennis contamination sensitivity:** exclude matches where |P_T−30 − P_PS-close| > 0.10, among matches linked to tennis-data.

## 5. Probability-error stress test (E)
- **Deterministic.** For k ∈ {1, 2, 3}, leg P ∈ {0.55, 0.60, 0.70, 0.80, 0.90} and per-leg shifts δ ∈ {±0.5, ±1, ±1.5, ±2, ±3, ±5} pp
  applied to all legs:
  - joint P, fair odds, and relative change;
  - EV at a price where the model EV is +2% and +5%;
  - Kelly fraction;
  - card-vs-singles log growth at 1% and 2%;
  - qualification status (EV > 0 / ≥ 2%).
- **Empirical.** On the ASOF-FB and CLOSE-DIAG POS_EV cards:
  - δ* = the uniform per-leg overestimate that makes card EV = 0;
  - the share of cards whose EV stays > 0 and ≥ 2% at each δ;
  - the δ at which the card's 1%-stake growth advantage over its singles disappears.
- **Observed-uncertainty version:** per-leg σ = development-period band calibration SE, as in cer-2. This is labelled separately from
  the deterministic grid. No confidence discount is invented.

## 6. Daily engine simulation, strategies and equal capital (F, G, H)
- **Selection is frozen before outcomes.** The selection function receives legs without outcome columns. A test checks that permuting
  outcomes cannot change any selection.
- One card per strategy per k per sport-day. All legs are distinct events and distinct participants. When prices exist, all legs are at
  the SAME book in the SAME snapshot.

| id | population | rule (ties broken by event hash) | prices |
|---|---|---|---|
| S1 | HIGH_P | top-k P among legs with P ≥ 0.70 | any |
| S2 | HIGH_P | top-k P among legs whose development-period singles band (5-pp) had \|bias\| ≤ 1 pp and CI half-width ≤ 1.5 pp; bands fixed on development data | any |
| S5 | HIGH_P | top-k lowest relative uncertainty σ_band/p (development-period band SE); expected to resemble S1, reported as such | any |
| S3 | POS_EV | per book, top-k legs by net EV among EV > 0; the book whose card has the highest EV is chosen | ASOF-FB, CLOSE-DIAG |
| S4 | POS_EV | per book, top-k by Kelly fraction EV/(O−1) among EV > 0; the book whose card has the highest 1%-stake expected log growth is chosen | ASOF-FB, CLOSE-DIAG |
| S6 | POS_EV | per book, top-k by P among EV > 0; the book with the highest P_joint is chosen (ties: EV) | ASOF-FB, CLOSE-DIAG |

- **HIGH_P and POS_EV results are never pooled.** Commission is 5% for BF, 0 otherwise. Only UK primary books are used:
  B365, WH, BW, BF.
- **Equal capital** (staking convention):
  - each day, total stake = s × the current bankroll, for s ∈ {0.5, 1, 2, 3, 5}%;
  - (A) k singles at s/k each versus (B) the k-fold card at s;
  - bankroll starts at 1 and compounds daily;
  - legs of a day are settled together, with no rebalancing within the day;
  - void or missing results do not occur in these datasets (legs require outcomes).
- **Metrics per strategy × k × price scenario × stake × period:**
  - n days, win probability (card won / singles day P&L > 0), whole-stake loss share;
  - mean model EV, realised ROI per unit stake (with CI), realised mean log return per day (day-bootstrap CI), model-expected log growth;
  - final bankroll, volatility (SD of daily log return), maximum drawdown, longest losing run;
  - the exact DP model probability of a losing run ≥ 5 / 8 / 10 for the card sequence;
  - severe impairment: P(bankroll < 0.5 at any time), from 1,000 day-bootstrap re-orderings.
- **Pre-declared comparison:** for each pair (singles vs card), the mean daily log-return difference with a day-bootstrap CI. A structure
  "dominates" only where that CI excludes 0.
- **Margin compounding (J):** for all favourite same-book cards at ASOF-FB and CLOSE-DIAG (not only POS_EV), the mean card net EV by k,
  and the card's implied overround versus consensus fair.

## 7. Overlap (K)
For U2, and for strategy outputs, report:
- raw card count, distinct leg sets, distinct events, distinct days;
- event reuse (cards per event), participant reuse, bookmaker reuse;
- model-implied Kish effective n (card correlations under leg independence) on 60 randomly chosen days per sport (seed 20260930),
  reported as the ratio n_eff / raw.

## 8. Profitability rule (I)
Profitability language ("realised ROI", "bankroll growth") is used **only** for ASOF-FB. Even there, it is qualified as:
untimestamped snapshot, single-book outliers possible, stake availability unverified, and multi prices INDICATIVE.
- CLOSE-DIAG results are "closing-price diagnostic".
- SYNTH results are risk descriptions.

A positive realised result counts as evidence only if its day-bootstrap 95% CI excludes 0 **in both development and holdout**.

## 9. Outputs
- Code: `scripts/v2_7h_card_backtest.py` and `src/prediction_markets_lab/research/card_backtest.py`.
- Tests: `tests_research/test_v2_7h_card_backtest.py`.
- Numbers: `RESULTS.json` plus CSV summaries.
- Report: `REPORT.md`, covering sections 1–20 of the directive and the separate classifications (N).
- Any analysis added after results are seen is labelled **POST-HOC EXPLORATORY** with its date.
