# V2-7 Prospective Shadow Cards (cer-2): Pre-registered Analysis Plan

**Written 2026-09-30, before any prospective shadow card exists.** Logging is not activated: `logging_enabled` and
`settlement_enabled` are both `false`. This plan is fixed before the first outcome. Any later change needs a dated amendment
that states whether outcomes had been seen, and the original text stays as written.

**Research question.** Across tennis match-winner legs, do singles, doubles or trebles give the strongest statistically supported,
risk-adjusted opportunities? No direction is assumed.

**What this study can and cannot show.** Every multi price is **INDICATIVE / NOT EXECUTION-VERIFIED**: it is the product of one
bookmaker's leg prices in one snapshot. Returns computed from those prices are *indicative returns*. They are always reported
separately from executable-price evidence, of which there is none. Hypothetical log-growth superiority is **not** evidence of live
profitability.

## 1. Units, validity and deduplication (fixed)
- **Valid card:** a row in `prospective/<YYYY-MM>/cards.csv` whose `record_id` has a `scan_runs.csv` row with status `OK` or
  `OK_ZERO_CANDIDATES` and mode `PROSPECTIVE`. Rows under any other status (FAILED, CAP_EXCEEDED, INPUT_INVALID, …) are
  excluded and counted as missingness (§6).
- **Primary unit, HIGH_P:** a unique leg set (`legset`). If the same leg set appears in several scans, only the **first logged
  scan** counts in the primary analysis; later appearances go into a secondary "latest scan" sensitivity check.
- **Primary unit, POS_EV:** the (book, leg set) card in its first logged scan. Summaries by leg set collapse books first, taking the
  median indicative price, so that replication across books is never counted as independent evidence.
- **Treble weights:** HIGH_P trebles have `sample_weight` = 10, from a fixed 10% hash sample on the leg set with the salt in the
  config. All HIGH_P treble estimates are weighted (Horvitz–Thompson). Singles and doubles have weight 1.
- **Settlement:** the last `card_settlements.csv` row per card is current, following `supersedes`. The following are **excluded**
  from calibration and counted: `VOID`, `WON_REDUCED_VOID_LEG`, cards with an `UNMATCHED` or `CONFLICT` leg, and cards overdue
  by more than 7 days. Cards with retirement flags stay in the analysis and are also reported separately.

