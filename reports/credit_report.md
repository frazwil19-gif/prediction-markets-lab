# Odds API credit report — 2026-11 (generated 2026-11-04T01:13Z)

Account credits used this month (latest logged counter): **68** of 500
Naive month-end projection at the current rate: 510 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 9 | 14 | 9 | 13 |
| football_shadow_scan | 8 | 8 | 22 | 22 |
| market_probe_c3 | 0 | 0 | 205 | 410 |
| nba_prediction_board | 0 | 7 | 0 | 0 |
| tennis_prediction_board | 6 | 6 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 9.3–13.3 | 14 |
| football_settlement | 0.0–2.7 | 0 |
| tennis_prediction_board | 13.3–20.0 | 6 |
| nba_prediction_board | 2.7–8.0 | 7 |

Football: 14 credits over 3 scan days vs 18 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 4)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 14 | 146 | 8.8 | 105.0 | 235 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 6 | 144 | 4.0 | 45.0 | 52 | 0 | on plan |
| nba_prediction_board | 55 | 7 | 48 | 12.7 | 52.5 | 23 | 0 | on plan |
| us_sports_board | 40 | 13 | 27 | 32.5 | 97.5 | 33 | 0 | on pace to exceed cap (97.5 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
