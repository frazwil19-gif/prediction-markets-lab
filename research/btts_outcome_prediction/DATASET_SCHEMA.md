# Phase 5 — Canonical BTTS Dataset Schema

Written by `scripts/run_phase5_btts_outcome_prediction.py --stage development` to
`data/processed/football/phase5_btts_canonical_dataset.csv` (derived, regenerable, not committed, same convention as
other `data/processed` files). One row per match, sorted by (match_date, match_id).

| group | columns |
|---|---|
| identity | match_id, season, match_date, competition, home_team, away_team |
| target | btts_yes (1 = both scored), home_goals, away_goals (labels only, never features) |
| Gate-1b fundamentals (19) | home/away_team_overall_last10_{avg_goals_for, avg_goals_against, avg_shots_for, avg_shots_against, avg_sot_for, avg_sot_against, avg_corners_for, avg_corners_against, points_per_game}, elo_rating_gap_incl_home_advantage |
| new rolling (10) | home/away_scoring_rate_l10, home/away_clean_sheet_rate_l10, home/away_btts_rate_l10, home_home_scoring_rate_l10, home_home_clean_sheet_rate_l10, away_away_scoring_rate_l10, away_away_clean_sheet_rate_l10 (shrunk toward the league's prior rate with 4 pseudo-matches) |
| context (not model inputs) | home/away_failed_to_score_rate_l10, home/away/min_history_matches, season_match_number, home/away_new_to_competition, abs_elo_gap, goal-diff volatility, market 1X2/OU2.5 probabilities |
| goal models | lambda_poisson_home/away, p_btts_poisson, lambda_market_closing_home/away, p_btts_market_implied_closing, p_btts_market_implied_opening |

All configurable values are in `BttsConfig` (`src/prediction_markets_lab/research/btts_outcome_prediction.py`).
