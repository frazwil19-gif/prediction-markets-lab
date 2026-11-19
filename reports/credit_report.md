# Odds API credit report — 2026-11 (generated 2026-11-19T02:29Z)

Account credits used this month (latest logged counter): **256** of 500
Naive month-end projection at the current rate: 404 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 32 | 48 | 82 | 123 |
| football_shadow_scan | 17 | 17 | 173 | 173 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 36 | 0 | 0 |
| tennis_prediction_board | 36 | 36 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 44.3–63.3 | 48 |
| football_settlement | 0.0–12.7 | 0 |
| tennis_prediction_board | 63.3–95.0 | 36 |
| nba_prediction_board | 12.7–38.0 | 36 |

Football: 48 credits over 18 scan days vs 108 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 19)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 75.8 | 708 | 0 | under-used (projected 75.8 of 160); candidate to release ~84 credits — review, no auto change |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 36 | 114 | 24.0 | 56.8 | 93 | 1 | under-used (projected 56.8 of 150); candidate to release ~93 credits — review, no auto change |
| nba_prediction_board | 55 | 36 | 19 | 65.5 | 56.8 | 134 | 0 | on pace to exceed cap (56.8 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 63.2 | 102 | 0 | on pace to exceed cap (63.2 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
