# Odds API credit report — 2026-11 (generated 2026-11-09T00:43Z)

Account credits used this month (latest logged counter): **175** of 500
Naive month-end projection at the current rate: 583 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 1 | 1 |
| football_daily_scan | 32 | 48 | 16 | 24 |
| football_shadow_scan | 17 | 17 | 63 | 63 |
| market_probe_c3 | 0 | 0 | 662 | 1324 |
| nba_prediction_board | 0 | 16 | 0 | 0 |
| tennis_prediction_board | 14 | 14 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 21.0–30.0 | 48 |
| football_settlement | 0.0–6.0 | 0 |
| tennis_prediction_board | 30.0–45.0 | 14 |
| nba_prediction_board | 6.0–18.0 | 16 |

Football: 48 credits over 8 scan days vs 48 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 9)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 160.0 | 708 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 14 | 136 | 9.3 | 46.7 | 69 | 0 | under-used (projected 46.7 of 150); candidate to release ~103 credits — review, no auto change |
| nba_prediction_board | 55 | 16 | 39 | 29.1 | 53.3 | 58 | 0 | on plan |
| us_sports_board | 40 | 30 | 10 | 75.0 | 100.0 | 84 | 0 | on pace to exceed cap (100.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
