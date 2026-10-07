# Odds API credit report — 2026-10 (generated 2026-10-07T00:35Z)

Account credits used this month (latest logged counter): **41** of 500
Naive month-end projection at the current rate: 182 (shadow football tiers throttle themselves before the reserve; see config/api_budget.json football_shadow_tiers)

| Consumer | Paid calls | Credits charged | Skipped (gate/floor) | Credits saved (est.) |
|---|---|---|---|---|
| football_daily_scan | 0 | 0 | 30 | 45 |
| football_shadow_scan | 0 | 0 | 50 | 50 |
| nba_prediction_board | 0 | 0 | 0 | 0 |
| prop_price_probe | 1 | 0 | 0 | 0 |
| tennis_prediction_board | 32 | 32 | 0 | 0 |

| Consumer | Plan A to date | Actual to date |
|---|---|---|
| football_daily_scan | 16.3–23.3 | 0 |
| football_settlement | 0.0–4.7 | 0 |
| tennis_prediction_board | 23.3–35.0 | 32 |
| nba_prediction_board | 4.7–14.0 | 0 |

Football: 0 credits over 5 scan days vs 30 if ungated (pre-Plan-A 6/day).

credits_saved_estimate = markets x regions of each skipped odds call; settlement scores and research calls are not in the shared ledger yet (account counter covers them).
