# Odds API credit report — 2026-11 (generated 2026-11-22T01:09Z)

Account credits used this month (latest logged counter): **300** of 500
Naive month-end projection at the current rate: 409 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 46 | 68 | 86 | 130 |
| football_shadow_scan | 23 | 23 | 197 | 197 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 43 | 0 | 0 |
| tennis_prediction_board | 42 | 42 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 51.3–73.3 | 68 |
| football_settlement | 0.0–14.7 | 0 |
| tennis_prediction_board | 73.3–110.0 | 42 |
| nba_prediction_board | 14.7–44.0 | 43 |

Football: 68 credits over 21 scan days vs 126 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 22)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 68 | 92 | 42.5 | 92.7 | 1210 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 42 | 108 | 28.0 | 57.3 | 97 | 1 | under-used (projected 57.3 of 150); candidate to release ~92 credits — review, no auto change |
| nba_prediction_board | 55 | 43 | 12 | 78.2 | 58.6 | 153 | 0 | on pace to exceed cap (58.6 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 54.5 | 102 | 0 | on pace to exceed cap (54.5 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
