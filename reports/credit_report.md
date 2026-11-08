# Odds API credit report — 2026-11 (generated 2026-11-08T00:24Z)

Account credits used this month (latest logged counter): **154** of 500
Naive month-end projection at the current rate: 578 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 1 | 1 |
| football_daily_scan | 27 | 41 | 15 | 22 |
| football_shadow_scan | 17 | 17 | 53 | 53 |
| market_probe_c3 | 0 | 0 | 561 | 1122 |
| nba_prediction_board | 0 | 15 | 0 | 0 |
| tennis_prediction_board | 13 | 13 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 18.7–26.7 | 41 |
| football_settlement | 0.0–5.3 | 0 |
| tennis_prediction_board | 26.7–40.0 | 13 |
| nba_prediction_board | 5.3–16.0 | 15 |

Football: 41 credits over 7 scan days vs 42 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 8)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 41 | 119 | 25.6 | 153.8 | 708 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 13 | 137 | 8.7 | 48.8 | 68 | 0 | under-used (projected 48.8 of 150); candidate to release ~101 credits — review, no auto change |
| nba_prediction_board | 55 | 15 | 40 | 27.3 | 56.2 | 51 | 0 | on pace to exceed cap (56.2 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 28 | 12 | 70.0 | 105.0 | 77 | 0 | on pace to exceed cap (105.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
