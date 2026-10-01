# V2-14 — Credit Plan A implementation (approved 2026-10-01; no purchase)

| Item | Status | Where |
|---|---|---|
| Football fixtures-first gate | **IMPLEMENTED** | `ingestion/the_odds_api_loader.fixture_gate` (free `/events`); `run_daily_scan.gated_odds_config` |
| Tennis upcoming-event gate | **IMPLEMENTED** | `run_tennis_prediction_board.has_upcoming_event` (free `/events` per active key) |
| Tennis cap 120 → 150; tennis/NBA floor 150 → 100; football hard floor 25 | **IMPLEMENTED** | `config/api_budget.json` (cap sum 420 ≤ target 425 ≤ 500 − reserve 75; tested) |
| Credit accounting | **IMPLEMENTED** | `ops/credit_ledger.py` → `status/credit_ledger.csv` (paid and skipped calls); `scripts/credit_report.py` → `reports/credit_report.{json,md}` (daily, settlement workflow) |
| Football paper settlement → football-data.co.uk | **DEFERRED (by design)** | Approved *only after* the migration shadow gate passes. It currently fails (0 of 100 comparisons; no pending bets have played since 24 Sep). Implementation will be a separate bounded change when `status/settlement_shadow.json` shows `passed: true`. Until then the Odds API scores path is unchanged (it already skips leagues with nothing started). |

## Football gate

The scan pays for a league only if, at run time, the league lists at least one fixture kicking off within **48h**. It also requires the account to have **≥ 25 credits remaining**.

- **48h** = `config/api_budget.json` `fixture_gate_hours`. A test asserts it equals the unified ledger's `FOOTBALL_WINDOW_MIN`, i.e. the FIRST_SCAN_WITHIN_48H window.
- **25** = the hard floor, `hard_floor_remaining`.

**No decision-time data is lost:**
- Every fixture that can reach the ledger (48h window) still causes the league's odds to be fetched, at the same snapshot as before.
- The same holds for the Money Card (24h horizon).
- When a league qualifies, all of its listed fixtures are fetched.

**Fail-safe behaviour:**
- Unparseable kickoff times count as in-horizon: on doubt, the scan pays rather than skips.
- Each skipped league appears in the card's system warnings and in the credit ledger.

## Tennis gate

The tennis board pays for an active key only if it lists **at least one event that hasn't started**.

**No time horizon is applied**, deliberately. A horizon would change which scan produces each event's canonical first prediction. That would be a change to the frozen tennis prospective protocol, so it is out of scope for a credit fix.

Savings are therefore modest: a key is skipped only when it has nothing upcoming.

## Accounting

Each paid or skipped call is recorded with:
- the credits charged;
- the estimated credits saved (markets × regions of the skipped call);
- the account counters.

`credit_report` compares the actual month-to-date spend with the Plan A projections and with the ungated football counterfactual (6 credits/day).

**Not yet in the shared ledger:** settlement `/scores` calls and NBA calls. NBA has its own log, which the report reads. The account counter covers everything.
