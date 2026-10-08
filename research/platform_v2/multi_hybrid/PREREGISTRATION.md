# Probability-first bet construction + multi + hybrid theory test — PRE-REGISTRATION

Date: 2026-10-02 (UTC). This document is committed before any new analysis is run.
Directive: "NEXT RESEARCH DIRECTIVE — PROBABILITY-FIRST BET CONSTRUCTION + MULTI/HYBRID THEORY TEST".

This is research only. Production (master) is untouched:
* no threshold, paper, multi, staking or model change;
* no data purchase.

## 0. What is already known (reused, not re-run)
* **V2-7H** (`card_backtest_v2_7h/REPORT.md`):
  * separate-event multis are calibrated, with no Holm rejection;
  * the independence error is about ±0.4 pp (tennis/NBA) and ±0.9 pp (football);
  * margin compounds about (1+EV)^k;
  * at realistic margin, singles beat cards in 100/100 SYNTH cells and 15/15 CLOSE-DIAG HIGH_P cells;
  * high-P doubles (≥ 0.80) and trebles (≥ 0.65) were **effectively untested** (U1 n = 10–55 per cell);
  * football favourites are under-confident at high P.
* **Probability model research:**
  * Football Gate 1 / Phase 2: market better than fundamentals, Elo+Poisson and hybrids; every Δ CI excludes 0.
  * Tennis ATP/WTA: market better than Elo/ranking; the stack is ≤ 0.0006 log loss better (holdout).
  * NBA: market ≈ stack, both better than Elo/data-logit.
* **Decision replay** (2026-10-01): high-P favourites at UK prices have EV ≈ −4% (the margin).

The new work below covers only the gaps.

## 1. Questions
* **Q1 (CONFIRMATORY):** Are cohort-restricted separate-event doubles/trebles calibrated? This fills V2-7H's
  high-P gap.
* **Q2 (CONFIRMATORY):** Does combining high-P legs improve the expected economics versus the same legs as singles,
  at equal capital, at same-book prices?
* **Q3 (EXPLORATORY):** Leg count 1–5: payout, EV, variance, whole-stake loss and drawdown.
* **Q4 (EXPLORATORY):** High-P legs rejected by the 1.33 singles floor: as singles and as double legs.
* **Q5 (CONFIRMATORY, new data slice):** Football, 13 additional leagues (xgabora). Is a hybrid of market + ClubElo
  better than the market in probability quality on an untouched chronological test?
* **Q6 (EXPLORATORY):** Disagreement regions: which estimator is calibrated there?
* **Q7:** Would hybrid probabilities change multi economics? This is answered only if Q5 shows an improvement;
  otherwise it is marked DATA_REQUIRED or moot.

## 2. Datasets (all held; hashes as in the decision replay / V2-18)

| Sport | P (probability analyses) | Prices (financial) | Outcomes |
|---|---|---|---|
| Tennis ATP/WTA 2021–25 | frozen engine (Betfair LTP T−30) | B365 close, with P = Pinnacle-close de-vig (aligned; reference estimator, not the frozen engine) | tennis-data / interim |
| Football E0/E1/SC0 2020/21–2025/26 | median-of-books consensus (≥ 3 books) at the pre-closing snapshot | same snapshot, per book: B365, WH, BW | FTR |
| NBA 2016–26 | de-vig of the OddsPortal average | none (not replayable) | score |
| Football, 13 other leagues 2020/21–2025/26 (xgabora) | B365 de-vig; ClubElo pre-match (`HomeElo` / `AwayElo`) | none used financially | FTR |

**Leakage check for Elo (pre-specified).**
* ClubElo is a daily, as-of-date rating. If Elo-only AUC exceeds the market AUC on the same rows, Elo is treated as
  leaked and Q5 is reported as DATA_INVALID.
* No post-match statistic is used. Form, shots and goals are not used: their pre-match construction from xgabora
  needs a rolling build that is out of scope for this bounded test.

## 3. Construction rules
* **Legs:** the favourite side (P ≥ 0.50) of each event. The directive's cohorts are P ≥ 0.60, 0.70, 0.75, 0.80,
  0.85, 0.90. They are analysis bands, not thresholds.
