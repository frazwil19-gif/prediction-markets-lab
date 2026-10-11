# Odds API credit report — 2026-10 (generated 2026-10-11T00:12Z)

Account credits used this month (latest logged counter): **125** of 500
Naive month-end projection at the current rate: 352 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 18 | 27 | 36 | 54 |
| football_shadow_scan | 18 | 18 | 72 | 72 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 45 | 45 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 25.7–36.7 | 27 |
| football_settlement | 0.0–7.3 | 0 |
| tennis_prediction_board | 36.7–55.0 | 45 |
| nba_prediction_board | 7.3–22.0 | 0 |

Football: 27 credits over 9 scan days vs 54 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 11)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 27 | 133 | 16.9 | 76.1 | 814 | 0 | under-used (projected 76.1 of 160); candidate to release ~83 credits — review, no auto change |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 45 | 105 | 30.0 | 126.8 | 177 | 0 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 9 | 31 | 22.5 | 25.4 | 42 | 0 | on plan |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
