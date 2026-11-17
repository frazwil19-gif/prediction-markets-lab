# Odds API credit report — 2026-11 (generated 2026-11-17T03:41Z)

Account credits used this month (latest logged counter): **245** of 500
Naive month-end projection at the current rate: 432 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 32 | 48 | 70 | 105 |
| football_shadow_scan | 17 | 17 | 153 | 153 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 32 | 0 | 0 |
| tennis_prediction_board | 33 | 33 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 39.7–56.7 | 48 |
| football_settlement | 0.0–11.3 | 0 |
| tennis_prediction_board | 56.7–85.0 | 33 |
| nba_prediction_board | 11.3–34.0 | 32 |

Football: 48 credits over 16 scan days vs 96 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 17)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 84.7 | 708 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 33 | 117 | 22.0 | 58.2 | 89 | 1 | under-used (projected 58.2 of 150); candidate to release ~91 credits — review, no auto change |
| nba_prediction_board | 55 | 32 | 23 | 58.2 | 56.5 | 117 | 0 | on pace to exceed cap (56.5 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 70.6 | 102 | 0 | on pace to exceed cap (70.6 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
