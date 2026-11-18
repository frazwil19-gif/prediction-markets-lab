# Odds API credit report — 2026-11 (generated 2026-11-18T02:50Z)

Account credits used this month (latest logged counter): **251** of 500
Naive month-end projection at the current rate: 418 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 32 | 48 | 76 | 114 |
| football_shadow_scan | 17 | 17 | 163 | 163 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 35 | 0 | 0 |
| tennis_prediction_board | 34 | 34 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 42.0–60.0 | 48 |
| football_settlement | 0.0–12.0 | 0 |
| tennis_prediction_board | 60.0–90.0 | 34 |
| nba_prediction_board | 12.0–36.0 | 35 |

Football: 48 credits over 17 scan days vs 102 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 18)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 80.0 | 708 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 34 | 116 | 22.7 | 56.7 | 91 | 1 | under-used (projected 56.7 of 150); candidate to release ~93 credits — review, no auto change |
| nba_prediction_board | 55 | 35 | 20 | 63.6 | 58.3 | 122 | 0 | on pace to exceed cap (58.3 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 66.7 | 102 | 0 | on pace to exceed cap (66.7 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
