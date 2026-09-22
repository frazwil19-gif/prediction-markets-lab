# Phase 3, Section 6 -- Historical Odds Source Audit

**Written 2026-09-22.** Investigates sources that could close the Over/Under 2.5 / Asian Handicap
bookmaker-depth gap Backtest Phase 1 identified, and separately documents a significant already-
acquired asset discovered during this audit. FREE prioritised over LOW COST over PAID, per the
instruction. Nothing was purchased. No API key was exposed.

## Headline finding: Fraser already has, and has already partly used, a large free Betfair historical dataset

While inventorying non-repo local assets (per Section 2's instruction to check what already exists
before searching externally), two connected folders on Fraser's machine were found to contain a
substantial archive of **Betfair Exchange Historical Data** (the free BASIC tier):

- `Downloads/tennis data/data.tar` -- 4.17 GB, a POSIX tar archive of ~996,779 `.bz2`-compressed JSON
  market-stream files, organised `BASIC/<year>/<month>/<day>/<eventId>/{<eventId>.bz2,
  1.<marketId>.bz2}` -- exactly Betfair's documented Historical Data file layout.
- `Downloads/BASIC/2026/` -- an already-unpacked continuation of the same pull, January through
  September 2026, ~28,500 event folders, 746 MB.

Every file sampled across both locations (8 samples, spanning 2021 through September 2026, market
types MATCH_ODDS / SET_WINNER / SET_BETTING / TOURNAMENT_WINNER / PLAYER_A_WIN_A_SET) carries
`"eventTypeId": "2"` -- Betfair's code for **Tennis**. This is a single, apparently ongoing, tennis-
only historical pull, not a multi-sport archive.

**This is not new to the project.** `reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md`
(2026-09-15) already identified and recommended exactly this source ("Betfair Historical Data ...
BASIC (free) ... Match Odds market data ... tennis, 2021-2025") with step-by-step account instructions.
Fraser evidently followed through (file timestamps cluster around 2026-09-16, the same day Workstream
B's closure record is dated), and Workstream B's own closure document confirms the information set it
tested was exactly "Betfair BASIC-tier last-traded price." The already-built ingestion/linkage code
(`ingestion/betfair_historical_schema.py`, `ingestion/betfair_market_index.py`,
`normalisation/tennis_betfair_linkage.py`) already parses this exact archive, and already achieved a
strong link rate (12,956 of 14,564 canonical matches, 88.96%) with 83.78% of matches usable at a
30-minute pre-match horizon with a genuinely fresh (not stale) price.

**What this means:** the raw data sitting in `Downloads/tennis data` and `Downloads/BASIC/2026`
is the SAME source and SAME granularity (last-traded price, no volume, no order-book depth) that
Workstream B already tested and closed for edge-hunting -- it is not a materially new information
source for THAT question, and reopening edge-hunting on it would be exactly the mistake this phase's
own instruction warns against. **It is, however, unexploited for a different question this project has
never asked of it**: a Phase-1-style frozen money-qualification backtest using consensus-as-probability
(no new predictive claim), which is squarely the current, corrected project objective (master directive
§14) rather than the now-closed edge-hunting objective. See `PHASE3_RETURN_CHECKPOINT.md` for why this
is proposed as a candidate next cycle, and note it requires NO new acquisition at all -- the data and
linkage pipeline both already exist.

## Candidate sources for the football OU2.5/AH gap

### 1. Betfair Historical Data -- football/soccer (eventTypeId 1), BASIC (free) tier

**Verdict: LIKELY USABLE, NOT YET ACQUIRED. Top candidate.** The same free product, same account
Fraser already registered for tennis, filtered to Soccer instead of Tennis. Confirmed via a fresh web
search this session (2026-09-22): the jurisdiction restriction is unchanged since the 2026-09-15 tennis
audit (Betfair.com customers only; Betfair.br/.it/.es/.ro/.se excluded -- not relevant for a UK-
registered account) [Betfair Developer Program](https://support.developer.betfair.com/hc/en-us/articles/360008664937-Which-juristictions-is-Betfair-Exchange-Historical-Data-available-to).
Betfair's own Automation Hub documentation states the historic data covers "nearly all markets offered
on the Exchange since 2016" [Historic Data Site -- The Automation Hub](https://betfair-datascientists.github.io/data/usingHistoricDataSite/),
and Betfair Exchange is well known to carry deep, liquid Asian Handicap and Over/Under goals markets
for football -- but the exact market-type list for the free BASIC tier could not be confirmed without
logging in (same limitation the original tennis audit stated honestly; this is a real gap, not
glossed over). **Provider**: historicdata.betfair.com. **Format**: same `.tar`/`.bz2` JSON stream
files as the tennis archive already in hand. **Timestamp granularity**: last-traded-price ticks
(BASIC), no volume/depth (needs paid ADVANCED/PRO, not recommended). **Cost**: free. **Licensing**:
Betfair.com account holders only, per the jurisdiction rule above. **Known limitation, stated rather
than assumed away**: whether BASIC-tier Asian Handicap markets include every line traded (not just the
"main" line) is unconfirmed without an account login -- exact-line matching (already flagged as the
one remaining gap for AH in production, per master directive §17) would need to be designed against
whatever the real download actually contains, not assumed in advance.

### 2. football-data.co.uk (existing source)

Already fully audited in Backtest Phase 1 -- confirmed insufficient bookmaker depth for OU2.5/AH
consensus (2-3 bookmakers/match). Not re-litigated here.

### 3. Other free/low-cost odds archives (Kaggle, community GitHub datasets)

Not deeply investigated this phase, since Betfair's own historical data (same provider, same account,
same free tier, already proven usable for tennis) is the strongest available candidate and checking
account-gated alternatives without logging in would only repeat the "cannot verify without an account"
limitation the tennis audit already documented once. If Betfair's football coverage turns out
inadequate on inspection, this is the natural next place to look -- flagged as a fallback, not
investigated further here per the instruction's "do not download huge datasets before establishing
their purpose."

## Conclusion

No purchase is recommended or needed. The single highest-value action available to Fraser is an
account action he has already successfully completed once (for tennis): log into
historicdata.betfair.com, filter Sport = Soccer, select the BASIC (free) package, and download the
relevant date range -- the exact same process `reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md`
already documented step-by-step for tennis. This is Decision Option B (`PHASE3_RETURN_CHECKPOINT.md`).

Sources: [Which jurisdictions is Betfair Exchange Historical Data available to -- Betfair Developer Program](https://support.developer.betfair.com/hc/en-us/articles/360008664937-Which-juristictions-is-Betfair-Exchange-Historical-Data-available-to), [Historic Data Site -- The Automation Hub](https://betfair-datascientists.github.io/data/usingHistoricDataSite/)
