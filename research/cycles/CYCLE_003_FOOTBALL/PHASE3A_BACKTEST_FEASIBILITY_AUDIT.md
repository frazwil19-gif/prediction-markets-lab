# Phase 3A — Historical Backtest Feasibility Audit

**Date:** 2026-09-19
**Context:** operator's "MAJOR NEXT PHASE — LIVE COMMISSIONING + BACKTEST/PAPER-TRADING VALIDATION" instruction, Phase 3A: "Audit what historical information we already possess before downloading anything else... do NOT use closing/future information when simulating an earlier betting decision."

## What we already have

The Cycle 1 dataset (frozen, hash-sealed, `cycle_001_v1.0.0-20260910T234139`): E0 (Premier League), E1 (Championship), SC0 (Scottish Premiership), 2020/21–2025/26, ~5,800 matches. Per match, per bookmaker, football-data.co.uk gives **one opening price and one closing price** — not an intraday time series, and no exchange (Betfair/Smarkets) price at all. This limitation is already documented and governed by `docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`, which this audit defers to rather than re-deriving.

## The timing problem, stated plainly

V1's live design is: de-vigged multi-bookmaker **consensus** as the probability, checked against a single **best currently-obtainable price** from the same snapshot in time. Historically, the only way to avoid mixing timestamps (which would be a leakage risk this project has spent months avoiding) is to build both the consensus *and* the "best price" from the **same** snapshot — either all-opening or all-closing, never one from each.

- **Opening odds as the simulated decision point**: per `HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md` rule 3, opening odds may be stale relative to what a live, same-day scan (V1's actual operating model) could achieve — a backtest built on opening prices would be **optimistic** relative to reality, not a fair test of the actual daily-scan design.
- **Closing odds as the simulated decision point**: this is the more honest analogue of "scan the market shortly before a decision is needed" (V1's actual behaviour), and closing bookmaker consensus is exactly what Gate 1 (§15 of the master directive) already validated for calibration quality. Using closing-snapshot consensus vs. closing-snapshot best price is internally consistent — no information from after that snapshot (i.e. no match result, no later price movement) is used, so this is **not** a lookahead violation.

**Conclusion: a historically honest backtest of the V1 daily engine is feasible using the existing Cycle 1 dataset, using the closing-price snapshot for both sides of the comparison, with one explicit, unavoidable caveat**: this tests "if you had scanned the market at closing time," not "if you had scanned this morning and the price held" — the two are not identical, and the backtest's results must be labelled accordingly (following the existing `proxy_clv` discipline: e.g. `backtest_price_basis: "closing_snapshot_proxy"`, never presented as equivalent to a same-day live scan's realistic execution).

## Market coverage in the existing data

- **1X2**: full coverage across all three leagues and every season — this is the market Gate 1 already validated end-to-end.
- **Over/Under 2.5**: partial. The E0/E1/SC0 files carry Bet365 (`B365>2.5`/`B365<2.5`) and Pinnacle (`P>2.5`, and presumably `P<2.5`) closing totals columns in more recent seasons, but not a multi-bookmaker consensus panel as rich as 1X2's. A consensus-quality O/U 2.5 backtest may be limited to whichever seasons have enough bookmakers' totals columns populated — this needs a column-completeness audit before backtesting O/U 2.5, not an assumption that coverage matches 1X2's.
- **Asian Handicap**: not audited here — AH remains out of scope for this phase (see the prior checkpoint), consistent with "should not delay core automation."

## What this backtest would need to build (not yet built)

A chronological, walk-forward replay: for each historical match date, using only that date's closing-snapshot odds panel, run the *exact same* production code path used live (`probability.market_pipeline` → `decisions.recommendation.build_recommendation` → grading/staking) to produce what V1 would have recommended, then compare against the real result. This is a genuinely new piece of engineering — a replay harness, not a reuse of Gate 1's comparison scripts (which compared *probability architectures* against each other, not this project's actual grading/EV/staking decision layer against real outcomes). It is the natural next build after this audit, and is **not started yet** — flagged honestly rather than rushed, given the volume of Phase 1/2/3B work already completed and committed in this same session.

## Recommendation

Feasible and worth building next, scoped as: replay 1X2 first (matches Gate 1's already-validated architecture and full data coverage), using the closing-snapshot proxy explicitly labelled as such, producing exactly the same performance metrics the operator's Phase 3A instruction specified (win rate vs. expected, Brier, log loss, calibration, ROI/yield, drawdown, losing-streak length) bucketed by grade/sport/competition/market/probability-band/odds-band. O/U 2.5 backtesting follows once its bookmaker-coverage completeness is separately confirmed.
