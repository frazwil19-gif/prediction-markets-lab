# Phase 3 -- Data Expansion & Next-Market Research Decision -- Return Checkpoint

Date: 2026-09-22. This is the master synthesis document for "PHASE 3 --
DATA EXPANSION & NEXT-MARKET RESEARCH DECISION." It answers the full
25-point instruction and must remain internally consistent with
`EXISTING_DATA_INVENTORY.md`, `MARKET_COVERAGE_MATRIX.csv`,
`EXHAUSTED_VS_OPEN_RESEARCH.md`, `HISTORICAL_SOURCE_AUDIT.md`,
`LIVE_MARKET_COMPATIBILITY.md`, `MARKET_PRIORITY_SCORECARD.md`, and
`DATA_ACQUISITION_PLAN.md`/`LIVE_DATA_PRESERVATION_PLAN.md` above -- all
already written this phase and cited by point below rather than repeated
in full.

**1. Instruction received and scope confirmed.** Full audit of ALL existing
data already in the repo, across every sport/market, before any external
search -- completed. Nothing was assumed available; every claim in this
checkpoint traces to a file that was actually opened, a CSV that was
actually queried, or a device folder that was actually listed this session
or the prior one within this same phase.

**2. Existing-data inventory.** Complete: `EXISTING_DATA_INVENTORY.md`.
Football has deep 1X2 history (5,800+ matches, E0/E1/SC0, 2020/21-2025/26,
rich rolling fundamentals) and functioning live OU2.5 production, but
shallow OU2.5/AH historical bookmaker depth. Tennis has a large, previously
undocumented-as-tested-for-this-purpose Betfair historical archive already
on Fraser's machine, already linked to match results, but zero live
production wiring. No other sport has any data at all.

**3. Research-area classification.** Complete: `EXHAUSTED_VS_OPEN_RESEARCH.md`.
Football 1X2 probability modelling: EXHAUSTED (Gate 1, §15). Football 1X2
money-qualification backtesting (frozen V1): EXHAUSTED for the current data
(Backtest Phase 1, §22, independently reverified in Phase 2, §23). Tennis
market-inefficiency/edge-hunting: EXHAUSTED (Workstream B, 13-for-13
REJECT, formally closed). Tennis as a money-qualification question:
PARTIALLY EXPLORED -- the data exists and is linked, but this specific
question (consensus-as-probability, Phase-1-style) was never asked of it.
Football BTTS, football team totals, other Odds-API sports: UNEXPLORED.
Football OU2.5/AH money-qualification backtesting: BLOCKED BY DATA (current
free historical source measured insufficient).

**4. Priority candidate market families evaluated.** Football O/U2.5,
Football Asian Handicap, BTTS, team totals, richer football data, Tennis,
other Odds-API sports -- all evaluated in `MARKET_COVERAGE_MATRIX.csv` and
`MARKET_PRIORITY_SCORECARD.md`. Tennis money-qualification and football
OU2.5/AH acquisition are the two evidence-supported candidates; BTTS, team
totals, basketball are UNEXPLORED (no evidence either way, not
recommended yet); Cricket remains BLOCKED by standing policy (§14).

**5. Exact data requirements defined per market.** Tennis
money-qualification: match-level Betfair MATCH_ODDS last-traded-price
history + linked TML results (already have both, already linked at
88.96%). Football OU2.5/AH backtesting: a source with >=3 bookmakers
quoting each line per match, historically, for E0/E1/SC0 2020/21-2025/26
(not yet confirmed to exist even in the Betfair candidate -- see point 8).

**6. Historical odds source investigation, FREE -> LOW-COST -> PAID.**
Complete: `HISTORICAL_SOURCE_AUDIT.md`. No purchase made or recommended.
Top FREE candidate for football OU2.5/AH: Betfair Historical Data BASIC
tier for Soccer (`eventTypeId: 1`) -- same source, same account, same
process already proven for tennis. No LOW-COST or PAID source was
identified as necessary at this stage (see point 8's caveat and
`DATA_ACQUISITION_PLAN.md`'s TIER 2/3 sections, both left empty
pending confirmation TIER 1 is actually insufficient).

**7. Live compatibility with The Odds API audited, without unnecessary
live requests.** Complete: `LIVE_MARKET_COMPATIBILITY.md`. Football OU2.5
already live and operational since 2026-09-19. Football AH and BTTS have
documented Odds-API market keys not yet wired (small extension, not a new
integration). Tennis and basketball have no wiring at all but plausible
sport_key support per The Odds API's public documentation. No live API
calls were spent confirming this -- all conclusions come from existing
documentation and code inspection, as instructed.

