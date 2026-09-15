# Tennis Historical Odds Source Audit (Workstream B)

**Status: IN PROGRESS -- Pass 2, 2026-09-15.** This is a systematic search
for a replacement historical ATP pre-match odds source (2021-2025), following
tennis-data.co.uk's confirmed server-side failure (see
`research/cycles/CYCLE_002_TENNIS/PLAN.md`, diagnostic runs #6-#8). Pass 1
(also 2026-09-15, see git history for the original version of this file)
did a first web-search pass without deep verification of tier/pricing/rights
detail; Pass 2 goes deeper on Betfair's actual documented tiers, jurisdiction
restrictions and account process, definitively resolves the Pinnacle CRAN
package (rejected), and adds two new commercial candidates that were not in
Pass 1's search.

**Methodology and an important limitation, stated up front**: every
candidate below was checked against real fetched content (web search +
page/API fetches from this environment), not assumed from a name or
description. This pass still could NOT download or inspect actual row-level
data for any candidate that requires a login (Kaggle, Betfair) -- that step
is Fraser's to do, not something done from here. So nothing below is marked
fully USABLE on the strength of this pass alone -- every account-gated
candidate still needs a real download-and-inspect step before being wired
into acquisition. This audit's job is to narrow the field honestly, not to
declare victory prematurely.

## Candidates

### 1. Betfair Historical Data (historicdata.betfair.com / Historical Stream API)
**Verdict: LIKELY USABLE -- PENDING ACCOUNT-ONLY ACTION. Current top priority, unchanged from Pass 1, now with concrete tier/process detail.**

- **Tiers (confirmed via official Betfair developer docs + the Betfair-affiliated
  Automation Hub tutorial):** three packages exist -- **BASIC** (free),
  **ADVANCED** (paid), **PRO** (paid).
  - BASIC: 1-minute odds intervals, **last-traded-price only, no volume**, no
    price-ladder depth.
  - ADVANCED: ~1-second intervals, top-3 price ladder + volume.
  - PRO: tick-level (~50ms) intervals, full price ladder + volume.
  - **For this cycle's initial benchmarking goal (a single closing/consensus
    price to compare model probabilities against), BASIC is sufficient --
    do not pay for ADVANCED/PRO yet.**
- **Match Odds market coverage:** official docs list "Tennis Game Betting"
  (in-play, game-level markets) as the only tennis exclusion from Historical
  Data -- Match Odds (== Match Winner, the market this project needs) is not
  excluded, so by elimination it should be included. Not a direct "yes"
  statement from Betfair, but the strongest evidence available without an
  account.
- **Traded volume:** confirmed tiered -- the free BASIC tier is
  last-traded-price snapshots only, with **no traded/available volume data**;
  full volume history needs a paid tier. This limits (but does not block)
  CLV-style analysis on the free tier -- a single last-traded price per
  minute is still usable as a market-consensus benchmark, just not as rich
  as a full order-book reconstruction.
- **File format:** `.tar` archives containing per-market `.bz2`-compressed
  JSON stream files (one file per marketId), matching the live Exchange
  Stream API's JSON format. The community `betfair-data` PyPI package
  (Rust-backed, actively maintained) parses this into structured Python
  objects -- a real, maintained parsing path, not something to build from
  scratch.
- **Player-name matchability to TML-Database: STILL UNVERIFIED.** Whether
  Betfair's JSON "runner" (player) names come as clean, directly-matchable
  "Firstname Lastname" strings, or need cleaning/fuzzy-matching against
  TML-Database's own name conventions, cannot be confirmed without an actual
  sample file -- budget time for a name-matching pass (the project's
  existing player-name matcher from Checkpoint 2, commit `9492a90`, may be
  directly reusable here) once real data is in hand.
- **2024/2025 ATP coverage -- rights-change question, still not fully
  resolved:** A real, officially-confirmed rights change exists but is
  UNRELATED to Betfair: Sportradar (via Tennis Data Innovations) won the
  global ATP Tour + Challenger *official live-scoring/data-feed* rights for
  a 6-year cycle starting 1 January 2024. This is a bookmaker data-feed deal,
  not an exchange-market-listing deal, and no source (official or
  forum/news) found in this pass states Betfair lost the ability to list ATP
  Match Odds markets, or that Betfair's historical ATP archive has a gap in
  2024/2025. One open thread remains: a Betfair-adjacent forum
  (forum.betangel.com) has a thread literally titled "ATP Tennis rights
  starting 2024," which could not be fetched (404 to automated tools, and
  archive.org was blocked) -- **this is the one remaining thing worth
  Fraser eyeballing himself** (he can log into that forum directly) before
  treating 2024-2025 ATP coverage as fully confirmed. Official docs do
  confirm tennis has its own dedicated Historical Data package (distinct
  from "Other Sports"), which is a mild positive signal for continued
  dedicated coverage.
