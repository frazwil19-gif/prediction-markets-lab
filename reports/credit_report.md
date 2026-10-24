# Odds API credit report — 2026-10 (generated 2026-10-24T23:05Z)

Account credits used this month (latest logged counter): **374** of 500
Naive month-end projection at the current rate: 483 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 66 | 102 | 72 | 105 |
| football_shadow_scan | 25 | 25 | 205 | 205 |
| market_probe_c3 | 0 | 0 | 1730 | 3460 |
| nba_prediction_board | 0 | 9 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 84 | 84 | 5 | 5 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 56.0–80.0 | 102 |
| football_settlement | 0.0–16.0 | 0 |
| tennis_prediction_board | 80.0–120.0 | 84 |
| nba_prediction_board | 16.0–48.0 | 9 |

Football: 102 credits over 22 scan days vs 132 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 24)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 102 | 58 | 63.8 | 131.8 | 1648 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 84 | 66 | 56.0 | 108.5 | 299 | 2 | on plan |
| nba_prediction_board | 55 | 9 | 46 | 16.4 | 11.6 | 36 | 0 | under-used (projected 11.6 of 55); candidate to release ~43 credits — review, no auto change |
| us_sports_board | 40 | 40 | 0 | 100.0 | 51.7 | 113 | 0 | on pace to exceed cap (51.7 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.3 | 0 | 0 | under-used (projected 1.3 of 25); candidate to release ~23 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
