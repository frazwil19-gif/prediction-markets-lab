# Staged Data Acquisition Plan -- Phase 3, Sections 10 & 13

Date: 2026-09-22. Staged TIER 1 (free/already-have) -> TIER 2 (low-cost) ->
TIER 3 (paid, only if justified) plan. Per explicit instruction: nothing in
this document is a purchase or a download action -- it is a plan for Fraser
and ChatGPT to decide on. No paid data has been bought, downloaded, or
requested; no API keys are exposed anywhere in this document.

## TIER 1 -- free, and in most cases already in hand

**1a. Tennis Betfair Historical Data (already downloaded, zero new action
needed).** `Downloads/tennis data/data.tar` (4.17 GB, 996,779 files) and
`Downloads/BASIC/2026/` (746 MB, ~28,500 event folders) are already on
Fraser's machine and already partially ingested (12,956/14,564 matches
linked). Cost: £0, and no further acquisition step exists -- this tier item
is "use what is already here," not "go get something." This is the
resource behind the STRONG-rated Tennis money-qualification backtest in
`MARKET_PRIORITY_SCORECARD.md`.

**1b. Football Betfair Historical Data, BASIC tier, filtered to Soccer
(`eventTypeId: 1`).** Same source, same account, same free tier, same
process Fraser has already successfully completed once for tennis (per
`TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md`, 2026-09-15). Cost: £0 (subject to
the jurisdiction restriction already confirmed unchanged this session:
Betfair.com registration, excluding Brazil/Italy/Spain/Romania/Sweden).
Action, if Fraser chooses to pursue this: repeat the existing
account/download steps on Betfair's historic data site, filtered to Soccer
instead of Tennis, for the same date range already covered by
football-data.co.uk (2020/21-2025/26) so the two sources can eventually be
cross-referenced. This is the acquisition step behind the MODERATE-rated
football OU2.5/AH backtest candidate -- genuinely free, but its payoff is
unconfirmed until downloaded and checked for OU2.5/AH-equivalent market
coverage (Betfair's own documentation says its historic data covers
"nearly all markets... since 2016" but does not confirm this at the
individual-market-type level without an account login, an honest caveat
already flagged in `HISTORICAL_SOURCE_AUDIT.md`).

**1c. Continued live data collection (no acquisition, time-based).** The
daily scan already running since 2026-09-20 continues to accumulate
real, timestamped 1X2 and OU2.5 market data for free, every day it runs.
This is not a discrete acquisition step but an ongoing, zero-cost data
asset that directly addresses both the money-event-horizon gate's
untestability (needs real intraday timestamped prices, per §22) and part
of the CLV-data gap (see `LIVE_DATA_PRESERVATION_PLAN.md` below).

**TIER 1 total cost: £0. No purchase, no new account beyond one Fraser
already has, no key exposure.**

## TIER 2 -- low-cost, not yet identified as necessary

No specific low-cost (i.e., small paid fee, not free) data source has been
identified as necessary for any of the currently-open research questions.
Every candidate market examined in this phase (Tennis money-qualification,
Football OU2.5/AH) has a plausible free (TIER 1) path; TIER 2 is left
empty rather than populated with a speculative purchase recommendation.
If TIER 1's football-Betfair download (1b) turns out NOT to contain usable
OU2.5/AH coverage, the next evidence-based step would be to name a specific
low-cost OU2.5/AH historical odds provider and return its
provider/cost/coverage details here for a decision -- not to buy it
pre-emptively now.

## TIER 3 -- paid, only if a specific justified need is identified

No paid dataset is recommended in this phase. Per the master directive's
standing cost constraint (§11: "No paid API/dataset unless free sources are
exhausted, the missing information has a specific expected research value,
and that value can be articulated in advance") and Fraser's own explicit
instruction for this phase ("do NOT purchase anything"), this tier is
intentionally left as a placeholder. If TIER 1 and TIER 2 are both
exhausted for a specific market (most plausibly football OU2.5/AH, if the
Betfair BASIC tier proves insufficient), the correct next step is to name
candidate paid providers, their cost, and their coverage here, and bring
that back to Fraser/ChatGPT for an explicit purchase decision -- never to
buy autonomously.

## Section 13 note -- minimum CLV data requirements (designed, not fabricated)

To eventually compute genuine (not proxy) CLV, the minimum requirement is:
a timestamped price at bet-placement time, and a timestamped closing price
from the same venue for the same selection, both captured automatically
(not reconstructed after the fact). The existing live scanner already
captures a scan-time snapshot (via The Odds API) but, per the finding in
`EXISTING_DATA_INVENTORY.md` and detailed in `LIVE_DATA_PRESERVATION_PLAN.md`
below, does not yet capture or persist a genuine closing-price snapshot for
the same fixtures -- that is the concrete gap a CLV-data design must close,
and it is addressed as a live-archiving recommendation, not as a data
purchase, since it can be captured for free by the system already running.
No CLV figures are fabricated or estimated in this document -- this section
only defines what would need to exist before true CLV could be computed at
all.
