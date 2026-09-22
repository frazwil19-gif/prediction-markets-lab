# Market Priority Scorecard -- Phase 3, Section 8

Date: 2026-09-22. Evidence-based categorical scorecard (STRONG / MODERATE /
WEAK / BLOCKED), never an arbitrary numeric score, per the instruction's
explicit requirement. Each row cites the specific evidence behind its
category. Sourced from `EXISTING_DATA_INVENTORY.md`,
`EXHAUSTED_VS_OPEN_RESEARCH.md`, `HISTORICAL_SOURCE_AUDIT.md`, and
`LIVE_MARKET_COMPATIBILITY.md` above -- no category here is asserted without
a citation back to one of those documents.

## Football Over/Under 2.5 (money-qualification backtest, via new historical odds)

**Category: MODERATE.** Live side is STRONG (already live and producing
real candidates daily, one already paper-recorded). Historical side is
currently BLOCKED (measured: only 2-3 bookmakers ever quote closing OU2.5
in football-data.co.uk, 2 for 80% of matches, below the production
`min_bookmakers=3` floor -- `cycle_002_consensus_ou25.csv` is 0 bytes as
direct evidence). A credible, evidence-named path exists to unblock it
(Betfair Historical Data BASIC tier for soccer, `eventTypeId: 1`, free,
same source/process already proven to work for tennis) but has not yet been
acquired or verified to actually contain OU2.5-equivalent market coverage.
Net: MODERATE rather than STRONG, because the fix is plausible and free but
unconfirmed; MODERATE rather than WEAK, because a concrete, low-cost,
previously-successful acquisition path is already named.

## Football Asian Handicap (money-qualification backtest, via new historical odds)

**Category: MODERATE**, same reasoning and same blocking evidence as OU2.5
(measured insufficient bookmaker depth in the current archive;
`cycle_002_consensus_ah.csv` is also 0 bytes) and the same candidate fix
(the same Betfair archive, if it in fact carries AH-equivalent lines, which
is unconfirmed). Live side is only PARTIALLY there (`spreads` market
exists in The Odds API's documented catalogue per
`LIVE_MARKET_COMPATIBILITY.md` but is not yet fetched/parsed/wired -- a
small, low-risk extension, not a blocker).

## Football BTTS (Both Teams To Score)

**Category: WEAK.** UNEXPLORED, not BLOCKED: no historical-data audit has
been run for BTTS at all (unlike OU2.5/AH, where the insufficiency is
measured), and live-side wiring does not exist (a `btts` market key is
documented by The Odds API but never fetched by this codebase). WEAK
because the necessary audits simply have not happened yet -- this could
turn out STRONG or BLOCKED once someone actually checks, but right now
there is no evidence in either direction, only an absence of investigation.

## Football team totals

**Category: WEAK**, for the same reason as BTTS -- fully UNEXPLORED, no
audit run, live-side existence not even confirmed in The Odds API's
documentation for the configured leagues.

## Tennis Match Winner -- money-qualification backtest (via already-downloaded Betfair archive)

**Category: STRONG.** This is the only candidate in this scorecard where
every prerequisite is already satisfied with zero new acquisition: the raw
data already exists on Fraser's machine (Betfair Historical Data BASIC
tier, tennis, `eventTypeId: 2`, ~1.7M+ files combined across
`Downloads/tennis data/data.tar` and `Downloads/BASIC/2026/`), it is
already partially ingested and linked to TML match results (12,956/14,564
matches, 88.96%, per `WORKSTREAM_B_PRICE_COVERAGE_AUDIT.md`), the ingestion
pipeline already exists (`betfair_historical_schema.py`,
`betfair_market_index.py`, `tennis_betfair_linkage.py`), and the exact
research design needed (a Phase-1-style frozen money-qualification backtest
using consensus-as-probability) has a direct, already-proven precedent in
this same repo (Backtest Phase 1, §22 of the master directive) that would
only need to be pointed at tennis's linked dataset instead of football's.
Crucially, per `EXHAUSTED_VS_OPEN_RESEARCH.md`, this is a genuinely
different, non-duplicative question from what Workstream B already closed
(edge-hunting/model-vs-market, 13-for-13 REJECT) -- the money-qualification
question was never asked of this data.

## Tennis live production wiring

**Category: WEAK**, kept separate from the backtest question above because
it is a separate piece of work: no tennis ingestion adapter exists in
production (`LIVE_MARKET_COMPATIBILITY.md`), though The Odds API documents
tennis `sport_key` values that would plausibly support one, following the
exact pattern already proven for football. WEAK rather than BLOCKED because
nothing found so far suggests this is infeasible -- it simply has not been
attempted, and the football precedent is directly reusable engineering.

## Basketball moneyline

**Category: WEAK.** Fully UNEXPLORED: no historical data of any kind
audited in this repo, no live wiring, though The Odds API's public
sport-list documentation suggests live odds are plausibly obtainable. No
evidence yet in either direction.

## Cricket match winner

**Category: BLOCKED**, per explicit standing instruction (master directive
§14: "Cricket stays PAUSED -- do not start acquisition or code... until a
fresh decision reopens Cricket specifically"). This is a policy block, not
a data block, and is recorded as BLOCKED here to keep the scorecard
complete rather than silently omitting it.

## Recommended research ordering (evidence-based, not a numeric ranking)

1. **Tennis Match Winner money-qualification backtest** -- STRONG, zero new
   acquisition, reuses an already-built harness and an already-linked
   dataset. The fastest path to a second genuine result after Backtest
   Phase 1.
2. **Football OU2.5 / AH via the Betfair historical archive** -- MODERATE,
   free and low-effort to attempt (Fraser has already done this exact
   process once, for tennis), but carries real uncertainty about whether
   the free BASIC tier actually contains OU2.5/AH-equivalent lines for
   football -- this needs to be checked before being trusted, not assumed.
3. **Football BTTS / team totals** -- WEAK, would need their own audits
   before any acquisition or backtest decision could be made responsibly.
4. **Tennis live wiring** -- WEAK but low-risk engineering, worth doing
   opportunistically once/if the tennis backtest (item 1) produces a result
   worth acting on live; not urgent on its own.
5. **Basketball** -- WEAK, no evidence yet either way; lowest priority of
   the UNEXPLORED items given tennis and football OU2.5/AH are both more
   evidence-supported right now.
6. **Cricket** -- BLOCKED by standing policy; not reconsidered here.
