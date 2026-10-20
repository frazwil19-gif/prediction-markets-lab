# Odds API credit report — 2026-10 (generated 2026-10-20T23:47Z)

Account credits used this month (latest logged counter): **319** of 500
Naive month-end projection at the current rate: 494 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 6 | 6 |
| football_daily_scan | 54 | 84 | 66 | 96 |
| football_shadow_scan | 25 | 25 | 175 | 175 |
| market_probe_c3 | 0 | 0 | 979 | 1958 |
| nba_prediction_board | 0 | 1 | 0 | 0 |
| pre_close_capture | 1 | 1 | 1 | 1 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 76 | 76 | 4 | 4 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 46.7–66.7 | 84 |
| football_settlement | 0.0–13.3 | 0 |
| tennis_prediction_board | 66.7–100.0 | 76 |
| nba_prediction_board | 13.3–40.0 | 1 |

Football: 84 credits over 19 scan days vs 114 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 20)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 84 | 76 | 52.5 | 130.2 | 1296 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 76 | 74 | 50.7 | 117.8 | 291 | 2 | on plan |
| nba_prediction_board | 55 | 1 | 54 | 1.8 | 1.6 | 8 | 0 | under-used (projected 1.6 of 55); candidate to release ~53 credits — review, no auto change |
| us_sports_board | 40 | 40 | 0 | 100.0 | 62.0 | 113 | 0 | on pace to exceed cap (62.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 1 | 24 | 4.0 | 1.6 | 0 | 0 | under-used (projected 1.6 of 25); candidate to release ~23 credits — review, no auto change |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
