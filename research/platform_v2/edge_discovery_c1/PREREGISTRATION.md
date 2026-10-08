# Edge Source Discovery — Cycle 1 — Analysis Plan (PRE-REGISTRATION)

Date: 2026-10-02. Committed before any analysis in this cycle.
Directive: "EDGE SOURCE DISCOVERY CYCLE 1 — DATA-FIRST PROFITABILITY DISCOVERY".

This is research only. Production is frozen at master `f4720b4`, and nothing is purchased.

## Nature of this cycle
This cycle is **DISCOVERY**: describe behaviour, then form hypotheses. Every discovered effect is labelled
DISCOVERY. Nothing found here is a validated edge.

Data-mining controls (fixed now):
1. **Discovery / confirmation split, fixed in advance:**

   | Dataset | Discovery | Confirmation |
   |---|---|---|
   | Football per-book | 2020/21–2022/23 | 2023/24–2025/26 |
   | Tennis | 2021–2023 | 2024–2025 |
   | NBA | seasons ≤ 2021-22 | ≥ 2022-23 |
   | xgabora leagues | 2020/21–2022/23 | 2023/24–2025/26 |

   A behaviour is a CANDIDATE only if its sign and approximate size repeat in the confirmation period. Confirmation
   here is still **not** validation: both periods have been seen by earlier research phases.
2. **False discovery:** every atlas test gets a p-value, either a two-sided bootstrap for ROI ≠ 0 or a
   calibration-bias test. Benjamini–Hochberg is applied at q = 0.10 across all atlas tests, and the count of tests is
   reported.
3. **No threshold search for maximum ROI.** Bins are descriptive and fixed below. Continuous relationships are
   estimated by linear or logistic fits.
4. **Price-evidence classes A–D** follow the decision replay. Class D never supports a financial statement.
5. **Leakage rules:**
   * a probability and a price are paired only from the same snapshot;
   * features are pre-match only (rank, points, ClubElo snapshot, Form5 = points from the previous 5 matches);
   * no post-match statistic is used.

## Analyses (fixed list)
* **F, football per-book** (E0 / E1 / SC0, 2020/21–2025/26, snapshots `opening` = pre-closing and `closing`):
  * books: B365, WH, BW, BF, 1XB (UK / UK-facing) and PS (Pinnacle, the sharp reference);
  * **F1:** margins per book × snapshot;
  * **F2:** price dispersion (best / median / worst UK price per outcome);
  * **F3:** three fair references: PS de-vig (proportional), LOO median-of-books consensus, and the production
    consensus;
  * **F4:** calibration of each reference by outcome type (H / D / A), P band, league and season, at both snapshots;
  * **F5:** EV continuum. Per UK book and per outcome (all three sides, all P), EV vs PS-fair and vs consensus.
    Realised ROI versus EV by fixed bands (<0, 0–1, 1–2, 2–4, 4–6, 6–10, 10%+) plus a linear fit of return on EV;
  * **F6:** timing. Opening → closing movement of PS-fair and of the soft books. Diagnostic: how often an opening
    soft price beats the closing PS-fair (opening CLV), and its relation to return;
  * **F7:** favourites vs underdogs vs draws: ROI at the best UK price and at PS, by P band;
  * **F8:** book-vs-consensus disagreement (price dispersion) versus PS-vs-consensus disagreement.
* **X, xgabora 13 leagues + E0 / E1 / SC0** (B365 close):
  * **X1:** calibration by outcome type, P band, league and season (favourite-longshot structure);
  * **X2 (residual information):** does Elo-difference or Form5-difference predict the outcome *after* the market
    probability? Logistic regression of each binary outcome on logit(market P) + feature. Fitted on discovery,
    evaluated by Δ log loss on confirmation, per league, with a bootstrap CI.
* **T, tennis:**
  * **T1:** frozen-engine (Betfair T−30) calibration by side, P band, tour, year, surface, level, best-of;
  * **T2:** tennis-data close: PS-fair vs B365 (both sides, all P) EV continuum and ROI; B365 margin by P region;
  * **T3 (residual information):** rank (log ratio), points (log ratio), surface, best-of, conditional on the frozen
    P. Discovery-fitted logistic, Δ log loss on confirmation.
* **N, NBA:** **N1:** calibration by side (home / away, favourite / underdog) and P band. Probability only.
* **P, prospective production snapshots** (tennis, 2026-09-23 → 10-01; about 6k per-book quotes, 20+ books with
  `last_update` timestamps):
  * **P1:** per-book margin, best-price frequency and dispersion versus the exchange mid (same scan);
  * **P2:** staleness (scan time − last_update) versus apparent EV;
  * **P3:** dispersion versus minutes-to-start.

  Outcomes are too few for return claims: descriptive only.

## Outputs
* `ATLAS.csv`, the Behaviour Atlas with the directive's fields;
* `HYPOTHESIS_REGISTRY.md`;
* `RESULTS.json`;
* `REPORT.md`.

Script: `scripts/edge_discovery_c1.py`.
