# Prop price probe 2 — Gate 0 interpretation (PRE-REGISTRATION)

Written and committed 2026-10-02, BEFORE the paid call. Approved by Fraser 2026-10-02: "SECOND AND FINAL BOUNDED PROP
PRICE PROBE", at most 2 credits, ONE EPL event, region uk, markets `alternate_totals_corners,alternate_totals_cards`,
ONE paid event-odds request, HARD STOP afterwards regardless of result. No player props, no other region, no other
event, no recurring capture.

## Timing rule (deterministic)
At run time the script lists EPL events with the FREE `/events` endpoint and computes h = hours to kickoff.
- Eligible: 1 <= h <= 24 (hard requirement h <= 24; h >= 1 so quotes are not pulled at kick-off).
- Preferred: 6 <= h <= 12. If any preferred event exists, choose the earliest-kicking-off preferred event; otherwise
  the earliest-kicking-off eligible event.
- If no event is eligible: NO paid call; the attempt is logged (attempts.csv) and the authorisation is not consumed.
- Trigger: a push to branch `probe/prop-price-c2`, timed by Claude for about T-8h before the first EPL kickoff of the
  next round (push-triggered runs start within minutes; scheduled cron runs here are 2-7 h late, so cron is not used).
- One-shot guard: once `research_shadow/prop_price_probe/probe2/result.json` exists, the script never calls again.

## Per-book evidence (computed from the raw response by scripts/prop_probe_audit.py; raw JSON preserved)
For each bookmaker x market x line: Over price, Under price, last_update, event commence time. Where BOTH sides
exist: raw implied P(over), P(under), overround = sum - 1, proportional de-vig P(over), P(under). One-sided quotes
are recorded as one-sided; the missing side is never manufactured.
Per comparable line: n books, n complete two-sided books, best/median Over, best/median Under, best/worst dispersion,
median fair P(over), range of fair P(over), median overround. Exchanges (betfair_ex_uk, smarkets, matchbook, any
other exchange key) are flagged; exchange commission from config/bet_selection_v2.yaml; unknown -> not assumed zero.

## Gate 0 outcomes (assessed separately for corners and for cards)
- **A — PRICEABLE:** at least one legitimate executable UK venue (a non-exchange UK bookmaker, or an exchange with
  known commission) quotes complete two-sided prices at >= 1 line, so a fair probability can be constructed.
  Consensus is "robust" only if >= 3 complete two-sided books share a line; with 1-2 books it is recorded as
  A (thin). A allows the corners probability cycle to proceed after Fraser reviews this evidence; it does NOT itself
  start Phase 2/3 and says nothing yet about financial quality.
- **B — PARTIALLY PRICEABLE:** the market appears but no venue gives complete two-sided prices at any line (one-sided
  only), or only an exchange with unknown commission. Probability research may proceed; financial validation is
  PRICE_DATA_REQUIRED.
- **C — CURRENTLY UNPRICEABLE THROUGH THIS API:** no UK bookmaker returns the market although the event is <= 24 h
  from kickoff. Record "PREDICTABLE / CURRENTLY UNPRICEABLE VIA CURRENT API", freeze, no third probe, next research
  priority becomes TEAM GOALS / TEAM TOTALS.
An API error (non-2xx) is not an outcome: it is reported, and no retry is made without Fraser's approval.
