# Live Market Compatibility Audit -- Phase 3, Section 7

Date: 2026-09-22. Scope: for each candidate next market/sport (per
`MARKET_COVERAGE_MATRIX.csv`), does existing live infrastructure already
obtain the current data needed to run it, or is that a gap? Answered from
documentation and existing code/repo evidence only. No unnecessary live
Odds API requests were made to produce this document (none were needed --
every fact below is already recorded in prior sessions' checkpoints or is
directly readable from source).

## What already exists and is confirmed live

`ingestion/the_odds_api_loader.py` (built 2026-09-19, §18-19 of the master
directive) fetches The Odds API v4's `/v4/sports/{sport}/odds` endpoint for
three configured `sport_key` values (`soccer_epl` -> Premier League,
`soccer_efl_champ` -> Championship, `soccer_spl` -> Scottish Premiership),
requesting `markets=("h2h", "totals")`. It parses the response into
`ParsedEvent` (id, sport_key, commence_time, home_team, away_team,
bookmakers) -> `ParsedBookmaker` (key, title, last_update, markets) ->
`ParsedMarket` (key, outcomes) -> `ParsedOutcome` (name, price, point), then
reduces `h2h` into 1X2 selections and `totals` (filtered to the configured
`total_goals_line`, currently 2.5) into Over/Under selections, both in the
same canonical shape the manual CSV loader already produced. This has been
running live, unattended, via `.github/workflows/daily_scan.yml` (07:00 UTC
daily) since 2026-09-19, producing real `daily_cards/<date>/` output every
day through today (2026-09-22) with zero Claude-session involvement --
confirmed operational, not just built.

Documented credit economics (§18-19): ~2 credits per league per scan for
h2h+totals combined, 3 leagues configured -> ~6 credits/day, ~180/month,
comfortably inside The Odds API's 500-credit free tier. This was confirmed
against the account's own quota-usage headers during the 2026-09-19 live
smoke test, not just the published documentation.

## Per-candidate-market compatibility

**Football Over/Under 2.5** -- ALREADY LIVE. The `totals` market fetch and
canonicalisation described above already covers this exactly; the gap
Backtest Phase 1 (§22) identified is on the HISTORICAL side (too few
bookmakers quote OU2.5 in football-data.co.uk's archive to backtest it),
not the live side. No new live infrastructure would be needed to extend
Phase-1-style money-qualification testing to OU2.5 once historical depth is
solved -- the live scanner already produces real OU2.5 candidates every day
(one is already sitting in `paper_ledger/paper_bets.csv`, confirmed via
direct query this session: `Counter({'1x2': 21, 'over_under_2_5': 1})`).

**Football Asian Handicap** -- PARTIALLY LIVE, NOT WIRED. The Odds API v4
does offer an Asian Handicap-style `spreads` market for soccer (documented
in The Odds API's own market-key reference), but `the_odds_api_loader.py`
only requests `("h2h", "totals")` -- `spreads` is not fetched, parsed, or
wired into the canonical shape anywhere in the current codebase. Per §17,
this was already correctly identified as "not yet wired... needs exact-line
matching, a small follow-on, not a research question" -- that assessment is
unchanged. Wiring it would be a config/parsing extension of the existing,
working loader, not a new integration.

**Football BTTS (Both Teams To Score)** -- NOT LIVE, NOT WIRED. The Odds
API v4 does offer a `btts` market key for soccer per its documentation, but
it is not in the configured `markets` tuple and no canonicalisation path
for it exists in `the_odds_api_loader.py`. Same category of gap as Asian
Handicap: a plausible small extension of an already-working adapter, not a
new live-data source.

**Football team totals** -- NOT LIVE. No team-total market is fetched or
parsed. Would require both a live-source check (does The Odds API offer a
team-totals key for the configured leagues -- not confirmed here, would
need a documentation check before building) and new canonicalisation code.

**Tennis Match Winner** -- NOT LIVE, NO WIRING AT ALL. No tennis-specific
ingestion path exists anywhere in `src/prediction_markets_lab/ingestion/`.
The Odds API does list tennis `sport_key` values (e.g. `tennis_atp_...`,
`tennis_wta_...`) in its public sport-list documentation, so live tennis
odds are plausibly obtainable via the same adapter pattern already proven
for football -- but this is a documented capability of the API, not a
confirmed-working integration in this repo. Building it would follow the
exact precedent `the_odds_api_loader.py` already set (one adapter function,
one config block, one set of canonicalisation tests) rather than needing
new architecture.

**Basketball moneyline** -- NOT LIVE. Same status as tennis: The Odds API
publicly documents basketball `sport_key` values, but nothing in this repo
fetches, parses, or tests against them.

**Cricket match winner** -- NOT LIVE, and explicitly PAUSED per §14 of the
master directive ("Cricket stays PAUSED -- do not start acquisition or code
until the daily engine's V1 scope is approved and either resolves cleanly
or a fresh decision reopens Cricket specifically"). Not investigated
further here, consistent with that standing instruction.

## Net conclusion for Section 7

For the two live-compatibility questions that matter most to Sections 10-11
(what could move fastest): Football OU2.5 needs zero new live-adapter work
(already live) -- its only blocker is historical bookmaker depth for
backtesting. Football Asian Handicap and BTTS need a small, low-risk
extension of an already-proven adapter (add a market key, add
canonicalisation, add tests) -- not a new integration. Tennis and
basketball would need a new adapter built from scratch, following the same
pattern, with sport_key values that appear to exist in The Odds API's
documented catalogue but have never been fetched or tested against by this
codebase. No live API calls were made to verify sport_key availability for
tennis/basketball/BTTS/spreads beyond what The Odds API's own published
documentation already states -- confirming them for real would cost a small
number of credits and is a reasonable first step if either candidate is
chosen, not a blocker to this audit.
