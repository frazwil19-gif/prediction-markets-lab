# Odds API credit report — 2026-11 (generated 2026-11-21T02:06Z)

Account credits used this month (latest logged counter): **283** of 500
Naive month-end projection at the current rate: 404 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 40 | 59 | 86 | 130 |
| football_shadow_scan | 22 | 22 | 188 | 188 |
| market_probe_c3 | 0 | 0 | 757 | 1514 |
| nba_prediction_board | 0 | 40 | 0 | 0 |
| tennis_prediction_board | 40 | 40 | 3 | 3 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 49.0–70.0 | 59 |
| football_settlement | 0.0–14.0 | 0 |
| tennis_prediction_board | 70.0–105.0 | 40 |
| nba_prediction_board | 14.0–42.0 | 40 |

Football: 59 credits over 20 scan days vs 120 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 21)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 59 | 101 | 36.9 | 84.3 | 1068 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 40 | 110 | 26.7 | 57.1 | 96 | 1 | under-used (projected 57.1 of 150); candidate to release ~92 credits — review, no auto change |
| nba_prediction_board | 55 | 40 | 15 | 72.7 | 57.1 | 147 | 0 | on pace to exceed cap (57.1 > 55); budget guard will stop it — review |
| us_sports_board | 40 | 40 | 0 | 100.0 | 57.1 | 102 | 0 | on pace to exceed cap (57.1 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
