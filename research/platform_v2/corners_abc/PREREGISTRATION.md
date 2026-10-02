# Corners A / B / C market comparison — PRE-REGISTRATION

Written and committed 2026-10-02, BEFORE any corners market-price evidence exists. So far there has been one empty
probe (no quotes); probe 2 is scheduled for 2026-10-10. Directive: "NEXT DIRECTIVE — TURN THE RESEARCH PLATFORM INTO
PROFIT ENGINES", §1A.

Research only. No paper corners betting, no EV-based selection and no production use without separate approval from
Fraser. ROI is never used to choose a probability model.

## Decision this changes
Whether sports-only corners probability (Model A) contains economically useful information relative to the corners
market. The outcome is one of three: reject corners as an independent edge source, take a hybrid forward, or
investigate executable EV.

## 1. Models
- **A — sports-only.** Model `corners-A-1.0`:
  - It is the frozen Model A specification (`props_c1/corners/model_a/FROZEN_SPEC.json`: G3 rolling-20 corners
    for/against, NB marginals plus a Gaussian copula).
  - It is refit ONCE on all `Matches.csv` data before 2026-07-01, using exactly that specification.
  - The coefficients, NB dispersions and ρ are written to `corners_A_v1_params.json`. They are committed before the
    first prospective prediction and never refit during this comparison.
  - Prospective features are built from Football-Data CSVs (same definitions). A parity check against the `Matches.csv`
    features on overlapping matches is reported.
- **B — market consensus.**
  - Per venue: a two-way proportional de-vig of Over/Under at a line, giving fair P(over).
  - Exchanges (back/lay available): implied P from the back/lay mid, used only when the spread condition in §4 holds.
  - Consensus: the median fair P(over) across venues with complete two-sided quotes at that line in the capture.
  - Sensitivity only, not used for decisions: power de-vig, and the best-venue fair P.
- **C — hybrid.** Logistic stacking: logit p_C = β0 + β1·logit p_B + β2·logit p_A.
  - β is fitted on the FIT block (the first 150 eligible events in chronological order).
  - β is then frozen (committed with SHA) and applied unchanged to the EVALUATION block (every later event).
  - No other C variant may be tried on the evaluation block.

## 2. Data, periods and capture timing
- **Leagues:** E0 E1 SC0 N1 D1 F1 SP1 I1 P1 B1.
- **Period:** prospective, from the first capture after this commit. There is no historical corners price panel, and
  paid Odds API history is not approved.
- **Captures:** at least one snapshot per event between T−24h and T−60min.
  - The **primary snapshot** is the latest one that is ≥ 60 minutes before kickoff (pre-lineup).
  - Snapshots after kickoff are never used.
- **Model A timing:** probabilities are computed from data available before the capture. Feature rows built later
  than the capture are not allowed.

## 3. Lines and units
- **Unit:** the event × line.
- **Primary analysis:** one row per event, at the event's **main line**. That is the line among {7.5…13.5} with
  two-sided quotes whose B P(over) is closest to 0.5 (ties go to the lower line). This stops events with many lines
  from being overweighted.
- **Secondary analysis:** all two-sided lines 7.5–13.5, with clustered uncertainty by event.

## 4. Data-quality rules (fixed)
A quote is valid only if all of these hold:
- odds > 1.01 on both sides;
- the venue's two-way overround is in [0, 0.15];
- the quote timestamp (`last_update`, or exchange snapshot time) is within 30 minutes of the capture time;
- the capture is ≥ 60 minutes before kickoff.

Exchange rules:
- An exchange line is used only if back and lay both exist and the lay/back − 1 ≤ 0.10 on each side.
- Exchange commission comes from `config/bet_selection_v2.yaml`. If it is unknown, the venue is excluded from
  executable pricing (it is never assumed to be zero). Commission does not affect B's fair probability.

Event-level rules:
- An event is excluded if kickoff moves by more than 60 minutes after capture, or if the match is abandoned or void.

## 5. Missing prices
- Events without a valid two-sided main line are excluded from the A/B/C comparison and counted by reason.
- Model A predictions are still logged for them; they feed A's own prospective calibration but not the comparison.
- Missing data is never imputed.

## 6. Metrics
- **Primary:** binary log loss at the main line.
- **Secondary:**
  - Brier score;
  - calibration intercept and slope (logistic recalibration), plus calibration-in-the-large;
  - reliability by probability band (deciles when N ≥ 300, otherwise quintiles);
  - N and the number of venues per event;
  - league and season (temporal) breakdowns;
  - all-lines secondary analysis;
  - the same metrics for executable-price diagnostics, reported only.
- **ESS:** one row per event at the main line, so ESS = N. The all-lines analysis uses event-clustered bootstrap.
- **Uncertainty:** event bootstrap, 2,000 resamples, seed 7.

## 7. Confirmatory tests (on the EVALUATION block; A vs B also reported on all events)
1. **A vs B:** Δ = LL(A) − LL(B). "A beats B" iff the 95% CI upper bound is < 0.
2. **Incremental information of A given B:**
   - On the FIT block: the likelihood-ratio test of β2 = 0 (reported).
   - Confirmatory test: on the EVALUATION block, Δ = LL(C) − LL(B). "A adds information" iff the CI upper bound is < 0.
3. **C vs B:** the same Δ as test 2, which is the primary hybrid test.

## 8. Evidence trigger, not calendar
- **Confirmatory evaluation:** when the EVALUATION block reaches ≥ 300 events with valid main lines.
- **INTERIM:** at ≥ 150 evaluation events, for reporting only. No promotion decision may be taken at INTERIM, except
  an early CASE 3 null when the C − B 95% CI lower bound is > 0.
- **Futility review:** if prices cannot be collected at a rate that reaches 300 evaluation events within one season,
  report that as a pricing-infeasibility finding.

## 9. Stability requirements for any positive verdict
- The direction of Δ must agree in ≥ 60% of leagues that have ≥ 30 evaluation events.
- No league with ≥ 50 evaluation events may show the opposite sign with a CI excluding 0.

## 10. Decision tree (fixed)
- **CASE 1 — A beats B robustly** (test 1 positive plus §9): investigate whether the probability advantage produces
  positive executable EV. That is a separate pre-registered financial study in PROSPECTIVE_SHADOW: best executable
  net price, uncertainty-adjusted EV, no stakes.
- **CASE 2 — B ≥ A, but C beats B robustly** (tests 2/3 positive plus §9): the hybrid becomes the candidate
  probability engine and goes to the same financial study.
- **CASE 3 — B ≥ A and C does not beat B:** reject sports-only corners as an independent edge source. Record the
  null and do not rescue A (no re-specification on these data).
- **Promotion cap:** promotion from any case goes at most to PROSPECTIVE_SHADOW. Paper betting and money each need
  explicit approval from Fraser.

## 11. Separation of prices (never substituted)
Every row stores three prices separately:
- MARKET_CONSENSUS (B's fair P, plus the venues used);
- BEST_EXECUTABLE (the best net odds on each side across valid venues, with venue and commission);
- DECISION price (empty in this research phase).

## 12. Price-source dependency
This comparison needs a legitimate recurring two-sided corners price source. Candidates:
- recurring Odds API event-odds capture, which needs Fraser's approval because it costs credits per event;
- the Betfair Exchange API with read-only delayed credentials, once the catalogue audit confirms corners markets.

Until one is approved, the collector logs Model A predictions and outcomes only, with `market_status =
NO_PRICE_SOURCE_ENABLED`.
