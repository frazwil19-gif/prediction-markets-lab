# Odds API credit report — 2026-11 (generated 2026-11-27T03:36Z)

Account credits used this month (latest logged counter): **383** of 500
Naive month-end projection at the current rate: 426 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 74 | 115 | 112 | 164 |
| football_shadow_scan | 25 | 24 | 285 | 285 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 52 | 0 | 0 |
| tennis_prediction_board | 44 | 44 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 63.0–90.0 | 115 |
| football_settlement | 0.0–18.0 | 0 |
| tennis_prediction_board | 90.0–135.0 | 44 |
| nba_prediction_board | 18.0–54.0 | 52 |

Football: 115 credits over 26 scan days vs 156 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 27)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 115 | 45 | 71.9 | 127.8 | 1539 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 44 | 106 | 29.3 | 48.9 | 98 | 1 | under-used (projected 48.9 of 150); candidate to release ~101 credits — review, no auto change |
| nba_prediction_board | 55 | 52 | 3 | 94.5 | 57.8 | 187 | 0 | on pace to exceed cap (57.8 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 44.4 | 102 | 0 | on pace to exceed cap (44.4 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
