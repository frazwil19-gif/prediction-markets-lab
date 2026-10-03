# Odds API credit report — 2026-10 (generated 2026-10-03T23:44Z)

Account credits used this month (latest logged counter): **24** of 500
Naive month-end projection at the current rate: 248 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 0 | 0 | 12 | 18 |
| football_shadow_scan | 0 | 0 | 20 | 20 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 1 | 0 | 0 | 0 |
| tennis_prediction_board | 15 | 15 | 0 | 0 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 7.0–10.0 | 0 |
| football_settlement | 0.0–2.0 | 0 |
| tennis_prediction_board | 10.0–15.0 | 15 |
| nba_prediction_board | 2.0–6.0 | 0 |

Football: 0 credits over 2 scan days vs 12 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).
