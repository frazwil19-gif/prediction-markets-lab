# Odds API credit report — 2026-11 (generated 2026-11-20T02:13Z)

Account credits used this month (latest logged counter): **267** of 500
Naive month-end projection at the current rate: 400 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 34 | 50 | 86 | 130 |
| football_shadow_scan | 19 | 19 | 181 | 181 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 39 | 0 | 0 |
| tennis_prediction_board | 38 | 38 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 46.7–66.7 | 50 |
| football_settlement | 0.0–13.3 | 0 |
| tennis_prediction_board | 66.7–100.0 | 38 |
| nba_prediction_board | 13.3–40.0 | 39 |

Football: 50 credits over 19 scan days vs 114 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 20)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 50 | 110 | 31.2 | 75.0 | 732 | 0 | under-used (projected 75.0 of 160); candidate to release ~85 credits — review, no auto change |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 38 | 112 | 25.3 | 57.0 | 95 | 1 | under-used (projected 57.0 of 150); candidate to release ~93 credits — review, no auto change |
| nba_prediction_board | 55 | 39 | 16 | 70.9 | 58.5 | 138 | 0 | on pace to exceed cap (58.5 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 60.0 | 102 | 0 | on pace to exceed cap (60.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
