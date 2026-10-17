# Odds API credit report — 2026-10 (generated 2026-10-17T23:01Z)

Account credits used this month (latest logged counter): **277** of 500
Naive month-end projection at the current rate: 505 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 46 | 71 | 56 | 82 |
| football_shadow_scan | 25 | 25 | 145 | 145 |
| market_probe_c3 | 0 | 0 | 589 | 1178 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 71 | 71 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 39.7–56.7 | 71 |
| football_settlement | 0.0–11.3 | 0 |
| tennis_prediction_board | 56.7–85.0 | 71 |
| nba_prediction_board | 11.3–34.0 | 0 |

Football: 71 credits over 16 scan days vs 96 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 17)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 71 | 89 | 44.4 | 129.5 | 1281 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 71 | 79 | 47.3 | 129.5 | 269 | 2 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 37 | 3 | 92.5 | 67.5 | 106 | 0 | on pace to exceed cap (67.5 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.8 | 0 | 0 | under-used (projected 1.8 of 25); candidate to release ~23 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
