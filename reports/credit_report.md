# Odds API credit report — 2026-10 (generated 2026-10-31T00:39Z)

Account credits used this month (latest logged counter): **423** of 500
Naive month-end projection at the current rate: 423 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 83 | 127 | 91 | 134 |
| football_shadow_scan | 25 | 25 | 265 | 265 |
| market_probe_c3 | 0 | 0 | 2461 | 4922 |
| nba_prediction_board | 0 | 12 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 84 | 84 | 35 | 35 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 72.3–103.3 | 127 |
| football_settlement | 0.0–20.7 | 0 |
| tennis_prediction_board | 103.3–155.0 | 84 |
| nba_prediction_board | 20.7–62.0 | 12 |

Football: 127 credits over 28 scan days vs 168 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 31)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 127 | 33 | 79.4 | 127.0 | 1947 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 84 | 66 | 56.0 | 84.0 | 299 | 2 | on plan |
| nba_prediction_board | 55 | 12 | 43 | 21.8 | 12.0 | 43 | 0 | under-used (projected 12.0 of 55); candidate to release ~43 credits — review, no auto change |
| us_sports_board | 40 | 40 | 0 | 100.0 | 40.0 | 113 | 0 | on plan |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.0 | 0 | 0 | under-used (projected 1.0 of 25); candidate to release ~24 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
