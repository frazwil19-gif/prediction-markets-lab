# Odds API credit report — 2026-10 (generated 2026-10-14T23:51Z)

Account credits used this month (latest logged counter): **214** of 500
Naive month-end projection at the current rate: 474 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 5 | 5 |
| football_daily_scan | 30 | 48 | 54 | 78 |
| football_shadow_scan | 25 | 25 | 115 | 115 |
| market_probe_c3 | 0 | 0 | 299 | 598 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| pre_close_capture | 1 | 1 | 0 | 0 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 59 | 59 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 32.7–46.7 | 48 |
| football_settlement | 0.0–9.3 | 0 |
| tennis_prediction_board | 46.7–70.0 | 59 |
| nba_prediction_board | 9.3–28.0 | 0 |

Football: 48 credits over 13 scan days vs 78 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 14)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 48 | 112 | 30.0 | 106.3 | 930 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 59 | 91 | 39.3 | 130.6 | 260 | 1 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 24 | 16 | 60.0 | 53.1 | 68 | 0 | on pace to exceed cap (53.1 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 2.2 | 0 | 0 | under-used (projected 2.2 of 25); candidate to release ~22 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
