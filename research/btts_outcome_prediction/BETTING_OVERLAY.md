# Phase 5 — BTTS Historical Betting Overlay: BLOCKED

The BTTS probability estimator was frozen first (`HOLDOUT_PROTOCOL.json`), as Section 20 requires. After that, the
overlay question was checked. football-data.co.uk has **no historical BTTS odds**: zero columns across all 18 season
files. No other BTTS price archive exists in the repo.

**Historical betting overlay: BLOCKED_BY_HISTORICAL_DATA. Nothing was fabricated.** No money threshold, odds floor,
EV floor or stake was used or changed. The market-implied probability can't be used as its own "price" either,
because that would make EV zero by construction.

The answer has to come prospectively. Live BTTS quotes exist from 9 UK books including Betfair Exchange (see
`DATA_AUDIT.md`), and the fields to log are listed in `PROBABILITY_ENGINE_ARCHITECTURE.md` §4. Useful context for
whether live BTTS bets could clear the unchanged money policy: the estimator produces a ≥60% probability on only
~7–10% of matches. At fair odds that is about 1.67 or shorter, so a qualifying bet needs a price clearly above that.
Given the 1X2 evidence (next file), that will be rare.
