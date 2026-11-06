# Odds API credit report — 2026-11 (generated 2026-11-06T01:29Z)

Account credits used this month (latest logged counter): **109** of 500
Naive month-end projection at the current rate: 545 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 15 | 23 | 15 | 22 |
| football_shadow_scan | 13 | 13 | 37 | 37 |
| market_probe_c3 | 0 | 0 | 367 | 734 |
| nba_prediction_board | 0 | 11 | 0 | 0 |
| tennis_prediction_board | 10 | 10 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 14.0–20.0 | 23 |
| football_settlement | 0.0–4.0 | 0 |
| tennis_prediction_board | 20.0–30.0 | 10 |
| nba_prediction_board | 4.0–12.0 | 11 |

Football: 23 credits over 5 scan days vs 30 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 6)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 23 | 137 | 14.4 | 115.0 | 291 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 10 | 140 | 6.7 | 50.0 | 65 | 0 | on plan |
| nba_prediction_board | 55 | 11 | 44 | 20.0 | 55.0 | 35 | 0 | on plan |
| us_sports_board | 40 | 21 | 19 | 52.5 | 105.0 | 49 | 0 | on pace to exceed cap (105.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