- **Jurisdiction restriction (new finding, Pass 2):** Betfair's own docs
  confirm Historical Data is for **"Betfair.com customers only"** and is
  explicitly blocked for customers registered in **Brazil, Italy, Spain,
  Romania, and Sweden**. Fraser should confirm his registration country
  isn't one of these before proceeding (very likely fine for a UK-based
  user, but stated here for completeness).
- **Exact account/registration process, for Fraser to do himself (precise,
  minimal steps -- this is the one manual action this project cannot do on
  its own):**
  1. Create a standard Betfair.com betting account at
     `register.betfair.com/account/registration` (or via betfair.com's normal
     signup) if he doesn't already have one -- there is no separate
     "historical data account" type.
  2. Complete whatever identity verification (KYC) Betfair's normal signup
     requires -- this is the actual "account creation" step; nothing about it
     is automatable or should be attempted from this environment.
  3. Once the account exists, log in directly at `historicdata.betfair.com`
     with the same Betfair username/password -- no separate application or
     approval step is documented.
  4. Filter by sport = Tennis, select date ranges 2021-2025, and choose the
     **BASIC (free)** package for Match Odds market data.
  5. **Do not purchase ADVANCED or PRO**, and do not fund/deposit money beyond
     whatever the account signup itself requires -- the paid tiers are not
     needed for this cycle's initial benchmarking goal.
  6. Exact £/$ pricing for anything beyond BASIC lives inside the
     JavaScript-only historicdata.betfair.com portal and could not be read
     from outside a logged-in session -- Fraser will see it once logged in,
     but again, BASIC should need no payment at all.

### 2. tennis-data.co.uk (existing source)
**Verdict: INACCESSIBLE.** Confirmed server-side broken across three
independent real clients (GitHub Actions, a separate web-fetch tool, and a
real Chrome browser) -- see PLAN.md diagnostic runs #6-#8. Not re-tested in
Pass 2 per the operating instructions (not our job to keep re-litigating an
already-confirmed dead source); kept configured as optional in the pipeline
in case it recovers.

### 3. 0xsimulacra/MLT (GitHub)
**Verdict: REJECTED.**
Its own README states plainly: "The Data is scraped from
http://www.tennis-data.co.uk." Coverage is 2000-2019 (ATP) / 2007-2019 (WTA)
-- a static, unmaintained mirror that stops six years before our study
window starts and is literally sourced from the site we're trying to
replace. No path to 2021-2025 data here.

### 4. maxfar/tennis-data (GitHub)
**Verdict: REJECTED.**
Verified via GitHub's own contents API: annual CSV files present for
2001-2014 only. Stale, doesn't reach anywhere near 2021-2025.

### 5. hakeem/atp-and-wta-tennis-data (Kaggle)
**Verdict: STILL UNVERIFIED -- likely stale, needs manual check.**
Pass 2 could still only retrieve page metadata, not real contents (Kaggle's
dataset pages remain a JS-rendered SPA to unauthenticated fetches). A cached
page fragment showed a card image referencing 2019-05-02, a weak (not
confirmed) signal the dataset may predate the 2021-2025 study window. Needs
a real login-and-download check by Fraser if pursued.

### 6. edoardoba/atp-tennis-data (Kaggle)
**Verdict: STILL UNVERIFIED -- needs manual check.**
Description confirms ATP results with bookmaker odds are included, but
years covered, source, and last-updated date remain unconfirmed without a
real login-and-download check.

### 7. ehallmar/a-large-tennis-dataset-for-atp-and-itf-betting (Kaggle)
**Verdict: INACCESSIBLE (both passes).**
The URL surfaced by search returned a 404 on fetch in Pass 1; not
re-surfaced in Pass 2 either. Needs a fresh search directly on Kaggle rather
than via a general web search engine's cached link, if pursued further.

### 8. dissfya/atp-tennis-2000-2023daily-pull (Kaggle) -- NEW, found in Pass 2
**Verdict: STILL UNVERIFIED.**
Title states range "2000-2026" with "daily-pull" in the slug, suggesting
active maintenance through the present -- a better recency signal than
candidates 5/6. However, the title emphasizes match results, and
odds/price inclusion could not be confirmed from public metadata alone.
Worth a real login-and-check if Betfair falls through.

