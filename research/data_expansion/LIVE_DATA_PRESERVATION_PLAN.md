# Live Data Preservation Plan -- Phase 3, Sections 14 & 15

Date: 2026-09-22. This document directly answers Fraser's explicit priority
question: **"what should we start archiving from The Odds API every day
right now? Every day that passes is an opportunity to accumulate timestamped
historical market data that we won't have to buy later."** It describes a
recommendation only -- per Section 14's instruction to "describe first,
don't silently change production," nothing in this document has been
implemented. No production code, schedule, or ledger has been modified in
this phase.

## The concrete gap, found by code inspection (not assumption)

`ingestion/the_odds_api_loader.py` fetches a full per-bookmaker odds panel
from The Odds API every scan: `ParsedEvent` (id, sport_key, commence_time,
home_team, away_team) containing a list of `ParsedBookmaker` (key, title,
last_update) each containing a list of `ParsedMarket` (key: "h2h" or
"totals") each containing a list of `ParsedOutcome` (name, price, point).
This is genuinely rich data -- confirmed live on 2026-09-19's smoke test to
include 20 distinct UK bookmakers for EPL alone, each with its own
`last_update` timestamp.

But this raw panel is never persisted. `storage.schemas.MarketRecord` (the
only record type that reaches `daily_cards/` and `paper_ledger/`) reduces
the entire panel down to: one `bookmaker_count` (an integer), one
`consensus_probability`/`consensus_mean`/`consensus_median`/
`consensus_std` (aggregated across all bookmakers), and one
`exchange_odds`/`exchange` pair (the single best price selected for the
value comparison). Confirmed via direct grep of `run_daily_scan.py` and
`the_odds_api_loader.py`: no raw-panel write, save, or persist call exists
anywhere in the ingestion or scanning path. Once a scan completes, the
individual bookmaker names, individual prices, and individual per-bookmaker
timestamps that produced that day's consensus and best-price figures are
gone -- unrecoverable, because The Odds API does not offer a historical
lookback endpoint on its free tier (and even a paid historical endpoint
would only start from whenever purchased, not retroactively).

This is exactly the kind of loss Fraser flagged: every day the scanner runs
without capturing the raw panel is a day of real, timestamped,
multi-bookmaker market data that is gone forever and would otherwise need
to be bought (if even purchasable at all -- historical per-bookmaker
timestamped panels for these specific leagues/markets may not exist as a
purchasable product at any price).

## What to start archiving now (recommendation, not yet implemented)

1. **The raw per-bookmaker panel, once per scan, verbatim.** For every
   scan, persist one row per (event, bookmaker, market, outcome): sport_key,
   event id, commence_time, home_team, away_team, bookmaker key/title,
   bookmaker `last_update`, market key, outcome name, price, point (for
   totals), and the scan's own wall-clock fetch timestamp. This is a direct,
   lossless serialisation of data already being fetched and paid for in API
   credits -- no new API calls, no new cost, only a new write step. This is
   the single highest-value addition: everything else below is either
   already partially captured or derivable from this if captured.

2. **A genuine closing-price snapshot per fixture.** The scanner currently
   only captures whatever price exists at scan time (07:00 UTC daily,
   currently). To eventually compute real (not proxy) CLV per Section 13's
   minimum requirement, a second capture close to kickoff (or at a defined
   fixed offset before it) is needed, tagged as a closing/near-kickoff
   snapshot distinct from the original scan snapshot. Without this, every
   future CLV calculation on live data will hit the exact same
   single-snapshot limitation `docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`
   already documents for the historical football-data.co.uk archive --
   an entirely avoidable repeat of a known problem, if not addressed now.

3. **Every scan's full raw HTTP response, or at minimum the parsed
   `ParsedEvent` list, before any reduction.** Even if the structured
   per-bookmaker table in (1) has an unanticipated gap, a preserved raw
   response can be re-parsed later; a discarded one cannot. Cheap to store
   (JSON, one file per scan) and provides insurance against retroactively
   discovering that today's chosen table schema missed a field kickoff/
   Section 15 later shows is needed for CLV or a future market family (for
   example, `spreads` or `btts` outcomes, not currently parsed at all, per
   `LIVE_MARKET_COMPATIBILITY.md` -- if the raw response is kept, extending
   the parser later to cover those markets could still recover their odds
   retroactively for every day archived from today onward).

4. **Bookmaker identity and count over time, not just the aggregated
   consensus.** Knowing which specific bookmakers were present/absent on a
   given day (already fetched, currently discarded) would let a future
   researcher study whether bookmaker-panel composition itself drifts
   (new bookmakers added/removed, coverage gaps for certain leagues) --
   useful context for interpreting any future backtest run on data
   collected from this point forward.

## What this would cost

Zero additional API credits (all of this data is already fetched every
scan; the cost is purely storage and a small amount of new, additive write
code). Storage is small in absolute terms: even a full per-bookmaker
per-outcome table across 3 leagues, ~2 markets, ~20 bookmakers, once daily,
is on the order of a few hundred rows per day -- trivially cheap to keep in
the repo's existing gitignored-then-committed convention (mirroring
`daily_cards/`, `paper_ledger/`, `real_bets/`).

## What this document does NOT do

It does not modify `the_odds_api_loader.py`, `run_daily_scan.py`,
`storage/schemas.py`, any GitHub Actions workflow, or any config file. It
does not add a new persisted table, a new scheduled job, or a new
close-to-kickoff scan. All of the above is a recommendation for Fraser (and
ChatGPT, per the project's operating split) to approve before any
production change is made -- consistent with Section 14's explicit
instruction and this phase's own restriction against modifying production
betting logic. If approved, the concrete implementation would be a small,
additive change in the same style as every other addition this project has
made to `the_odds_api_loader.py`/`run_daily_scan.py` to date (new optional
persistence step, appended after the existing scan logic, off by default
until explicitly wired in) -- not a rebuild.
