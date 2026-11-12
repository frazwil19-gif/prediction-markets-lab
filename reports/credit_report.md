# Odds API credit report — 2026-11 (generated 2026-11-12T02:13Z)

Account credits used this month (latest logged counter): **208** of 500
Naive month-end projection at the current rate: 520 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 3 | 3 |
| football_daily_scan | 32 | 48 | 40 | 60 |
| football_shadow_scan | 17 | 17 | 103 | 103 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 23 | 0 | 0 |
| tennis_prediction_board | 18 | 18 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 28.0–40.0 | 48 |
| football_settlement | 0.0–8.0 | 0 |
| tennis_prediction_board | 40.0–60.0 | 18 |
| nba_prediction_board | 8.0–24.0 | 23 |

Football: 48 credits over 11 scan days vs 66 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 12)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 120.0 | 708 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 18 | 132 | 12.0 | 45.0 | 75 | 1 | under-used (projected 45.0 of 150); candidate to release ~105 credits — review, no auto change |
| nba_prediction_board | 55 | 23 | 32 | 41.8 | 57.5 | 82 | 0 | on pace to exceed cap (57.5 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 100.0 | 102 | 0 | on pace to exceed cap (100.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
