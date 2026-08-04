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
