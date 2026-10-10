# Odds API credit report — 2026-10 (generated 2026-10-10T00:42Z)

Account credits used this month (latest logged counter): **95** of 500
Naive month-end projection at the current rate: 294 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 12 | 18 | 36 | 54 |
| football_shadow_scan | 14 | 14 | 66 | 66 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 1 | 0 | 0 | 0 |
| tennis_prediction_board | 42 | 42 | 0 | 0 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 23.3–33.3 | 18 |
| football_settlement | 0.0–6.7 | 0 |
| tennis_prediction_board | 33.3–50.0 | 42 |
| nba_prediction_board | 6.7–20.0 | 0 |

Football: 18 credits over 8 scan days vs 48 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 10)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 18 | 142 | 11.2 | 55.8 | 615 | 0 | under-used (projected 55.8 of 160); candidate to release ~104 credits — review, no auto change |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 42 | 108 | 28.0 | 130.2 | 169 | 0 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 7 | 33 | 17.5 | 21.7 | 16 | 0 | on plan |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
