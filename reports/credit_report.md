# Odds API credit report — 2026-11 (generated 2026-11-02T00:32Z)

Account credits used this month (latest logged counter): **29** of 500
Naive month-end projection at the current rate: 435 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 5 | 7 | 1 | 2 |
| football_shadow_scan | 4 | 4 | 6 | 6 |
| market_probe_c3 | 0 | 0 | 43 | 86 |
| nba_prediction_board | 0 | 3 | 0 | 0 |
| tennis_prediction_board | 3 | 3 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 4.7–6.7 | 7 |
| football_settlement | 0.0–1.3 | 0 |
| tennis_prediction_board | 6.7–10.0 | 3 |
| nba_prediction_board | 1.3–4.0 | 3 |

Football: 7 credits over 1 scan days vs 6 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 2)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 7 | 153 | 4.4 | 105.0 | 145 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 3 | 147 | 2.0 | 45.0 | 43 | 0 | on plan |
| nba_prediction_board | 55 | 3 | 52 | 5.5 | 45.0 | 4 | 0 | on plan |
| us_sports_board | 40 | 6 | 34 | 15.0 | 90.0 | 18 | 0 | on pace to exceed cap (90.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
