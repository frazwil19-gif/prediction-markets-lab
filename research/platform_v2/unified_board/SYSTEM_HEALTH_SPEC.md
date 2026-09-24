# System Health (V2-5)

Computed on every board build (`health.py`), shown at the top of the board and in its JSON.
| component | source | flag |
|---|---|---|
| daily_scan | `status/latest.json` last_scan | OK / FAILED (status ≠ success) / STALE (> 30 h) / OUTAGE (> 48 h) / UNKNOWN |
| settlement | `status/latest.json` last_settlement | same |
| tennis_board | `tennis_predictions/run_log.csv` last row (or last unified tennis ingest) | same |
| ci_tests | last workflow run whose test step passed (recorded with `--ci-passed`) | same |
| API credits | latest `x_requests_remaining` in tennis/NBA credit logs | < 75 ⇒ DEGRADED |
Overall: **DEGRADED** if daily_scan or settlement is FAILED/STALE/OUTAGE or credits are below reserve (the board prints a
banner); HEALTHY_WITH_WARNINGS if anything else is flagged; otherwise HEALTHY. `outage_flag` and `stale_data_warning` are
explicit booleans for ChatGPT. If the daily scan fails, the workflow still rebuilds the board (build only), so staleness shows
instead of a normal-looking board.

## Stale-data safeguards
Football rows are refused if the card data is > 6 h old at ingest, outside 0–48 h to kickoff, the event has started, the
triplet is incomplete, duplicated or sums outside 1 ± 0.03, or the engine is unknown. NBA requires ≥ 3 paired books and 0–36 h
to tip-off. Tennis keeps its frozen quote-age rule (6 h). The registry is validated before any run; an invalid registry
produces no predictions.
