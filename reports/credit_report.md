# Odds API credit report — 2026-10 (generated 2026-10-12T00:27Z)

Account credits used this month (latest logged counter): **159** of 500
Naive month-end projection at the current rate: 411 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 24 | 36 | 36 | 54 |
| football_shadow_scan | 22 | 22 | 78 | 78 |
| market_probe_c3 | 0 | 0 | 2 | 4 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 49 | 49 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 28.0–40.0 | 36 |
| football_settlement | 0.0–8.0 | 0 |
| tennis_prediction_board | 40.0–60.0 | 49 |
| nba_prediction_board | 8.0–24.0 | 0 |

Football: 36 credits over 10 scan days vs 60 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 12)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 36 | 124 | 22.5 | 93.0 | 845 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 49 | 101 | 32.7 | 126.6 | 223 | 0 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 15 | 25 | 37.5 | 38.8 | 46 | 0 | on plan |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
