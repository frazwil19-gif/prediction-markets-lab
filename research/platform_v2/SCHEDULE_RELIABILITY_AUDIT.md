# GitHub Schedule Reliability Audit — 2026-09-24

Observed start delays of scheduled runs (configured cron → actual start, UTC):
| workflow | configured | actual starts | delay |
|---|---|---|---|
| daily_scan | 07:00 | 20 Sep 12:05 · 21 Sep 13:44 · 22 Sep 12:27 · 23 Sep 12:38 · 24 Sep 12:36 | **5.1–6.7 h** |
| settlement_and_performance | 21:00 | 21 Sep 23:59 · 22 Sep 23:33 · 23 Sep 23:34 | 2.6–3.0 h |
| tennis_prediction_board | 06:30 | 24 Sep 12:04 | 5.6 h |
| tennis_prediction_board | 22:30 | 24 Sep 00:39 | 2.2 h |
GitHub documents that scheduled workflows can be delayed during high load and may be dropped. The delays here are
large and consistent. **Current reliability is not adequate for a precisely timed snapshot**, though it is adequate
for "one board per day, well before most starts" (a noon football card still precedes 15:00 kickoffs but can miss
12:30 ones).

## Instrumentation (implemented, additive)
- Every tennis board run appends to `tennis_predictions/run_log.csv`: scan timestamp, trigger (schedule/manual),
  **configured cron**, GitHub run id, keys, events, predictions added, and median minutes to start. Each ledger row
  already holds `prediction_timestamp` and `commence_time`, so minutes-to-event is exact per prediction.
- Historical predictions are not altered.

## Options (none implemented; no paid infrastructure)
1. **Redundant crons + idempotency (free, simplest):** add 1–2 extra tennis crons. The ledger already ignores
   duplicates, *but each run costs credits*, so this is limited by the budget.
2. **External free trigger (most accurate):** a free cron service (e.g. cron-job.org) calls GitHub's
   `workflow_dispatch` API at exact times. It needs a fine-grained GitHub token with Actions-write on this repo,
   created and stored by Fraser. Manual dispatches today started within ~1 minute.
3. Local Mac scheduler: accurate but only when the Mac is on (rejected earlier for production).
Recommendation: **option 2 for the tennis/NBA boards** when prospective timing matters (NBA especially). Until then,
treat the actual scan timestamp (recorded) as the snapshot of record.
