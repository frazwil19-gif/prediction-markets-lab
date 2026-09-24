# Production Recovery Log (V2-4 gate 0) — 2026-09-24

## Outage record
**22 Sep 2026 12:27 UTC → 24 Sep 2026 15:40 UTC: SYSTEM OUTAGE / NO PROSPECTIVE DATA.** Every scheduled workflow
failed at "Run the test suite first": two Backtest-Phase-1 tests read gitignored local data. There were no football
scans, no settlements and no tennis boards. **Nothing is reconstructed for this window.** The 6 WTA predictions
ledgered on 23 Sep 20:05 UTC (manual run, before their matches) remain valid prospective evidence.
Fix: `c4d7779` → pushed as `732f67a`/`1cd2259`.

## Verification evidence (GitHub Actions API)
| workflow | run id | trigger | commit | started → finished (UTC) | result | evidence |
|---|---|---|---|---|---|---|
| tests | 36021901773 | push | 1cd2259 | 15:40:33 → 15:42:01 | ✅ success | first clean-checkout pass since 22 Sep |
| daily_scan | 36023253292 | manual | 1cd2259 | 15:51:36 → 15:52:40 | ✅ success | tests passed; **38 fixtures, 190 candidates, 0 money-qualified** ("NO MONEY BETS QUALIFIED TODAY"); card.json/csv/md + money_card.json/md committed as `8a1b1b6`; status `last_scan: success`; Odds API credits used 42 → 48 (6, as expected) |
| tennis_prediction_board | 36023546752 | manual | 8a1b1b6 | 15:54:05 → 15:55:19 | ✅ success | tests passed; 1 active key (WTA Singapore); 3 events; 3 valid predictions; **1 new ledger row** (2 already predicted, correctly not overwritten); ledger prefix byte-identical to the 23 Sep version (immutability held); board `board_1555.md` committed as `074b145`; credits 48 → 49 |
| settlement_and_performance | — | next schedule (21:00 cron) | — | pending | ⏳ not yet verified | last run 23 Sep failed (outage). Its first post-fix run is the next check |

**Decision:** daily_scan and tennis board are **verified healthy**. Settlement will be verified at its next run
(a manual dispatch works too). The operator's gate (both named workflows green) is met, so V2-4 research may
begin, with settlement verification carried as an open item.

## Observations from the recovery runs (monitoring, no change to frozen engines)
- The board shows the *current* scan's probability for matches already in the ledger (for example Andreeva 70.6% ledgered vs
  77.3% on today's board). **The ledger's first prediction is the only one that counts.** A future board version
  should display the ledgered value and mark later snapshots as "re-quote".
- One match was rescheduled by the provider (Andreeva v Fernandez 25 Sep 03:00 → 10:30). The ledger keeps the original
  commence_time; settlement uses a ±21-day window, so it is unaffected.
- One exchange quote had a wide back/lay spread (1.40 / 1.72). A spread-width quality flag is a candidate for engine
  v2, not changed now.
- Paper ledger: 22 pending bets, and 4 have kickoffs that have passed (20 Sep). All 4 are Sep-19 backfill rows
  without provider ids, so the Odds API path can never settle them. The free-results adapter (below) can.
