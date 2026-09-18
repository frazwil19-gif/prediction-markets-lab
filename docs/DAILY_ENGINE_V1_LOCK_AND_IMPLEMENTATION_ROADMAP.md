# Daily Probability Engine — Objective Lock & V1 Implementation Roadmap

**Date:** 2026-09-18
**Trigger:** Operator's "MAJOR PROJECT DIRECTIVE — LOCK THE DAILY PROBABILITY ENGINE OBJECTIVE"
instruction (relayed by Fraser, 2026-09-18), issued after the Claude Project description itself was
rewritten to state the daily-bet-selection-engine objective directly, and after Gate 1's empirical
result (see below) landed.
**Status:** Audit and roadmap only, per the operator's explicit instruction. No paid data acquired, no
bet placed, no automation implemented, no new sport research cycle started.

This document does not repeat work already done. It answers the operator's 10-point CURRENT TASK list
in order, building on two documents already in the repo/project and treating both as authoritative
background rather than re-deriving them:

- `docs/DAILY_PROBABILITY_ENGINE_V1_DESIGN_MIGRATION_REPORT.md` (2026-09-18) — the full 34-point
  audit and V1 design. Its findings stand; this document updates and sharpens them, it does not
  replace them.
- The Claude Project's `master-research-directive.md` §14 (objective correction) and §15 (Gate 1
  result) — the governing objective statement and the empirical finding that now closes one of the
  migration report's own open design choices (see point 7 below).

---

## 1. Audit against the corrected objective

Confirmed directly against the repository this session (fresh `device_bash` reads, not recalled from
memory): the objective correction is already fully reflected in governance documents —
`docs/ARCHITECTURE_FREEZE_V1.md` carries a 2026-09-18 supersession note, and the Project's
`master-research-directive.md` §1 is explicitly marked "Superseded by §14" with inline `§14 note`
annotations at §3, §5, §6, §7, §8, §12. No further supersession edits are required (point 3 below is
therefore already satisfied, not newly done here).

What *is* new this session, and materially updates the migration report's own design: **Gate 1** (a
separate, already-completed and already-checkpointed piece of work — see `master-research-directive.md`
§15) empirically tested the migration report's central open question — "where should the daily
engine's probability actually come from?" — for football 1X2, across 5,631 out-of-sample matches,
2020/21-2025/26, strict walk-forward validation. Result: **de-vigged multi-bookmaker consensus beats
the existing frozen Elo/Poisson blend, a from-scratch fundamentals-only model, and a market+fundamentals
ensemble, on every metric (log loss, Brier, calibration, AUC), with 95% bootstrap CIs excluding zero.**
This is not a new instruction to act on; it is evidence that confirms the migration report's own
recommended "Option A" (consensus-as-probability, price-dispersion-as-value) was the right call, not a
provisional placeholder pending a model that would eventually beat the market. Nothing in the V1 design
needs to change because of Gate 1 — it needed to be tested, and now it has been.

## 2. Preservation of prior research and verdicts

Confirmed unchanged, again directly against the repo: `research/cycles/CYCLE_001/`,
`research/cycles/CYCLE_002_TENNIS/`, and `research/cycles/CYCLE_003_FOOTBALL/` remain exactly as
committed, including Stage 3B's MARKET DOMINATES verdict, Tennis Cycle 1's PARTIAL verdict, Tennis
Workstream B's 13-for-13 REJECT, Football Cycle 2's H-FB2-001 REJECT and H-FB2-002 sealed-OOS FAIL, and
now Gate 1's own market-consensus-wins result. None of these were reopened, reframed, or deleted. They
remain permanent scientific record answering a real (if no longer primary) question: can a specific
model beat the market's own price. The daily engine's new objective does not require any of them to be
different.

## 3. Old "must-beat-market" directive language — supersession status

Already handled, not newly required: `docs/ARCHITECTURE_FREEZE_V1.md`'s supersession note and
`master-research-directive.md` §14 (with its §1/§3/§5/§6/§7/§8/§12 inline notes) together already mark
every instance of "prove persistent mispricing before betting" as historical, superseded language. This
document adds one clarification the prior two did not need to make, because Gate 1 hadn't run yet:
**the migration report's Option A was written as a design choice justified on cost/risk grounds
("this needs no new predictive claim"); it can now also be justified on evidence grounds ("this
specific claim — that consensus is the best available football-1X2 probability source — has been
empirically tested and confirmed").** Both justifications point to the same V1 design, so no document
needs rewriting, only this additional grounding.

## 4. Everything already built that is reusable (updated inventory)

The migration report's §4 inventory (calculation engine, manual workflow, schemas, football/tennis
historical infrastructure, research governance layer — 718 tests passing at the time) stands. This
session's fresh audit adds two confirmed, concrete findings that sharpen it — one confirms a known gap,
one is new:

- **`src/prediction_markets_lab/ingestion/odds_api_loader.py` is confirmed, by direct inspection, to
  contain only a docstring** — zero logic, a Stage-6 placeholder exactly as the migration report
  described. No live-odds automation exists anywhere in the codebase today.
- **New finding: the schemas and decision code that Option A will run through were built assuming a
  bookmaker-vs-*exchange* comparison, not a bookmaker-vs-bookmaker comparison.** `storage/schemas.py`'s
  `MarketRecord` has fields named `exchange`, `exchange_odds`, `exchange_implied_probability`, and a
  non-zero `commission`; `decisions/grading.py`'s `GradingInput` has hard gates named
  `exchange_price_current`, `market_rules_match`, and `liquidity_adequate` — all exchange-specific
  concepts (an order book has live prices, liquidity, and settlement-rules risk that a fixed-odds
  bookmaker quote does not). The migration report's Option A text describes comparing consensus against
  "a softer bookmaker's price" as well as an exchange price, but the code was only ever exercised
  against the exchange framing. This is a real, if small, naming/semantics gap — see point 8's
  itemisation and point 10's NEEDS MODIFICATION bucket. It does not block V1; it is one of the small
  fixes point 8 lists.
- `scripts/settle_results.py` (settlement/bankroll-ledger logic) is confirmed present, complete, and
  already covered by `tests/integration/test_settlement_script.py` — this had been flagged as "not yet
  located" in an earlier continuity note; it is now confirmed to exist and function as the migration
  report's §24 described.
- `config/thresholds.yaml` and `config/bankroll.yaml` are confirmed to still hold their original Stage-1
  placeholder figures (stake caps £0.25/£0.50, starting bankroll £10.00) — unreconciled against
  Fraser's actual bankroll, exactly as migration report §23/§30 already flagged. Not a technical gap;
  a pending decision.

## 5. Shortest rigorous roadmap from current state to the first operational Daily Bet Card

This is the migration report's own §31 sequence, unchanged in shape, with Gate 1's result removing one
source of hesitation (step 0 below is new; everything else is §31 verbatim, renumbered):

0. **(Done, this session)** Confirm empirically that market consensus is a trustworthy probability
   source for football 1X2 — Gate 1, complete.
1. Reconcile `config/bankroll.yaml` / `config/thresholds.yaml` stake figures against Fraser's real
   starting bankroll and risk comfort — a decision, not code.
2. Fix the exchange-vs-bookmaker naming/semantics gap identified in point 4 — rename or generalise
   `MarketRecord`'s `exchange*` fields and `GradingInput`'s `exchange_price_current` /
   `market_rules_match` / `liquidity_adequate` gates so they describe "the venue/bookmaker the bet will
   actually be placed at," with sensible defaults for a fixed-odds bookmaker (commission = 0,
   liquidity/market-rules gates either dropped or redefined as "quote is not stale" and "market
   definition matches the consensus market exactly"). Small, mechanical, fully covered by existing
   tests that will need matching updates — not a redesign.
3. Run the existing test suite and do a fresh read-through of the Stage 1/2 modules to confirm they
   still function as documented (verification, not rewrite).
4. Pick one real day and one real football fixture for a manual dry run: identify the fixture, manually
   enter prices from 2-3 real bookmaker sources into the existing CSV templates, run the existing
   `generate_daily_shortlist.py` → `daily_report.py` pipeline unmodified, inspect the output by hand.