### 9. aigeon-ai/pinnacle-odds (GitHub)
**Verdict: REJECTED for this purpose (downgraded from Pass 1's "limited/unverified" after closer inspection).**
Confirmed in Pass 2: this is an MCP server / live API wrapper around
Pinnacle's real-time odds API (tools like "Historical Data," "List of
Archive Events," "Odds History" are live calls against Pinnacle's own
servers, requiring a Pinnacle API account). No stated date-range boundary
for how far its "historical" calls actually reach, and it is not a static,
downloadable bulk archive. Not the right shape of tool for building a fixed
2021-2025 dataset.

### 10. Pinnacle Data API (api.bettingiscool.com) / `pinnacle.data` R package (CRAN)
**Verdict: REJECTED (resolved in Pass 2 -- was unverified in Pass 1).**
Directly inspected the CRAN mirror and its GitHub source
(`marcoblume/pinnacle.data`): the package contains exactly two datasets --
`MLB2016` (2016 MLB odds) and `USA_Election_2016` (2016 US election odds).
**No tennis data of any kind.** Appears to be a single-commit, unmaintained
2016 demo package. Definitively rejected, not merely unverified.

### 11. BigDataBall -- ATP & WTA Tennis Data (bigdataball.com) -- NEW, found in Pass 2
**Verdict: LIKELY USABLE -- cheap, no-account-required commercial fallback.**
Confirmed via the public pricing page: sells year-by-year Excel datasets
(match-by-match and set-by-set) with opening and closing moneyline odds from
real bookmakers, covering ATP & WTA tour-level and Grand Slam matches
through 2025 (Challenger-level excluded, which doesn't matter for this
project's tour-level scope). Priced at **$30/season** (bundle discounts
available); "Add to cart" works without login -- only a discount requires a
free account, not the purchase itself. Column schema and player-name format
were not independently verified (would need to buy a sample). This is the
best-verified fallback if Betfair's account/coverage step doesn't pan out,
but it costs money, so it stays behind Betfair per the project's "free
first" ordering.

### 12. OddsWarehouse -- ATP Men's Tennis Historical Sports Betting Odds -- NEW, found in Pass 2
**Verdict: LIKELY USABLE -- cheap, no-account-required commercial fallback.**
Confirmed via the public product page: covers 2009-2025, one-time price
**$99** for the full database (or per-season), includes match dates,
locations, ATP rankings/points, and moneyline odds per player. Optional
weekly ($9) or monthly ($19) update subscriptions during the ATP season.
Whether the 2021-2025 window is exclusively tour-level (vs. mixing in lower
tiers) wasn't confirmed from the public page alone -- support offered to
email a sample on request. Second-tier fallback behind Betfair and
BigDataBall (BigDataBall is cheaper per season and already has a clearer
public pricing structure).

## Summary and recommendation

**Betfair's official Historical Stream API remains the correct top
priority**, now with a fully documented, precise account-creation path (see
candidate 1 above) that Fraser can follow directly. No credible evidence of
an ATP 2024/2025 coverage gap was found in either pass; the one open thread
(a Betfair-adjacent forum title mentioning "ATP Tennis rights starting
2024") is worth Fraser eyeballing directly since it 404's to automated
tools, but nothing else supports a coverage-gap hypothesis, and the one
confirmed 2024 rights change found (Sportradar's ATP data-feed deal) is
about bookmaker data feeds, not Betfair's own exchange listings.

Pinnacle is now **fully resolved and rejected** on both leads investigated
(the CRAN package has zero tennis data; the GitHub wrapper is a live-API
tool, not a bulk archive) -- Pinnacle is no longer an open thread for this
project. The three Kaggle candidates remain open but unverified pending a
real login; two new commercial fallbacks (BigDataBall at $30/season,
OddsWarehouse at $99 one-time) were found and are legitimate, low-cost,
no-account-creation options if the Betfair path stalls -- kept as
second-tier options, not a replacement for trying Betfair first.

**This workstream is not complete.** Per the operating instructions, it
continues rather than stopping at this partial result -- the honest status
is **PRICE DATA SEARCH IN PROGRESS, PENDING FRASER'S BETFAIR ACCOUNT
SIGNUP** -- not PRICE DATA BLOCKED and not PRICE DATA FOUND. Nothing further
is automatable on this thread from this environment until that account
exists; the next research-side action is picking up the Kaggle candidates
if Fraser wants a second opinion pursued in parallel.
