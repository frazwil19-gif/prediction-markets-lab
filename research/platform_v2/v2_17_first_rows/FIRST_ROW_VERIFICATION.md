# First prospective row verification — football (expected ~7–8 Oct) and NBA (from 20 Oct)

**Rules:**
- Read-only, 0 API calls.
- Run only after a **genuine schedule-triggered** run has written the first rows. Never trigger a run to create evidence.
- Report the result as **PASS / FAIL / PENDING**. On FAIL: report it, change nothing, and propose a fix for approval.

## Procedure

1. Identify the run that wrote the first rows: run id, cron, actual start vs configured, and production commit SHA.
2. On that commit, run `python scripts/verify_first_rows.py --sport football` (or `--sport basketball`).

## What the script checks

| Area | Check |
|---|---|
| Provenance | Engine ids, the live estimator named (`…@1-live`), origin |
| Timing | Prediction time < start; minutes-to-event inside the snapshot window (48h football, 36h NBA); workflow timing recorded |
| Event keys | No duplicate (event, market, selection, engine). Football: complete H/D/A triplets, and DC price source synthetic only. NBA: one row per game, and the price source is the actual book (`odds_api:<book>`) |
| Stage A | Every valid upcoming row is on the board, with probability basis, σ method, calibration status and price status. 1X2 normalised; DC never `PRICE_VALID` |
| Start times | est-1 resolution rows exist (written by evaluate runs) |
| Stage B | bet-selection candidates exist for priced markets (1X2, O/U, NBA moneyline). DC stays DATA_BLOCKED |

## Manual additions to the report

- **Football:**
  - Settlement mapping for every team on the rows; Bolton and Lincoln must resolve.
  - The DC no-peek guard is CLOSED (`holdout_masked` present).
  - The credit ledger shows the football gate decisions for that run.
- **NBA:**
  - Activation was not before 2026-10-20.
  - Minutes-to-tip distribution.
  - Credit spend vs the NBA cap.
- **Both:**
  - `reports/credit_report.md` actual vs Plan A.
  - V2-7 logging unaffected: a separate research commit, config sha `9e52b67df08691d0`.
