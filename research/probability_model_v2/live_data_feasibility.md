# Phase 2, Section 18 -- Live-Data Feasibility for the Fundamentals Feature Set

**Written 2026-09-22.** Since no fundamentals-based or blended architecture was nominated as a V2
candidate (see `PHASE2_RETURN_CHECKPOINT.md`, decision A), this question is not currently load-bearing
for any deployment decision. It is answered anyway, briefly, per the instruction's explicit request,
for the record and for any future Gate 1b that revisits fundamentals with a richer feature set.

## What the 9 tested features actually need, prospectively

Every fundamentals feature used in Gate 1 is a **rolling statistic over each team's own recently
COMPLETED matches** (goals/shots/SOT/corners/cards from the last 10 matches), plus a continuously
updated Elo rating. None of them require any information about the upcoming fixture itself beyond
which two teams are playing -- they need a live feed of **past** match results and box-score
statistics, updated after each round, not live in-play data.

| Requirement | Historical source (used here) | Prospective/live equivalent | Cost | Reliability/update cadence |
|---|---|---|---|---|
| Full-time score, per match | football-data.co.uk CSV | Same provider publishes updated season CSVs; alternatively already-integrated live odds/scores adapter (`ingestion/the_odds_api_scores.py`, built for settlement in §20) covers scores for the leagues already in production | Free (both) | football-data.co.uk updates on its own schedule, not verified in this phase to be same-day; the-odds-api scores adapter is already live-tested for settlement purposes |
| Shots, shots on target, corners, cards | football-data.co.uk CSV (`cycle_002_match_statistics.csv`'s source) | NOT currently covered by any adapter already built in this repository -- The Odds API does not provide box-score statistics | Unknown -- not investigated | Not verified |
| Elo rating | Derived entirely from full-time scores (no separate source needed) | Computable from whichever score source is used | Free | Same as score source |
| Referee identity | football-data.co.uk CSV | Not currently sourced live anywhere in this repository, and not used as a feature by any tested model regardless | N/A (unused) | N/A |

## Honest conclusion

**The score/result side of a live fundamentals pipeline is very likely feasible** (an adapter for
results already exists for settlement purposes). **The shots/SOT/corners/cards side is NOT currently
covered by anything already integrated, and this phase did not investigate or acquire a live source
for it** -- doing so was not justified, since no fundamentals-containing architecture demonstrated any
predictive value worth deploying. If a future Gate 1b research effort found a fundamentals or blended
architecture that did add value, this feasibility gap -- a live box-score-statistics source -- would
need to be closed, and its cost/reliability investigated, before that architecture could run daily.
No paid source was investigated or recommended here, per the instruction's explicit "do not purchase
anything."
