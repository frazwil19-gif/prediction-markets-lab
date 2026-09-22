# Phase 4 -- Market Selection Audit (2026-09-22)

## 1. Reuse of the prior data-expansion cycle (Section 3 of the Phase 4 instruction)

Commit `d10c48d` (Phase 3, "data expansion & next-market research decision", same day, earlier in this
session) already produced: `EXISTING_DATA_INVENTORY.md`, `MARKET_COVERAGE_MATRIX.csv`,
`EXHAUSTED_VS_OPEN_RESEARCH.md`, `HISTORICAL_SOURCE_AUDIT.md`, `LIVE_MARKET_COMPATIBILITY.md`,
`MARKET_PRIORITY_SCORECARD.md`, `DATA_ACQUISITION_PLAN.md`, `LIVE_DATA_PRESERVATION_PLAN.md`,
`PHASE3_RETURN_CHECKPOINT.md` under `research/data_expansion/`. This audit was read in full before any
new work began in this Phase 4 cycle, per the operator's own explicit instruction not to repeat it.

**That cycle's own headline conclusions, reused here rather than re-derived**: football 1X2
(probability modelling AND money-qualification) and tennis market-inefficiency edge-hunting are
EXHAUSTED; football OU2.5/AH money-qualification backtesting is BLOCKED BY DATA (only 2-3 bookmakers
per match historically, below the production `min_bookmakers=3` floor); tennis money-qualification is
PARTIALLY EXPLORED and was that cycle's own top-priority nomination; BTTS/team totals/other markets are
UNEXPLORED; Cricket remains paused.

**What that prior audit did NOT separately assess, and this cycle adds**: it evaluated markets almost
entirely through the lens of MONEY-QUALIFICATION-BACKTEST feasibility (can we replay history against
production thresholds?). It did not separately ask the outcome-PREDICTION question the operator's
research-direction correction (this cycle's own driving instruction) now requires: can we build and
validate a calibrated probability estimate for this market's outcome, even where a production-grade
historical betting replay is unavailable? Section 8/20 of this cycle's instruction is explicit that
these are different questions with potentially different answers -- and that turned out to matter
directly: football OU2.5 money-qualification backtesting is BLOCKED, but OU2.5 OUTCOME PREDICTION was
not blocked at all (5,759/5,800 matches, 99.3% coverage, immediately usable).

## 2. Research Atlas

See `RESEARCH_ATLAS.md` / `RESEARCH_ATLAS.json` (same directory) for the full per-market
classification this section's reasoning is built on.

## 3. Market priority decision (Section 18-19 of the Phase 4 instruction)

Candidates actually compared, on the instruction's own stated criteria (historical sample size, feature
quality, outcome label quality, live compatibility, research independence, calibration feasibility,
event frequency, implementation complexity, future betting-overlay feasibility -- explicitly NOT
"which market looks historically most profitable"):

| Market | Historical sample | Feature reuse | Live compatibility | Betting-overlay feasibility | Implementation complexity |
|---|---|---|---|---|---|
| Football O/U 2.5 | 5,759/5,800 matches, 99.3% coverage | Full reuse of existing `cycle_002_discovery_features.csv` rolling goals/shots/SOT features -- zero new feature engineering | LIVE already, wired into production `decisions/recommendation.py` since 2026-09-19 | Blocked retrospectively (thin historical panel), but the live system is already prospectively paper-trading it | Lowest -- new module (~19 features + 1 thin-panel market field, both already columns in an existing file), reused binary logistic regression / walk-forward / metrics tooling unchanged |
| Football BTTS | 5,800/5,800 matches (target trivially derivable) | Same feature reuse as O/U 2.5 | NOT live, not wired anywhere | No historical odds at all, no live wiring either | Low, but strictly higher than O/U 2.5 (needs new live wiring work before any future betting overlay is even conceivable) |
| Football AH | Blocked by per-match varying line | Feature reuse possible in principle | Not wired for AH | Blocked by data (thin historical panel, same as O/U 2.5) | Highest -- needs a new line-pooling/target design before Stage A is well-defined at all |
| Tennis Match Winner | 12,956 linked matches | Different feature family entirely (Elo/ranking, no reuse of football features) | NOT live | Every prerequisite already satisfied (per Phase 3's own nomination) -- but this is a MONEY-QUALIFICATION question, not the outcome-prediction-discovery question this cycle is scoped to | Already-built pipeline exists (Workstream B), but this cycle deliberately avoided defaulting to tennis per the instruction's own Section 5 caution not to repeat Workstream B under a different name without fresh justification |

**Decision: Football Over/Under 2.5 Goals**, exactly the outcome the operator's Section 19 flagged as
the expected (not mandated) preference, confirmed here by an actual audit rather than assumed: it has
the best combination of ready outcome-prediction feasibility (essentially complete match coverage, full
feature reuse, zero new acquisition), live compatibility (already in production), and research
independence (a genuinely different, binary target from 1X2, not a repeat of the same modelling
question in different clothes).

**Why not BTTS**: equally feasible for Stage A, but strictly weaker on live compatibility (not wired at
all) and would need new production wiring work before any future Stage B could even be attempted --
correctly deferred as a good next-in-line candidate, not this cycle's pick.

**Why not tennis**: per the instruction's own Section 5 explicit caution, tennis was not defaulted to.
It also answers a different research question (money-qualification, already scoped and nominated by
the separate Phase 3 data-expansion cycle) rather than the outcome-prediction-discovery question this
Phase 4 instruction is specifically about.

**Why not Asian Handicap**: the per-match varying handicap line means "the AH outcome" is not a single
well-defined binary target the way O/U 2.5 or BTTS are -- Section 6.C's own explicit warning against
merging different handicap lines confirms this is a materially larger design problem, correctly
deferred rather than rushed.

## 4. Sequencing discipline (Section 22)

This cycle researched exactly ONE market (Football O/U 2.5) end-to-end (research -> validation ->
"freeze" in the sense of a settled Decision B verdict, see `PHASE4_RETURN_CHECKPOINT.md`) before
touching any other candidate. BTTS, Asian Handicap, and Tennis money-qualification all remain
correctly un-started, per Section 22's explicit "do not launch five uncontrolled research cycles
simultaneously."
