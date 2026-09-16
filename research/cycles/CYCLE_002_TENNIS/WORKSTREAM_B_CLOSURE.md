# Tennis Workstream B — Permanent Closure Record

**Date:** 2026-09-16
**Authority:** Operator decision (Option C), relayed by Fraser, accepted in full.

This document is the permanent, frozen closure record for Tennis Workstream
B, superseding nothing in `WORKSTREAM_B_PHASE2_CHECKPOINT.md` (which remains
the full 12-point evidentiary record) but fixing the final status line so it
is never ambiguous in future sessions or reports.

## Frozen status

| Item | Status |
|---|---|
| Tennis Cycle 1 predictive modelling | **PARTIAL** |
| Tennis Workstream B 2021-2023 market-edge discovery | **CLOSED — NULL RESULT** |
| Families tested | 13 |
| Families promoted | 0 |
| 2024 development validation | NOT OPENED / NOT REQUIRED |
| 2025 market-edge OOS | NOT OPENED / NOT REQUIRED |
| Executable strategies | 0 |
| Paper bets | 0 |
| Live bets | 0 |

## What this does and does not mean

This does **not** mean tennis can never contain an edge. It means this
specific information set (Betfair BASIC-tier last-traded price) and these
13 pre-registered hypothesis families, tested rigorously with a corrected
methodology, did not demonstrate one.

**Any future Tennis cycle must begin from a materially new information
source or mechanism** (e.g. serve/return statistics, point-by-point data,
injury/withdrawal information, richer exchange microstructure) **and
receive a fresh pre-registration.** This cycle is not reopened by adding
variables (H2H, seeding, weather/altitude, surface interactions, player
styles, or any other covariate) merely because the first 13 families
returned zero promoted hypotheses — doing so would increase researcher
degrees of freedom and create a real risk of hypothesis mining, exactly the
failure mode this project's whole discipline exists to prevent. Per the
operator's explicit instruction, **this option (extending discovery) is
rejected**, not merely deferred.

Workstream B's committed code (the linkage module, the Betfair schema
parser, the market-observation pipeline, the ingestion architecture) is not
deleted or deprecated — it is exactly the kind of reusable infrastructure a
materially-new future tennis cycle would build on, if one is ever
justified.

## Next active priority

Football Cycle 2. See `research/cycles/CYCLE_003_FOOTBALL/
FOOTBALL_CYCLE_2_INITIATION_REPORT.md`.
