# API Usage Plan after V2-5 (plan 500/month; target ≤ 425; reserve ≥ 75)

| consumer | rule | projected / month |
|---|---|---|
| football daily_scan (core) | 3 leagues × (h2h + totals) = 6 per scan | ~180 |
| football settlement, Odds API (core, until the football-data switch) | **new V2-5 guard:** a league's scores (2 credits) are fetched only if a pending bet kicked off within the 3-day window | ~40–90 (was up to ~180: 6/day every day) |
| tennis boards (optional) | 1 per covered key per board; cap 120; floor 150 | 60–120 |
| NBA (optional, from 20 Oct) | ≤1 odds call/day only when games start within 36 h; scores every 3rd day; cap 60; floor 150 | ~35 (Oct, part month), ~50 (Nov+) |
| unified board: football 1X2/O-U/DC, tennis mirror, football settlement | reuse data already fetched + free football-data.co.uk | **0** |
| explicit DC prices | not fetched (probability validation does not need them) | 0 |
| **total** | | **~315–440**; caps and floors stop optional consumers first |

After the settlement switch the Odds API scores fallback falls to ~0–20, giving ~300–370 in a normal month.
Limitation: daily_scan does not log its own credits (core; left unchanged). Health reports the last value any logging
consumer saw. Remaining credits on 24 Sep: 449 (51 used this month).
