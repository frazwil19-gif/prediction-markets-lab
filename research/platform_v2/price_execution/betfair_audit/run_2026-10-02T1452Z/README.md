# Betfair catalogue audit — run 1 (2026-10-02 14:52 UTC, Fraser's Mac, delayed key, 65 read-only calls)

These are aggregates only; the raw responses stay gitignored on Fraser's machine. This run was made with the
PRE-FIX script, so the `COVERAGE.*` files carry two classifier errors, corrected below.

## Reading
**Timing — the run is inconclusive for prop markets.**
- It happened during the international break.
- Every sampled top-flight event was 7–8 days ahead (9–10 October).
- At that distance Betfair lists only core markets for those events: Match Odds, Over/Under 0.5/1.5/2.5,
  Alt Total Goals, Asian Handicap, Correct Score, BTTS.
- No corners, bookings/cards, player SOT, player card or GK saves markets appeared for any sampled event, and
  none appear in any competition's market-type list.
- That does not show they are absent. A same-day reserve match in the run already carried about 30 market types,
  which fits the pattern of markets being added close to kickoff.

**Classifier error 1:** "player_to_score: GOOD COVERAGE" is wrong. It was `BOTH_TEAMS_TO_SCORE` matching the
keyword "TO_SCORE". No player goalscorer markets were listed.

**Classifier error 2:** B1 matched "Belgian Beloften Pro League Reserve". The correct competition, "Belgian Pro
League", is listed.

**Unresolved competitions:**
- SC0 is listed but had no events in the window.
- N1 and P1 had no Eredivisie or Primeira Liga competition listed at all; their leagues are on the break.

**Fixed script (`betfair-audit-fixes`):**
- exact Match Odds matching and exclusion of composite and outright codes;
- reserve and youth competitions excluded;
- only events within 36 hours of kickoff are sampled (`--max-hours-to-kickoff`).

The re-run is due on matchday, about 09:00–11:00 UK time on Saturday 10 October.