* **Decision set:** one calendar day per sport. No cross-sport cards.
* **Disjoint cards:**
  * within each day and cohort, legs are ordered by an outcome-free hash of the event id and chunked into
    non-overlapping groups of k = 2, 3, 4, 5;
  * remainders are dropped;
  * each event appears in at most one card per k;
  * distinct events and distinct participants (tennis: no player twice).
* **Top-N per day:**
  * the N highest-P legs of the day (N = 2, 3, 4, 5), as one card;
  * ties are broken by the hash.
* **Dependence class:**
  * different events on the same day in the same sport are LOW_EXPECTED_DEPENDENCE (V2-7H P2 supports this);
  * same-event combinations are excluded;
  * there are no UNKNOWN or DEPENDENT combinations in this study.

## 4. Price-evidence classes (the directive's B1)
* **A:** executable same-book combined odds. None exist.
* **B:** same-book product proxy. All legs come from the same book in the same snapshot.
  * Football pre-closing B365, WH and BW: each book is replayed separately, and results are reported per book and
    pooled.
  * Tennis B365 close with Pinnacle-fair P: **closing / reference**, labelled B-close.
* **C:** cross-book product (best price per leg). Reported only to show the inflation; never used for conclusions.
* **D:** NBA and the 13 xgabora leagues. Probability only.

## 5. Metrics
* **Calibration (Q1):**
  * N cards, unique events, unique days, ESS = N disjoint cards;
  * mean joint P, hit rate, Brier, log loss;
  * day-cluster bootstrap 95% CI of bias (2,000 resamples, seed 20261002);
  * bands of joint P: <0.5, 0.5–0.6, 0.6–0.7, 0.7–0.8, 0.8+.
  * **Confirmatory test:** cohort ≥ 0.80 doubles and ≥ 0.70 trebles, per sport. Bias CI must contain 0. Holm across
    the confirmatory cells.
* **Economics (Q2):**
  * per card: joint P, fair odds, product odds, margin = 1 − (product odds × joint P)^(−1) … reported as
    EV = P_joint·odds − 1;
  * EV at P−1σ per leg (σ = production band SE);
  * P(lose whole stake) = 1 − P_joint;
  * per-unit variance.
  * **Equal capital:** one unit on the k-fold versus 1/k unit on each of its k legs as singles, same book.
  * **Confirmatory test:** mean (card − singles) return difference per unit, day-cluster CI. Cohorts ≥ 0.80 and
    ≥ 0.85 doubles, football B-prices.
* **Margin compounding:** mean leg margin, mean card margin and fair versus offered product odds, by cohort × k.
* **Bankroll (Q3, EXPLORATORY):**
  * £30 / £50 / £100 at 0.5%, 1% and 2% of the current bankroll, chronological, one card per day per structure;
  * minimum stake £0.10;
  * stress test (not a policy): flat £3 / £5;
  * report final value, maximum drawdown, longest losing run and resampled P(drawdown ≥ 20%).
* **Hybrid (Q5):**
  * train 2020/21–2022/23; validation 2023/24, used only to choose between "stack" and "market", never refitted
    on test;
  * test 2024/25–2025/26, untouched by any earlier research of *this* comparison. V2-18 used the same rows for
    market calibration only;
  * stack = multinomial logistic on [log market odds-ratio features, Elo difference, home indicator], fitted on
    train;
  * report log loss, Brier, slope/intercept, AUC, and match-bootstrap ΔLL CI versus market, per league and pooled;
  * Holm across 13 leagues.

## 6. Multiple comparisons and stopping
* Confirmatory cells are listed above. Everything else is EXPLORATORY: 6 cohorts × 4 k × 4 sports × 3 books, plus
  bankroll cells.
* No threshold, leg count or cohort is recommended from exploratory cells.
* There is no stopping rule beyond completing the pre-specified tables, and no re-run with altered rules.
* **If a result looks too good** (|card EV| better than the singles by more than 5 pp with CI excluding 0, or a
  hybrid ΔLL better than −0.01), a leakage audit runs before it is reported.

## 7. Two scoreboards (always separate)
* **Prediction:** per leg, P versus outcome, plus Brier and log loss.
* **Betting:** per card, joint P, odds, stake, W/L, P&L, ROI and drawdown. A card with 4 of 5 legs correct is reported
  as "4 correct / 1 incorrect" and also as a lost card.

Outputs: `research/platform_v2/multi_hybrid/` (REPORT.md, RESULTS.json, tables).
Script: `scripts/multi_hybrid_research.py`.
