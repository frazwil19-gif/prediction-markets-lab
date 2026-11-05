# Odds API credit report — 2026-11 (generated 2026-11-05T01:26Z)

Account credits used this month (latest logged counter): **81** of 500
Naive month-end projection at the current rate: 486 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 10 | 16 | 14 | 20 |
| football_shadow_scan | 9 | 9 | 31 | 31 |
| market_probe_c3 | 0 | 0 | 293 | 586 |
| nba_prediction_board | 0 | 8 | 0 | 0 |
| tennis_prediction_board | 8 | 8 | 1 | 1 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 11.7–16.7 | 16 |
| football_settlement | 0.0–3.3 | 0 |
| tennis_prediction_board | 16.7–25.0 | 8 |
| nba_prediction_board | 3.3–10.0 | 8 |

Football: 16 credits over 4 scan days vs 24 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).

## Credit utilisation review (2026-11, day 5)

| Consumer | Allocation | Consumed | Unused | Util % | Proj. month-end | Predictions | Qualifying bets | Recommendation |
|---|---|---|---|---|---|---|---|---|
| football_daily_scan | 160 | 16 | 144 | 10.0 | 96.0 | 235 | 0 | on plan |
| football_settlement | 20 | 0 | 20 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| tennis_prediction_board | 150 | 8 | 142 | 5.3 | 48.0 | 59 | 0 | on plan |
| nba_prediction_board | 55 | 8 | 47 | 14.5 | 48.0 | 33 | 0 | on plan |
| us_sports_board | 40 | 15 | 25 | 37.5 | 90.0 | 38 | 0 | on pace to exceed cap (90.0 > 40); budget guard will stop it — review |
| pre_close_capture | 25 | 0 | 25 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |
| clv_capture | 100 | 0 | 100 | 0.0 | 0.0 | 0 | 0 | idle so far (fixture gate / season not started / nothing to settle) — not evidence of over-allocation; review at month end |

Early-month projections are noisy; season starts (NBA 20 Oct) change the picture. Recommendations are advisory — any cap change is a versioned config change approved by Fraser.
