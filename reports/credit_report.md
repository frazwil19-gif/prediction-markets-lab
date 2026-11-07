# Odds API credit report — 2026-11 (generated 2026-11-07T00:50Z)

Account credits used this month (latest logged counter): **129** of 500
Naive month-end projection at the current rate: 553 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 1 | 1 |
| football_daily_scan | 21 | 32 | 15 | 22 |
| football_shadow_scan | 17 | 17 | 43 | 43 |
| market_probe_c3 | 0 | 0 | 462 | 924 |
| nba_prediction_board | 0 | 12 | 0 | 0 |
| tennis_prediction_board | 12 | 12 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 16.3–23.3 | 32 |
| football_settlement | 0.0–4.7 | 0 |
| tennis_prediction_board | 23.3–35.0 | 12 |
| nba_prediction_board | 4.7–14.0 | 12 |

Football: 32 credits over 6 scan days vs 36 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 7)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 32 | 128 | 20.0 | 137.1 | 574 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 12 | 138 | 8.0 | 51.4 | 66 | 0 | under-used (projected 51.4 of 150); candidate to release ~98 credits — review, no auto change |
| nba_prediction_board | 55 | 12 | 43 | 21.8 | 51.4 | 44 | 0 | on plan |
| us_sports_board | 40 | 22 | 18 | 55.0 | 94.3 | 52 | 0 | on pace to exceed cap (94.3 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
