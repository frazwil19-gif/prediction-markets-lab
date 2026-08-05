# Cycle 1 — Data Feasibility Decisions

Reassessment of the four football hypotheses recommended for Cycle 1
(project instructions Part 4), based **only** on confirmed data
availability from the Stage 3A acquisition work — not on any outcome
or profitability signal.

## 1. Popular favourites may be overpriced in high-profile matches (H-FB-001)

**TESTABLE_WITH_PROXY.** Football-Data has no direct measure of match
"popularity" or profile. A proxy must be defined and pre-registered
before any testing begins (per `docs/RESEARCH_ENGINE.md` — defining
the test after seeing results is not allowed). Candidate proxies,
to be decided in Stage 3B before backtesting:

- Competition tier (Premier League > Championship > Scottish
  Premiership) as a coarse popularity proxy.
- Bookmaker count itself (more bookmakers quoting may correlate with
  more public attention) — though this risks circularity, since
  bookmaker count also feeds the consensus estimate; if used, it must
  be from a period before the match, not contaminate the consensus
  used for grading the same match.

## 2. Large bookmaker disagreement may predict greater model uncertainty (H-FB-002)

**TESTABLE_AS_DEFINED.** Both opening and closing per-bookmaker prices
are confirmed present with genuine multi-bookmaker coverage (6
bookmakers per match in the acquired sample — see
`reports/audits/football_bookmaker_coverage.csv`). IQR/standard
deviation of fair probabilities across bookmakers
(`probability.consensus.ConsensusResult`) is already computed by the
existing pipeline. No new data is required.

## 3. Exchange prices materially above margin-free consensus may identify candidate value (H-FB-003 in the registry)

**NOT TESTABLE from Football-Data.co.uk alone — confirmed, unchanged
from the original feasibility audit.** This source has no exchange
price history (Smarkets/Betfair) at all, historical or otherwise, and
even its bookmaker prices are two static snapshots (opening, closing)
rather than a time series. This hypothesis requires either a paid
exchange-history data source (out of budget per project constraints)
or forward data collection starting now (recording live exchange
prices going forward, which only produces evidence retroactively as
time passes). Remains `DATA_REQUIRED`.

## 4. Short-rest or schedule-congestion effects may be incompletely priced (H-FB-004 recommended set item)

**TESTABLE_AS_DEFINED,** contingent on multi-season chronological
coverage (needed to compute each team's rest days between its own
fixtures — a single season's opening weeks have no "previous match"
within that season to measure rest from, so this hypothesis benefits
particularly from acquiring the full 5-season window rather than a
single season). Match dates are complete and well-formed in every row
inspected so far (`reports/audits/football_data_schema_inventory.csv`
shows 0% null rate on the `Date` column in the sample). No new data
source is required; a rest-day feature is a straightforward derived
field from already-available fixture dates once multi-season data is
loaded chronologically.

## Summary decision for Cycle 1

Of the four hypotheses recommended for Cycle 1 in the task prompt, two
map cleanly onto the confirmed data (#2 bookmaker disagreement, #4
short-rest/congestion), one is testable only via an explicitly-defined
proxy that must be pre-registered before testing (#1 popular-favourite
overpricing), and one is not testable from this data source at all and
must be replaced or deferred (#3 exchange-price value — already
flagged as H-FB-003 = `DATA_REQUIRED` in the Hypothesis Registry).

**Recommendation for Stage 3B:** proceed with H-FB-002 (bookmaker
disagreement) and H-FB-004-equivalent (short-rest/congestion) as the
two hypotheses with the cleanest data support; treat H-FB-001
(popularity proxy) as testable only after the proxy is formally
defined in a Cycle 1 addendum; leave the exchange-value hypothesis
excluded from Cycle 1 entirely.
