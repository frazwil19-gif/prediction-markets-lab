# Phase 3, Section 3 -- Exhausted vs. Open Research Areas

**Written 2026-09-22.**

## EXHAUSTED FOR CURRENT INFORMATION SET

**Football 1X2 probability modelling (beating or complementing market consensus).** Gate 1
(2026-09-18) and Phase 2 (2026-09-22) both tested market-only, fundamentals-only, market+fundamentals,
and the existing Elo+Poisson blend, with pre-registered chronological walk-forward validation and
bootstrap CIs excluding zero in every comparison. Not to be reopened by trying more algorithms on the
same 9-feature set or the same match/goal data -- only a materially new information source (xG, rest
days, referee history) or a genuinely new market family justifies revisiting this.

**Football 1X2 money-qualification backtesting (frozen V1, as-is).** Backtest Phase 1 (2026-09-22) ran
the current production thresholds against 5,776 matches under both closing and opening snapshots and
found zero qualifying bets in both, with a clear mechanistic explanation. Not to be reopened by
threshold search -- any future work here is Fraser's own threshold-review decision, not a research
question.

**Tennis market-inefficiency / edge-hunting (Workstream B's specific information set).** 13
pre-registered hypothesis families, tested against Betfair BASIC-tier last-traded price 2021-2023 (with
2024/2025 validation/OOS never even needed since development itself was null), all rejected. Per the
operator's own explicit instruction (`WORKSTREAM_B_CLOSURE.md`), this is CLOSED, not merely paused --
adding more covariates (H2H, seeding, weather, surface interactions, playing styles) to the same 13
families would not reopen it and is explicitly rejected as a path.

## PARTIALLY EXPLORED

**Tennis, as a money-qualification (not edge-hunting) question.** The exact data and linkage pipeline
Workstream B already built (12,956 linked matches, Betfair BASIC-tier intraday last-traded price) has
never been run through a Phase-1-style frozen money-qualification backtest using consensus-as-
probability -- a different research question from "can we beat the market" (see
`HISTORICAL_SOURCE_AUDIT.md` and `PHASE3_RETURN_CHECKPOINT.md`).

## UNEXPLORED

Football BTTS and team totals (no historical odds panel of any kind currently exists for either, even
though the underlying outcome is trivially derivable from existing goals data -- the gap is a live/
historical *price* source, not the outcome itself). Other sports available via The Odds API where
Betfair or another source might provide adequate historical depth (not yet surveyed in this phase
beyond the two sports the repo already touches).

## BLOCKED BY DATA

**Football Over/Under 2.5 and Asian Handicap money-qualification backtesting**, per Backtest Phase 1's
own measured finding: only 2-3 bookmakers ever quote a closing OU2.5/AH price per match in the
football-data.co.uk dataset, below the production `min_bookmakers=3` consensus floor. This is a data
depth problem, not a modelling problem -- see `HISTORICAL_SOURCE_AUDIT.md` for the leading candidate
fix (Betfair Historical Data, football/soccer, same free tier already used for tennis).
