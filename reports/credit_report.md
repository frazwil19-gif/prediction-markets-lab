# Odds API credit report — 2026-10 (generated 2026-10-14T00:15Z)

Account credits used this month (latest logged counter): **200** of 500
Naive month-end projection at the current rate: 443 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| clv_capture | 0 | 0 | 3 | 3 |
| football_daily_scan | 29 | 46 | 49 | 71 |
| football_shadow_scan | 25 | 25 | 105 | 105 |
| market_probe_c3 | 0 | 0 | 199 | 398 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 2 | 2 | 0 | 0 |
| tennis_prediction_board | 55 | 55 | 2 | 2 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 32.7–46.7 | 46 |
| football_settlement | 0.0–9.3 | 0 |
| tennis_prediction_board | 46.7–70.0 | 55 |
| nba_prediction_board | 9.3–28.0 | 0 |

Football: 46 credits over 12 scan days vs 72 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-10, day 14)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 46 | 114 | 28.8 | 101.9 | 930 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 55 | 95 | 36.7 | 121.8 | 250 | 1 | on plan |
| nba_prediction_board | 55 | 0 | 55 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| us_sports_board | 40 | 22 | 18 | 55.0 | 48.7 | 65 | 0 | on pace to exceed cap (48.7 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
