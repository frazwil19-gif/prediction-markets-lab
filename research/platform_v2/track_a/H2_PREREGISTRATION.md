# H2 — Pre-close execution measurement (PRE_CLOSE_VALUE) — PRE-REGISTRATION

Date: 2026-10-02. Approved by Fraser: "I APPROVE adding prospective execution-quality measurement, subject to the
existing credit budget". This metric is **diagnostic only**: it never enters qualification, grading or staking.

## Population
Paper selections in `paper_betting_v2/selections.csv` (all rule versions; the rule version is recorded). Each
selection is captured once, before its event starts.

## Decision-time record (copied, never modified)
selection_id, prediction_id, rule_version, sport, event, selection, decision P, decision bookmaker, decision odds,
commission, decision timestamp (`decision_at`), quote timestamp (`price_observed_at`).

## Later reference observation
* **When:** an hourly job looks for selections whose event starts within the next `capture_window_minutes` (75).
  For each sport key it makes **one** `/v4/sports/{key}/odds` call (h2h, region uk). That costs 1 credit and returns
  every book plus Betfair exchange back and `h2h_lay` for every event.
* **Reference probability:**
  * p_ref = de-vigged Betfair exchange **mid** (mean of back and lay), normalised across outcomes;
  * fallback, if no lay is available: the median of UK-book proportional fair probabilities. The basis is recorded.
* **Recorded alongside:** best UK price at capture, median UK price at capture, capture timestamp, minutes before
  start.

## Metrics (names are fixed)
* **PRE_CLOSE_VALUE** = p_ref × (decision_odds − 1) × (1 − commission) − (1 − p_ref). This is the EV of the
  decision price under the later reference probability.
* **PRE_CLOSE_PRICE_RATIO** = decision_odds / best UK odds at capture − 1.
* **Not CLV.** The benchmark is the last pre-start observation (typically 5–75 minutes before start, depending on
  GitHub scheduling), so these are never labelled CLV. A row may carry `clv_proxy_quality = NEAR_CLOSE` only when
  captured ≤ 10 minutes before start.

## Credit control
* Consumer `pre_close_capture` in `config/api_budget.json`.
* Monthly cap 25 credits (≈ 5 paper bets/week, worst case one call per bet).
* It pays only while remaining credits are ≥ the Tier-2 shadow floor (it protects Tier 1 football, tennis, NBA and
  settlement), and never below the hard floor.
* A call returning no events is free. Every call is logged to `status/credit_ledger.csv`.

## Analysis (at the review trigger: 30 captured selections, or the protocol interim, whichever comes first)
* Mean PRE_CLOSE_VALUE, with a bootstrap 95% CI.
* Share > 0.
* Relationship to decision EV and to settled return.
* Breakdown by sport, book and minutes-before-start.

There is no rule change from this analysis without separate approval.