**8. Market-priority scorecard built, evidence-based categories only.**
Complete: `MARKET_PRIORITY_SCORECARD.md`. STRONG: Tennis
money-qualification backtest (zero new acquisition needed). MODERATE:
Football OU2.5/AH via the Betfair archive (free and plausible, but
**explicitly unconfirmed** whether the BASIC tier's free coverage actually
includes OU2.5/AH-equivalent lines for football -- Betfair's own
documentation says historic data covers "nearly all markets... since 2016"
but does not confirm this at the individual-market level without an
account login). WEAK: BTTS, team totals, tennis live wiring, basketball
(all UNEXPLORED, not BLOCKED). BLOCKED: Cricket (policy).

**9. Explicit confirmation: market consensus itself may remain the best
estimator for any newly explored market, and that is an acceptable
outcome.** No market family in this document is assumed to need or produce
a beatable inefficiency. Both candidate next questions (Tennis
money-qualification, Football OU2.5/AH) are framed exactly like Backtest
Phase 1 was: does a trustworthy consensus probability, compared honestly
against available prices, produce qualifying value under the existing
gates? Not: can we beat the market?

**10. Staged TIER 1/2/3 acquisition plan.** Complete:
`DATA_ACQUISITION_PLAN.md`. TIER 1 (free, mostly already in hand): the
existing tennis Betfair archive (zero new action), a football-Betfair
BASIC-tier download (same free process, one new download if Fraser
chooses), and continued live data collection (already running). TIER 2 and
TIER 3: both intentionally empty -- no low-cost or paid need has been
identified yet.

**11. ONE primary next research cycle nominated, based on evidence.**
**Primary recommendation: Tennis Match Winner money-qualification
backtest**, using the already-downloaded, already-linked Betfair archive
and a Phase-1-style frozen-strategy replay harness adapted to tennis. This
is the only candidate needing zero new data acquisition, zero purchase
decision, and zero unconfirmed assumption about data coverage -- every
prerequisite is already satisfied and already evidenced in this repo.
**Strong parallel/secondary candidate**: Football OU2.5/AH via the Betfair
historical archive (Decision Option B, point 22) -- free and low-effort,
but gated on Fraser choosing to spend the time re-running his own download
process and on confirming the resulting data actually contains usable
OU2.5/AH coverage before any backtest design work begins on it.

**12. Since free/existing data is adequate for the primary nomination
(Tennis), the correct next step per the instruction is: create canonical
dataset, data audit, leakage audit, and pre-registered plan for that
question -- then STOP and report, not hypothesis-mine.** This checkpoint
recommends but does NOT perform that next-stage work: no new dataset was
canonicalised, no leakage audit was written for a tennis money-qualification
backtest, and no pre-registration was drafted in this phase. That is
correctly sequenced as the actual next research cycle, pending Fraser's
go-ahead, not folded into this audit/decision phase.

**13. Minimum CLV data requirements designed, not fabricated.** Complete:
`DATA_ACQUISITION_PLAN.md` Section 13 note. A timestamped placement-time
price and a timestamped closing-price snapshot from the same venue/
selection, both captured automatically, are the minimum; neither exists
yet for live-scanned data (see point 14/15), and no CLV number is claimed
or estimated anywhere in this phase's documents.

**14/15. Live paper archive audited for whether it can gradually solve
historical-data limitations, and additive fields to start archiving now
identified.** Complete: `LIVE_DATA_PRESERVATION_PLAN.md` -- this directly
answers Fraser's own stated priority question. Concrete finding: the full
per-bookmaker odds panel The Odds API already returns every scan (20+
bookmakers for EPL alone, each with price/point/last_update) is parsed in
memory (`ParsedEvent`/`ParsedBookmaker`/`ParsedMarket`/`ParsedOutcome`) but
never persisted -- only the reduced consensus/best-price `MarketRecord`
survives. Recommendation (not yet implemented): persist the raw
per-bookmaker panel verbatim every scan, add a genuine near-kickoff
closing-price snapshot distinct from the scan-time snapshot, keep the full
raw parsed response for insurance against schema gaps, and retain
bookmaker-panel composition over time. Zero new API cost; small new storage
and an additive, off-by-default-style implementation if approved. **Not
implemented this session** -- described only, per Section 14's "describe
first" instruction.

