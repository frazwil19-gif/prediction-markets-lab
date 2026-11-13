# Odds API credit report — 2026-11 (generated 2026-11-13T01:46Z)

Account credits used this month (latest logged counter): **214** of 500
Naive month-end projection at the current rate: 494 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 3 | 3 |
| football_daily_scan | 32 | 48 | 46 | 69 |
| football_shadow_scan | 17 | 17 | 113 | 113 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 24 | 0 | 0 |
| tennis_prediction_board | 20 | 20 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 30.3–43.3 | 48 |
| football_settlement | 0.0–8.7 | 0 |
| tennis_prediction_board | 43.3–65.0 | 20 |
| nba_prediction_board | 8.7–26.0 | 24 |

Football: 48 credits over 12 scan days vs 72 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 13)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 110.8 | 708 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 20 | 130 | 13.3 | 46.2 | 77 | 1 | under-used (projected 46.2 of 150); candidate to release ~103 credits — review, no auto change |
| nba_prediction_board | 55 | 24 | 31 | 43.6 | 55.4 | 86 | 0 | on pace to exceed cap (55.4 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 92.3 | 102 | 0 | on pace to exceed cap (92.3 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
