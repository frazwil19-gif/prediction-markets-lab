# Odds API credit report — 2026-10 (generated 2026-10-13T02:32Z)

Account credits used this month (latest logged counter): **184** of 500
Naive month-end projection at the current rate: 439 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 3 | 3 |
| football_daily_scan | 28 | 44 | 44 | 64 |
| football_shadow_scan | 25 | 25 | 95 | 95 |
| market_probe_c3 | 0 | 0 | 109 | 218 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 51 | 51 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 30.3–43.3 | 44 |
| football_settlement | 0.0–8.7 | 0 |
| tennis_prediction_board | 43.3–65.0 | 51 |
| nba_prediction_board | 8.7–26.0 | 0 |

Football: 44 credits over 11 scan days vs 66 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 13)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 44 | 116 | 27.5 | 104.9 | 901 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 51 | 99 | 34.0 | 121.6 | 238 | 0 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 17 | 23 | 42.5 | 40.5 | 49 | 0 | on pace to exceed cap (40.5 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