**16. Cross-market diversification preference over threshold-loosening.**
Affirmed: nothing in this phase recommends loosening any money-qualification
threshold to manufacture bets in football 1X2 or OU2.5. Every candidate
above is a genuinely new market/question, not a retuning of an already-
answered one.

**17. Multis and auto-execution kept explicitly out of scope.** Confirmed:
no multi-leg correlation analysis and no execution-automation design appear
anywhere in this phase's documents.

**18. Research output package produced under `research/data_expansion/`.**
Complete: `EXISTING_DATA_INVENTORY.md`, `MARKET_COVERAGE_MATRIX.csv`,
`EXHAUSTED_VS_OPEN_RESEARCH.md`, `HISTORICAL_SOURCE_AUDIT.md`,
`LIVE_MARKET_COMPATIBILITY.md`, `MARKET_PRIORITY_SCORECARD.md`,
`DATA_ACQUISITION_PLAN.md`, `LIVE_DATA_PRESERVATION_PLAN.md`, and this
document.

**19. This phase stayed an audit/decision phase, not a large build.** No
new modelling code, no new ingestion adapter, no new persistence layer was
written. The only repo changes in this phase are the eight new documents
plus this checkpoint -- no `src/`, `decisions/`, `config/`, or workflow file
was touched.

**20. Production betting logic was not modified.** Confirmed by the test
run in point 21 and by direct review: no file under `decisions/`,
`scripts/run_daily_scan.py`, `config/thresholds.yaml`,
`config/bankroll.yaml`, `storage/schemas.py`, or any GitHub Actions
workflow was changed in this phase.

**21. Full existing test suite run before completion.** `940/940 passing`
(unchanged from Phase 2, §23 -- confirmed by rerun this session, not
assumed carried over). No test was added, removed, or modified in this
phase, consistent with it being a pure-documentation phase.

**22. Decision option selected: A -- start next research cycle using
existing/free data.** Specifically: Tennis Match Winner money-qualification
backtest (point 11), for which existing/free data is already fully
adequate. Decision Option B (acquire a specific low-cost dataset first) is
named as a credible parallel path for football OU2.5/AH but is not the
primary recommendation, because its data sufficiency is unconfirmed while
Tennis's is already confirmed. Decision Option C (continue live collection
before next cycle) is already happening in parallel regardless of which
cycle is chosen, per point 14/15's ongoing recommendation. Decision Options
D (different sport family) and E (data insufficient, don't force research)
were considered and rejected as the primary path: D is effectively what
Tennis and football-OU2.5/AH already represent, and E does not apply --
usable, adequate free data does exist for at least one genuinely open
question (Tennis).

**23. No purchase or download of paid data occurred or is recommended as
an immediate action.** Every acquisition item in `DATA_ACQUISITION_PLAN.md`'s
TIER 1 is free; TIER 2/3 are explicitly left empty pending further evidence.
This checkpoint is being brought to Fraser before any purchase decision,
exactly as instructed.

**24. Nothing was silently deleted or overwritten; superseded objectives
remain marked, not removed.** This phase added new documents only; no
existing document (including the master research directive's own §1-§23
history) was altered by this phase (the directive's own §24 entry,
summarising this phase, is added separately via `project_write`, following
the same append-only discipline used for §14-§23).

**25. Explicit summary for Fraser: nothing has been bought or downloaded.**
The recommended next action, if approved, is to begin a new pre-registered
research cycle -- **Tennis Match Winner money-qualification backtest** --
using data Fraser already has, adapting the existing Backtest Phase 1
harness. A free, optional, parallel action Fraser could also take at his
own pace: repeat his own Betfair historical-data download process, filtered
to Soccer, to test whether it resolves the football OU2.5/AH bookmaker-
depth gap -- not required before Tennis work can start, and not a purchase
either way. Separately, and independent of which research cycle is chosen,
this checkpoint recommends beginning to archive the raw per-bookmaker odds
panel from the live daily scanner starting now (point 14/15) -- every day
this is deferred is real, free, timestamped market data that cannot be
reconstructed retroactively. No production change has been made toward
that recommendation; it awaits Fraser's explicit approval.

**Git status.** All Phase 3 files are new, untracked additions under
`research/data_expansion/`. Not yet committed -- committing (with the
required attribution footer) and updating the master research directive
project doc with a new §24 are the two remaining steps after this
checkpoint is delivered, both to follow immediately.
