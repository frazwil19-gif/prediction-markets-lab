# Odds API credit report — 2026-11 (generated 2026-11-03T02:53Z)

Account credits used this month (latest logged counter): **51** of 500
Naive month-end projection at the current rate: 510 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 8 | 12 | 4 | 6 |
| football_shadow_scan | 7 | 7 | 13 | 13 |
| market_probe_c3 | 0 | 0 | 150 | 300 |
| nba_prediction_board | 0 | 4 | 0 | 0 |
| tennis_prediction_board | 4 | 4 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 7.0–10.0 | 12 |
| football_settlement | 0.0–2.0 | 0 |
| tennis_prediction_board | 10.0–15.0 | 4 |
| nba_prediction_board | 2.0–6.0 | 4 |

Football: 12 credits over 2 scan days vs 12 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 3)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 12 | 148 | 7.5 | 120.0 | 208 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 4 | 146 | 2.7 | 40.0 | 45 | 0 | on plan |
| nba_prediction_board | 55 | 4 | 51 | 7.3 | 40.0 | 19 | 0 | on plan |
| us_sports_board | 40 | 8 | 32 | 20.0 | 80.0 | 22 | 0 | on pace to exceed cap (80.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
