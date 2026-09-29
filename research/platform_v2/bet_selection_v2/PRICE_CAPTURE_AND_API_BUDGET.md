# V2-6 Price Capture and API Budget (pre-registered 2026-09-29)

## Rule: no new paid consumer
V2-6 adds **0 Odds API credits**. It only reads prices that production already buys:
| source | where it comes from | cost |
|---|---|---|
| tennis Betfair back (predicted side) | unified ledger `live_price` (from the tennis board's existing odds call) | 0 |
| tennis bookmaker h2h, all UK books | `tennis_predictions/price_snapshots.csv`, written from the **same** response the tennis board already fetches | 0 |
| football best price per selection | daily card `available_odds` / `bookmaker` / `price_timestamp` | 0 |
| Double Chance executable prices | **not fetched** (DC is PROVISIONAL_PROSPECTIVE; at most WATCH; a price would change no decision) | 0 |

A selective extra price call (for example a screened DC price) is designed as a hook that is **disabled**. It may only be
enabled after (a) its market key and per-call cost are verified on one manual call, (b) a monthly forecast shows the total
stays ≤ 425 with ≥ 75 reserve, and (c) only candidates that already passed probability/evidence screening are priced. Core
prospective collection keeps priority: optional consumers stop first (`config/api_budget.json` unchanged).

## Observed usage (credit_log.csv, Odds API headers)
- 23 Sep 20:05: 41 used / 459 remaining → 28 Sep 21:21: **88 used / 412 remaining** (September, monthly plan 500).
- Pattern: daily_scan ≈ 6/day (logged indirectly: +6 between consecutive tennis logs around each scan); tennis board = 1 per
  active key per board (0 when no key is active); settlement 0 since the V2-5 guard (no pending bet in the 3-day window).

## Forecast for October (not a promise; caps and floors enforce it)
| consumer | basis | credits |
|---|---|---|
| football daily_scan (core) | 6 × 31 | 186 |
| football settlement (core) | V2-5 guard; fixtures resume 9 Oct | 0–40 |
| tennis boards (optional, cap 120) | 1–2 keys × 2 boards on tournament days | 60–120 |
| NBA (optional, cap 60, from 20 Oct) | ≤ 1 odds/day + scores every 3rd day | ~35 |
| **V2-6 bet selection** | reuse only | **0** |
| **total** | | **~281–381** (target ≤ 425, reserve ≥ 75 holds) |
