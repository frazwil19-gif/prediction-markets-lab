# Odds API credit report — 2026-11 (generated 2026-11-25T04:05Z)

Account credits used this month (latest logged counter): **351** of 500
Naive month-end projection at the current rate: 421 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 61 | 95 | 101 | 148 |
| football_shadow_scan | 23 | 23 | 247 | 247 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 48 | 0 | 0 |
| tennis_prediction_board | 44 | 44 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 58.3–83.3 | 95 |
| football_settlement | 0.0–16.7 | 0 |
| tennis_prediction_board | 83.3–125.0 | 44 |
| nba_prediction_board | 16.7–50.0 | 48 |

Football: 95 credits over 24 scan days vs 144 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 25)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 95 | 65 | 59.4 | 114.0 | 1316 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 44 | 106 | 29.3 | 52.8 | 98 | 1 | under-used (projected 52.8 of 150); candidate to release ~97 credits — review, no auto change |
| nba_prediction_board | 55 | 48 | 7 | 87.3 | 57.6 | 173 | 0 | on pace to exceed cap (57.6 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 48.0 | 102 | 0 | on pace to exceed cap (48.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
