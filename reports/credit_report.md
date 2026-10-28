# Odds API credit report — 2026-10 (generated 2026-10-28T00:25Z)

Account credits used this month (latest logged counter): **406** of 500
Naive month-end projection at the current rate: 450 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 73 | 112 | 83 | 122 |
| football_shadow_scan | 25 | 25 | 235 | 235 |
| market_probe_c3 | 0 | 0 | 2162 | 4324 |
| nba_prediction_board | 0 | 12 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 84 | 84 | 17 | 17 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 65.3–93.3 | 112 |
| football_settlement | 0.0–18.7 | 0 |
| tennis_prediction_board | 93.3–140.0 | 84 |
| nba_prediction_board | 18.7–56.0 | 12 |

Football: 112 credits over 25 scan days vs 150 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 28)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 112 | 48 | 70.0 | 124.0 | 1696 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 84 | 66 | 56.0 | 93.0 | 299 | 2 | on plan |
| nba_prediction_board | 55 | 12 | 43 | 21.8 | 13.3 | 43 | 0 | under-used (projected 13.3 of 55); candidate to release ~41 credits — review, no auto change |
| us_sports_board | 40 | 40 | 0 | 100.0 | 44.3 | 113 | 0 | on pace to exceed cap (44.3 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.1 | 0 | 0 | under-used (projected 1.1 of 25); candidate to release ~23 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
