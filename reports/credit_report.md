# Odds API credit report — 2026-10 (generated 2026-10-03T00:23Z)

Account credits used this month (latest logged counter): **18** of 500
Naive month-end projection at the current rate: 186 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 0 | 0 | 6 | 9 |
| football_shadow_scan | 0 | 0 | 10 | 10 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 1 | 0 | 0 | 0 |
| tennis_prediction_board | 9 | 9 | 0 | 0 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 7.0–10.0 | 0 |
| football_settlement | 0.0–2.0 | 0 |
| tennis_prediction_board | 10.0–15.0 | 9 |
| nba_prediction_board | 2.0–6.0 | 0 |

Football: 0 credits over 1 scan days vs 6 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).