## 2. Pre-declared tables (cohort × k ∈ {1,2,3} × probability band)
Bands on P_joint are fixed: 0.20–0.35, 0.35–0.50, 0.50–0.65, 0.65–0.80, 0.80+. For each cell:
1. n cards, n unique leg sets, n unique matches, and the **effective n** (§3).
2. Predicted versus realised joint win rate (weighted), and calibration-in-the-large = realised − predicted, with a 95% CI.
3. Brier score and log loss against a climatology baseline (the cell's mean predicted P).
4. POS_EV only: mean indicative EV at logging versus mean indicative realised return per unit, labelled INDICATIVE.
   Also the hit rate of `SHADOW_CANDIDATE` (EV lower bound > 0) cards versus `SHADOW_WATCH` cards.
5. Equal-total-stake comparison at stakes 1%, 2% and 5% (fixed). This compares realised log growth of each multi
   against the same legs staked as singles (s/k each), using settled leg outcomes. The model-implied expected values stored at
   logging are reported alongside. Assumptions are stated in §7.

## 3. Uncertainty (fixed methods)
- **CIs:** a cluster bootstrap with 2,000 resamples, **clustered by sport-day (UTC date of the earliest leg start)**, with seed 20260930.
  As a sensitivity check, the same bootstrap is re-run clustered by match (each card assigned to its earliest match).
- **Effective n:** Kish, n_eff = (Σw)² / Σ_i Σ_j w_i w_j ρ_ij. ρ_ij is the model-implied correlation of the two cards' win indicators
  under leg independence on distinct matches: identical leg sets give 1, disjoint sets give 0. This is computed per scan
  (`scan_diagnostics.jsonl`) and pooled over the primary units. **Card counts are never reported as sample sizes.**
- A difference counts as detected only if its 95% cluster CI excludes 0. There is no significance testing on individual cards, and no
  selection of "best" cards or books after the fact.

## 4. Risk diagnostics (fixed)
- Losing streaks and drawdown: first-logged cards are ordered chronologically by the settlement time of their last leg, one
  sequence per cohort and k. Report the longest losing streak, and the maximum drawdown of a 1-unit indicative P&L sequence
  (POS_EV only). Compare each against the exact streak distribution implied by the predicted P (DP as in `AUDIT_AND_LOGGER.md` §1).
- Shared-event exposure: the distribution per scan of `max_event_share_of_cards`, `share_of_card_pairs_sharing_a_match` and
  `max_books_repeating_one_leg_set`.

## 5. Decision rules (fixed; nothing here is automatic)
- **Thirty settled scans** (scans whose valid cards are all settled or explicitly excluded) trigger an **operational review**: data
  completeness, failure rate, storage growth, settlement coverage and exposure. **This is not statistical validation**, and no gate
  changes because of it.
- **Minimum evidence for a claim** depends on the claim. It is judged from the CI, never from a card count.
  - "Doubles are calibrated in band b": the 95% CI of calibration-in-the-large must lie within ±3 pp. At p ≈ 0.55 this needs
    n_eff ≈ 1,000 or more, so expect months of collection.
  - "Multis out-grow singles at stake s": the CI of the mean per-card log-growth difference (card − singles) must exclude 0.
  - "Trebles above 0.65 are calibrated": no claim is possible until n_eff in that cell reaches 300 or more.
- **No threshold optimisation on early outcomes.** Pools, bands, stakes, sampling rate and salt are frozen for cer-2. Changing
  them needs a new rule version and a new plan, and data collected under cer-2 stays cer-2.
- A POS_EV multi cannot be considered for paper qualification until all of the following hold:
  - an executable accumulator price has been verified at the book;
  - the calibration claim for its (k, band) cell is met;
  - singles have met their own live gate;
  - Fraser has separately approved it.

## 6. Missingness, selection and sampling effects (reported every review)
- Scan records by status per day. Any production scan (in `exchange_probability_snapshots.csv`) with no shadow scan record is
  reported as `MISSING_SHADOW_RUN`.
- Legs excluded by quality code (EXCHANGE_BOOK_TOO_WIDE, stale quotes, STARTED_BEFORE_LOGGING, …) as a share of validated
  favourites. Truncation counts (HIGH_P `max_events`, POS_EV `max_legs_per_book`) and POS_EV cap anomalies.
- **Selection bias statements:**
  - HIGH_P covers only favourites with P ≥ 0.70 in tight Betfair books that are priced by at least one bookmaker.
  - POS_EV covers only favourites (the logger never takes the underdog side).
  - The universe is the Odds-API-covered tournaments only.
  - Unsettled cards are more likely to involve lower-tier events.
- Sampling check: the realised sampled fraction of HIGH_P trebles per scan versus 10%, plus a weighted versus unweighted comparison.

## 7. Equal-capital assumptions (stated once, applied everywhere)
One period. Total stake s is a fraction of the bankroll at the start of the period, placed on the card, compared with s/k on each of
the same k legs placed as singles at the same time. Further assumptions:
- leg outcomes are independent (supported for distinct matches by V2-7 A1/A2 at the stated precision);
- expected-growth figures treat model P as the true P, whereas realised figures use actual outcomes;
- each leg wins or loses; void legs are excluded from the comparison;
- there is no rebalancing between legs, and no compounding within the period;
- prices are indicative same-book prices;
- utility is logarithmic.

Under these assumptions, the card grows faster only at small stakes (P = 0.6 @ 1.73: below 4.8% for a double and 4.1% for a
treble). This advantage is sensitive to probability error (see `SHADOW_INTEGRATION_AUDIT.md` §1).
