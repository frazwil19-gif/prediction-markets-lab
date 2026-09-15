# Tennis Historical Odds Source Audit (Workstream B)

**Status: IN PROGRESS -- first pass, 2026-09-15.** This is a systematic search
for a replacement historical ATP pre-match odds source (2021-2025), following
tennis-data.co.uk's confirmed server-side failure (see
`research/cycles/CYCLE_002_TENNIS/PLAN.md`, diagnostic runs #6-#8).

**Methodology and an important limitation, stated up front**: every
candidate below was checked against real fetched content (web search +
page/API fetches from this environment), not assumed from a name or
description. However, this pass could NOT download or inspect actual row-level
data for any candidate -- Kaggle's dataset pages are JavaScript-rendered and
did not return usable metadata to an automated fetch, and pulling real files
from Kaggle, Betfair, or Pinnacle requires an authenticated account, which is
Fraser's to create, not something done from here. So nothing below is marked
PREFERRED or USABLE on the strength of this pass alone -- every non-rejected
candidate needs a real download-and-inspect step, ideally by Fraser directly,
before being wired into acquisition. This audit's job is to narrow the field
honestly, not to declare victory prematurely.

## Candidates

### 1. Betfair Historical Data (historicdata.betfair.com / Historical Stream API)
**Verdict: USABLE (pending account verification) -- current best lead.**

- What it is: Betfair's own official historical exchange data service,
  covering "all the historical Stream API data since 2016" across multiple
  sports including tennis (per Betfair's own "How to model" education page,
  betfair.com.au/hub/education/how-to-model/historical-data-sources/).
- Format: compressed JSON, delivered as `.tar` files; a companion Python
  library (`betfair-data` on PyPI, Rust-backed) exists specifically to parse
  this format (bz2/gzip/tar/zip, JSON stream files) into structured data --
  this is a real, maintained parsing path, not something we'd build from
  scratch.
- Access: requires being a "registered Betfair customer" (per Betfair's own
  developer support article on downloading historical data). A free tier
  exists at 1-minute odds-interval granularity; finer granularity (1-second,
  50ms -- "Advanced"/"Pro" tiers) is paid. The support article also describes
  it as data "for purchase & download," which may mean the free tier is
  more limited than the Hub education page implies -- this needs resolving
  by actually registering and looking at the historical-data site's real
  options, not by assuming either description is complete.
- Why this is promising beyond just "a replacement for tennis-data.co.uk":
  it's real exchange price data (money actually traded), not just a
  bookmaker's posted price -- arguably a better basis for "P implied by
  obtainable market price after margin/costs" than a single bookmaker
  snapshot, and it supports genuine opening-vs-closing-price (CLV) analysis
  since it's a continuous stream, not one point-in-time file.
- Open questions / caveats found, not resolved: a Betfair community forum
  thread title ("ATP Tennis rights starting 2024") surfaced in search
  suggesting some kind of broadcast/market-rights change affecting ATP
  tennis on Betfair around 2024 -- the actual thread 404'd when fetched, so
  this is an unconfirmed lead, not a finding; it needs checking directly
  (e.g. on the Betfair/Bet Angel forums) before assuming full 2021-2025 ATP
  coverage is intact. Also unconfirmed: real liquidity/market depth for
  lower-tier ATP events (Challengers, early rounds of smaller 250s) -- exchange
  volume is not guaranteed to be even across the tour the way a bookmaker's
  posted price is.
- Next step (needs Fraser, not automatable from here): register a free
  Betfair account, visit historicdata.betfair.com directly (it's a
  JavaScript app that doesn't render via automated fetch), and check real
  ATP tennis coverage/pricing for the free tier before any acquisition code
  is written against it.

### 2. tennis-data.co.uk (existing source)
**Verdict: INACCESSIBLE.** Confirmed server-side broken across three
independent real clients (GitHub Actions, a separate web-fetch tool, and a
real Chrome browser) -- see PLAN.md diagnostic runs #6-#8. Not re-litigated
here; kept configured as optional in the pipeline in case it recovers.

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
**Verdict: UNVERIFIED -- likely stale, needs manual check.**
Previously flagged (2026-09-15 diagnostic notes) as a candidate; this pass
could only retrieve the dataset's page metadata, not its real contents. The
one date visible (a 2019-05-02 image timestamp) is a weak signal the
dataset itself may be from around 2019, not maintained through 2025, but
this is not confirmed -- Kaggle dataset "last updated" dates aren't
reliably exposed to an unauthenticated fetch. Needs a real login-and-download
check.

### 6. edoardoba/atp-tennis-data (Kaggle)
**Verdict: UNVERIFIED -- needs manual check.**
Description confirms it includes ATP results with bookmaker odds, but
years covered, source, and last-updated date could not be retrieved from
an unauthenticated fetch of Kaggle's JS-rendered page. Needs a real
login-and-download check.

### 7. ehallmar/a-large-tennis-dataset-for-atp-and-itf-betting (Kaggle)
**Verdict: INACCESSIBLE (this pass).**
The URL surfaced by search returned a 404 on fetch -- either the slug has
changed or the dataset was removed/renamed. Needs a fresh search directly
on Kaggle rather than via a general web search engine's cached link.

### 8. aigeon-ai/pinnacle-odds (GitHub)
**Verdict: LIMITED / UNVERIFIED.**
This is an API wrapper/MCP server for Pinnacle's odds feed (real-time and
"historical" per its own description), not a static historical archive --
practically, it means live-fetching Pinnacle's API on some cadence going
forward would build a history, not that 2021-2025 history already exists
somewhere ready to download. Whether Pinnacle's underlying API actually
exposes multi-year backfill (vs. only recent history) is unconfirmed, and
likely has a cost. Lower priority than Betfair unless Betfair falls through.

### 9. Pinnacle Data API (api.bettingiscool.com) / `pinnacle.data` R package (CRAN)
**Verdict: UNVERIFIED -- not yet investigated in depth.**
Surfaced by search as "years of sharp odds data" from Pinnacle; the CRAN
package name suggests a real, historically-oriented Pinnacle odds dataset
exists in some form. Not yet checked for tennis coverage, cost, or years
available -- flagged for a follow-up pass if Betfair's account-gated
verification doesn't pan out.

## Summary and recommendation

No candidate can be marked PREFERRED yet without an actual authenticated
download-and-inspect step, which is not something this environment can do on
its own (Kaggle/Betfair/Pinnacle all require real account credentials).
**Betfair's official Historical Stream API is the strongest lead**: it's an
official, well-documented, currently-maintained source that explicitly
covers tennis since 2016, has a free tier, and would give us real exchange
prices (arguably a scientifically better benchmark than a single bookmaker's
posted odds). It requires Fraser to register a free Betfair account and
check the real historicdata.betfair.com site directly, since that page is a
JavaScript app this environment cannot render or verify remotely.

Two Kaggle candidates (`hakeem/atp-and-wta-tennis-data`,
`edoardoba/atp-tennis-data`) remain open but unverified pending a real
Kaggle login; both GitHub-static-mirror candidates checked so far
(`0xsimulacra/MLT`, `maxfar/tennis-data`) are rejected outright for stale
coverage that stops years before our study window.

**This workstream is not complete.** Per the operating instructions, it
continues rather than stopping at this partial result -- the honest status
is PRICE DATA SEARCH IN PROGRESS, not PRICE DATA BLOCKED and not PRICE DATA
FOUND.
