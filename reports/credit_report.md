# Odds API credit report — 2026-10 (generated 2026-10-15T23:39Z)

Account credits used this month (latest logged counter): **235** of 500
Naive month-end projection at the current rate: 486 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 5 | 5 |
| football_daily_scan | 34 | 53 | 56 | 82 |
| football_shadow_scan | 25 | 25 | 125 | 125 |
| market_probe_c3 | 0 | 0 | 399 | 798 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| pre_close_capture | 1 | 1 | 0 | 0 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 63 | 63 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 35.0–50.0 | 53 |
| football_settlement | 0.0–10.0 | 0 |
| tennis_prediction_board | 50.0–75.0 | 63 |
| nba_prediction_board | 10.0–30.0 | 0 |

Football: 53 credits over 14 scan days vs 84 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 15)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 53 | 107 | 33.1 | 109.5 | 955 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 63 | 87 | 42.0 | 130.2 | 264 | 2 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 30 | 10 | 75.0 | 62.0 | 79 | 0 | on pace to exceed cap (62.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 2.1 | 0 | 0 | under-used (projected 2.1 of 25); candidate to release ~22 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
