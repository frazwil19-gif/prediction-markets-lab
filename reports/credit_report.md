# Odds API credit report — 2026-10 (generated 2026-10-08T00:55Z)

Account credits used this month (latest logged counter): **43** of 500
Naive month-end projection at the current rate: 167 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 0 | 0 | 36 | 54 |
| football_shadow_scan | 0 | 0 | 60 | 60 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 1 | 0 | 0 | 0 |
| tennis_prediction_board | 34 | 34 | 0 | 0 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 18.7–26.7 | 0 |
| football_settlement | 0.0–5.3 | 0 |
| tennis_prediction_board | 26.7–40.0 | 34 |
| nba_prediction_board | 5.3–16.0 | 0 |

Football: 0 credits over 6 scan days vs 36 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).
