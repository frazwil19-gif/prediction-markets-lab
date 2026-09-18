# Architecture Freeze — V1

## Status

As of the end of Stage 2, the current architecture is **sufficient
for the first research cycle**. This document freezes it: no new
infrastructure modules should be added unless a real research
requirement proves they are necessary.

## Why freeze now

The project has built:

- A working calculation engine (odds conversion, margin removal,
  consensus, EV, grading, staking, risk gates) — Stage 1.
- A manual workflow (CSV ingestion, daily reports, settlement,
  Sheets workbook) — Stage 2.
- A research-governance layer (Hypothesis Registry, Behaviour Atlas,
  evidence grading, prioritisation) — Stage 2.

This is enough machinery to run an actual research cycle. Adding more
infrastructure now — before any real historical data has been
acquired or any hypothesis tested — would be building on top of an
unvalidated foundation instead of validating it. The project's own
philosophy (`docs/RESEARCH_ENGINE.md`) explicitly warns against
mistaking "the framework exists" for "the framework works."

## The rule

**All new work should prioritise evidence generation over
infrastructure.** Concretely:

- Speculative features are deferred, even if they seem useful.
- New files require a clear, stated purpose tied to a specific
  research task in progress.
- Duplicated functionality is prohibited — if something like it
  already exists in `src/prediction_markets_lab/`, extend or reuse it
  rather than writing a parallel version.
- Placeholder modules (the many documented-but-empty files from Stage
  1, e.g. `models/football_elo.py`) should not be expanded merely to
  "complete" the directory tree. They get real content only when a
  research task in progress actually needs them.

## Change-control questions

Every proposed new module — before it is written — must have answers
to all five of these:

1. **Which current research task requires it?** (Name the specific
   Cycle/hypothesis/behaviour, not a general aspiration.)
2. **Why can the task not be completed using existing components?**
   (Check `src/prediction_markets_lab/` first — probability/, ev/,
   risk/, decisions/, research/, storage/ already cover a lot.)
3. **What test proves the module is necessary?** (If you can't write
   a failing test that only this new module would fix, it's probably
   not necessary yet.)
4. **What maintenance burden does it add?** (New config files, new
   CSV schemas, new dependencies all have an ongoing cost — state it.)
5. **Is it required before the next research decision?** (Or could the
   decision be made — even if only "defer" — without it?)

If these five questions cannot all be answered concretely, **defer the
module.** Write it down as a future need (e.g. in
`docs/ROADMAP.md` or a Cycle's `CYCLE_PLAN.md`) rather than building it
speculatively.

## What this does NOT freeze

This freeze is about *infrastructure*, not *evidence*. It is fully
expected and encouraged to:

- Acquire and audit real historical data.
- Populate `research/hypotheses/hypothesis_registry.csv` status
  transitions as real testing happens.
- Add real rows to `research/behaviours/behaviour_atlas.csv` once a
  hypothesis earns them.
- Fill in `research/cycles/CYCLE_00N/` outputs with real results.
- Fix bugs found in existing modules (e.g. the per-bookmaker margin
  removal correction already made — see CHANGELOG.md).

None of that requires new infrastructure modules; it requires *using*
the infrastructure that already exists to generate evidence.

## Revisiting this freeze

This document can be revisited once Cycle 1 (`research/cycles/CYCLE_001/`)
is complete and its findings identify a genuine, specific gap in the
existing architecture — not before.

## Supersession note (2026-09-18)

This freeze is partially superseded. The operator's "MAJOR PROJECT DIRECTION CHANGE — DAILY
PROBABILITY & BET-SELECTION ENGINE" instruction (2026-09-18) identified the "genuine, specific gap"
this document's "Revisiting this freeze" section required before new infrastructure could be added:
a live-data intake and daily-orchestration layer never existed, because the project moved from
Stage 2 straight into pure historical hypothesis-testing (Cycles 1-2) without ever exercising the
Stage 1/2 calculation/decision/persistence engine against real daily data.

See `docs/DAILY_PROBABILITY_ENGINE_V1_DESIGN_MIGRATION_REPORT.md` for the full audit and design. Its
headline finding is that almost none of this freeze's concern applies: the calculation engine,
decision/risk gates, storage schemas, and manual-workflow scripts this freeze protected are exactly
what the new objective reuses, unmodified. The freeze's change-control questions (five questions
before any new module) remain in force and were applied in that report — only a small number of
genuinely new, narrowly-scoped additions were identified (an events/feature-snapshot/model-prediction
persistence layer, a staleness-expiry rule, and a small method registry), each tied to a specific
requirement in that report rather than built speculatively.

This freeze is not lifted wholesale. It still applies to anything outside the V1 scope that report
defines (§13) — in particular, no corners/cards/shots-on-target tradable-market infrastructure, no
odds-API integration, no automated execution, and no Cricket infrastructure should be built on the
strength of this note alone.
