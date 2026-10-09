# Odds API credit report — 2026-10 (generated 2026-10-09T01:11Z)

Account credits used this month (latest logged counter): **68** of 500
Naive month-end projection at the current rate: 234 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 6 | 9 | 36 | 54 |
| football_shadow_scan | 10 | 10 | 60 | 60 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 1 | 0 | 0 | 0 |
| tennis_prediction_board | 38 | 38 | 0 | 0 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 21.0–30.0 | 9 |
| football_settlement | 0.0–6.0 | 0 |
| tennis_prediction_board | 30.0–45.0 | 38 |
| nba_prediction_board | 6.0–18.0 | 0 |

Football: 9 credits over 7 scan days vs 42 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 9)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 9 | 151 | 5.6 | 31.0 | 488 | 0 | under-used (projected 31.0 of 160); candidate to release ~129 credits — review, no auto change |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 38 | 112 | 25.3 | 130.9 | 159 | 0 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 2 | 38 | 5.0 | 6.9 | 11 | 0 | under-used (projected 6.9 of 40); candidate to release ~33 credits — review, no auto change |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
