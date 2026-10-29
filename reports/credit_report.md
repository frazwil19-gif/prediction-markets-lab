# Odds API credit report — 2026-10 (generated 2026-10-29T00:46Z)

Account credits used this month (latest logged counter): **408** of 500
Naive month-end projection at the current rate: 436 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 74 | 114 | 88 | 129 |
| football_shadow_scan | 25 | 25 | 245 | 245 |
| market_probe_c3 | 0 | 0 | 2262 | 4524 |
| nba_prediction_board | 0 | 12 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 84 | 84 | 23 | 23 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 67.7–96.7 | 114 |
| football_settlement | 0.0–19.3 | 0 |
| tennis_prediction_board | 96.7–145.0 | 84 |
| nba_prediction_board | 19.3–58.0 | 12 |

Football: 114 credits over 26 scan days vs 156 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 29)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 114 | 46 | 71.2 | 121.9 | 1696 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 84 | 66 | 56.0 | 89.8 | 299 | 2 | on plan |
| nba_prediction_board | 55 | 12 | 43 | 21.8 | 12.8 | 43 | 0 | under-used (projected 12.8 of 55); candidate to release ~42 credits — review, no auto change |
| us_sports_board | 40 | 40 | 0 | 100.0 | 42.8 | 113 | 0 | on pace to exceed cap (42.8 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.1 | 0 | 0 | under-used (projected 1.1 of 25); candidate to release ~23 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