5. Fix whatever the dry run surfaces (expect small issues — stale config, a schema mismatch — not
   architectural ones, per the migration report's own inventory).
6. Add the small, genuinely new persistence pieces (`events`, `feature_snapshots`, `model_predictions`,
   `model_performance` — migration report §19) only once the dry run proves the existing schemas need
   them, not speculatively.
7. Wire the deterministic half of the daily loop (shortlist generation, report rendering, settlement,
   monitoring) into GitHub Actions once the manual dry run has been repeated successfully by hand a
   handful of times; event/market discovery and price entry remain manual/operator-assisted for V1
   (no live fixture or odds feed exists — see point 8).
8. Only then extend scope from football 1X2/O-U 2.5/AH to tennis match winner, then to any further
   research-cleared market — one family at a time.

## 6. Prioritise a useful V1 over another long research cycle

No new research cycle is proposed or started by this document. Step 0 above (Gate 1) was already
approved and gated work, now closed. Every other step in point 5 is implementation and configuration
work against already-tested code, explicitly chosen over starting Tennis Cycle 2, Basketball, or
Cricket, all of which remain paused per §14/§5 of the master directive.

## 7. Recommended first sport(s) and market(s)

**Football 1X2, Over/Under 2.5, and Asian Handicap — unchanged from the migration report's §12/§13
ranking, now reconfirmed rather than merely inferred.** Reasoning, combining both documents: this is
the only market family with simultaneously (a) full historical depth and tested feature/model
infrastructure, (b) full historical price coverage for validation, (c) a current price obtainable today
even with no live feed (manual entry from any bookmaker site or Oddschecker), and, as of Gate 1, (d) an
empirically confirmed probability source for the most important of the three markets (1X2). Tennis
Match Winner remains the next addition once the football path is proven end-to-end manually — it has
the same "consensus as probability" logic available but has not had its own Gate-1-equivalent test, and
the migration report itself flags Global Elo there as only PARTIAL-validated (not disqualifying, since
consensus rather than Elo would be the V1 probability source, but a reason to sequence it second).

## 8. Exactly what is still missing

- **Current fixture source**: none. No live fixture feed exists or is proposed for V1; fixture
  identification stays operator-assisted (a person names today's matches), per the migration report's
  §18 Task A. `football-data.org`'s free tier could cover this later for Premier League/Championship
  but not the Scottish Premiership, and is explicitly not required for V1.
- **Current odds source**: none automated. `ingestion/odds_api_loader.py` is a confirmed empty
  placeholder. V1 uses the existing manual CSV templates (`templates/manual_odds_entry.csv`,
  `templates/exchange_price_entry.csv`) exactly as Stage 2 designed, filled in by Fraser from
  bookmaker sites/Oddschecker each morning.
- **Probability models**: for the V1 scope, none needed beyond what exists — de-vigged consensus
  (`probability/consensus.py`, `margin_removal.py`, `market_pipeline.py`), now Gate-1-confirmed for
  1X2. The frozen Elo/Poisson models remain available as secondary diagnostics only.
- **Market enumeration**: not automated; operator-assisted daily selection of which fixtures/markets to
  price, per migration report §18 Task A. No market-enumeration service exists or is proposed for V1.
- **Grading**: exists and is tested (`decisions/grading.py`, config-driven via
  `config/thresholds.yaml`), but needs the point-4/point-5-step-2 naming fix (exchange-specific field
  names/gates) before it cleanly represents a bookmaker-vs-bookmaker comparison, and needs its stake
  figures reconciled against a real bankroll (point 4).
- **Staking/risk**: exists and is tested (`risk/staking.py`, `risk/bankroll.py`, `risk/exposure.py`,
  `risk/loss_locks.py`) — fixed-stake-per-grade, hard-capped, no martingale, no chasing, by
  construction. Needs the same config reconciliation as grading.
- **Daily scheduling**: no automation exists yet. `weekly_report.yml` is a confirmed disabled
  placeholder (`on: workflow_dispatch` only, no cron). For V1, the deterministic half of the pipeline
  (shortlist generation from a manually-populated CSV, report rendering, settlement, monitoring) is the
  only part proposed for GitHub Actions automation, and only after a successful manual dry-run
  sequence (point 5, steps 4-7) — event discovery and price entry stay manual.
- **Result logging**: exists and is tested (`scripts/settle_results.py`, `BetRecord`'s
  result/profit/CLV fields, `performance/clv.py`/`roi.py`/`drawdown.py`) — confirmed present this
  session, not merely assumed. Never yet run against a real logged recommendation, only against
  backtest/synthetic data.

## 9. Realistic MVP for Fraser to begin manual placement while the system keeps learning

1. Fraser (with operator assistance) identifies 1-3 football fixtures each morning from the frozen
   competitions (E0/E1/SC0) with a clear 1X2/O-U 2.5/AH market.
2. Fraser manually enters 3+ bookmakers' current prices into the existing CSV templates.
3. The existing, unmodified `generate_daily_shortlist.py` → `daily_report.py` pipeline computes
   de-vigged consensus (the Gate-1-confirmed probability), compares it against the single best
   currently-obtainable price from a different bookmaker, and produces graded (A+/A/B/C/Reject)
   recommendations with a recommended stake, capped by the reconciled `config/bankroll.yaml` figures.
4. Fraser places any A+/A recommendation manually — at very small, explicit stakes agreed in advance
   (point 5, step 1) — and logs it via the existing `BetRecord` schema/template. Zero qualifying bets
   on a given day is a correct, expected outcome, never a reason to loosen thresholds.
5. `scripts/settle_results.py` logs the result once known; `performance/clv.py`/`roi.py`/
   `calibration.py` accumulate real, as-lived performance data over time — reusing existing, tested
   code, pointed at live rather than backtest data for the first time in the project's history.
6. This MVP requires no paid data, no live feed, no automation, and no new model — every component in
   it already exists and is tested. The only genuinely new step before it can run is the point-5-step-2
   naming/semantics fix and the point-5-step-1 config reconciliation, both small and mechanical.

## 10. BUILT/REUSABLE vs NEEDS MODIFICATION vs NEEDS BUILDING vs FUTURE

**BUILT / REUSABLE AS-IS** — no code changes required to run the V1 MVP:
`probability/odds_conversion.py`, `probability/margin_removal.py`, `probability/consensus.py`,
`probability/market_pipeline.py`, `probability/uncertainty.py`; `ev/expected_value.py`,
`ev/break_even.py`, `ev/edge.py`, `ev/commission.py` (commission=0 is already a valid input, so a
bookmaker-only V1 run needs no code change, only a config value); `risk/staking.py`,
`risk/bankroll.py`, `risk/exposure.py`, `risk/loss_locks.py`, `risk/decision_gates.py`;
`ingestion/manual_odds_loader.py`, `ingestion/exchange_price_loader.py` (already generic enough to
read any venue's CSV); `scripts/generate_daily_shortlist.py`, `scripts/settle_results.py`;
`reports/daily_report.py`, `reports/markdown_renderer.py`; `storage/csv_store.py`,
`storage/sqlite_store.py`, `storage/google_sheets_adapter.py`; `models/football_elo.py`,
`models/football_poisson.py`, `models/football_blended.py` (secondary diagnostics only);
`performance/calibration.py`, `performance/clv.py`, `performance/roi.py`, `performance/drawdown.py`;
the entire research-governance layer (`research/registry.py`, `research/schemas.py`,
`research/evidence_grading.py`, verdict classifiers) — untouched, continues to govern any future
research claim.

**NEEDS MODIFICATION** — small, mechanical, no redesign:
`storage/schemas.py::MarketRecord` and `decisions/grading.py::GradingInput` (generalise the
`exchange`-named fields/gates to describe any venue, including a fixed-odds bookmaker, per point 4/8);
`config/bankroll.yaml` and `config/thresholds.yaml` (reconcile stale Stage-1 placeholder figures
against Fraser's real bankroll and risk comfort); `DailyShortlistRow.price_expiry_note` (currently an
unpopulated field — needs a concrete staleness rule, migration report §21); `docs/DAILY_WORKFLOW.md`,
`docs/MARKET_RULES.md`, `docs/OPERATING_MANUAL.md` and similar operational docs (review for currency
against the confirmed V1 scope, not a rewrite — migration report §29).

**NEEDS BUILDING** — genuinely new, all small and narrowly scoped:
an `events` table/schema (today's fixture-level identity — currently implicit); a `feature_snapshots`
table (freezing the exact predictor/price inputs used for a given day's recommendation, for
reproducibility); a `model_predictions` table (a small Model/Method Registry recording which method
produced each day's probability, its version, and validation status); a `model_performance` aggregation
table (rolling up calibration/CLV/ROI from accumulating live `BetRecord` rows — the calculation
functions already exist, only the aggregation-over-time storage is new); the GitHub Actions workflow
that runs the deterministic half of the daily pipeline on a schedule (point 5, step 7) — deferred until
after a successful manual dry-run sequence, not before.

**FUTURE — explicitly out of scope for V1, not started, not blocked from ever happening**:
any live fixture or live odds API integration (`ingestion/odds_api_loader.py` stays a placeholder);
corners/cards/shots-on-target as tradable propositions (no free live-or-historical price source exists
for them — a data-availability wall, not a priority choice); Tennis Set Betting/Handicap, Football
Over/Under-at-other-lines, and Both-Teams-To-Score (all require a scoped extraction/modelling step
before joining any V1); the multi-bet constructor (no code exists, none proposed for V1); any Betfair
Live Application Key / automated execution (a one-off £499 fee, requires betting functionality, and is
explicitly gated behind manual and paper-trading validation per the master directive §9 and migration
report §33); Cricket, Basketball, and any further pure market-inefficiency research cycle (all paused
per §14/§5 of the master directive).

## 11. Explicit confirmation of the operator's restrictions

No paid data was acquired. No bet was placed. No betting automation was implemented. No new major sport
research cycle was started — Cricket, Basketball, and any further Tennis/Football hypothesis work
remain exactly where §14/§5 of the master directive left them. This document is audit and design only.

## 12. Next decision needed from Fraser/the operator

Everything in points 5 and 9 above can begin immediately without further approval — it is
configuration, small mechanical code changes, and running already-tested scripts against manually
entered real data, all within the master directive's existing "manual execution first" doctrine. The
one number this document deliberately does not choose on its own is the reconciled stake-cap figures in
point 5 step 1 / point 8 (grading) — that is Fraser's own risk decision, not a technical one, and the
recommendation is to set it explicitly (even if provisionally) before the first manual dry run, so the
dry run's output reflects real intended stakes rather than stale Stage-1 placeholders.
