# Odds API credit report — 2026-10 (generated 2026-10-18T23:00Z)

Account credits used this month (latest logged counter): **297** of 500
Naive month-end projection at the current rate: 512 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 51 | 78 | 57 | 84 |
| football_shadow_scan | 25 | 25 | 155 | 155 |
| market_probe_c3 | 0 | 0 | 673 | 1346 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 72 | 72 | 4 | 4 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 42.0–60.0 | 78 |
| football_settlement | 0.0–12.0 | 0 |
| tennis_prediction_board | 60.0–90.0 | 72 |
| nba_prediction_board | 12.0–36.0 | 0 |

Football: 78 credits over 17 scan days vs 102 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 18)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 78 | 82 | 48.8 | 134.3 | 1289 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 72 | 78 | 48.0 | 124.0 | 281 | 2 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 39 | 1 | 97.5 | 67.2 | 109 | 0 | on pace to exceed cap (67.2 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.7 | 0 | 0 | under-used (projected 1.7 of 25); candidate to release ~23 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
