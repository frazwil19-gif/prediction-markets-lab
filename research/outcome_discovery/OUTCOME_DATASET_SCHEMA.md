# Outcome Dataset Schema -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22. Schema of the candidate-level dataset built by
`src/prediction_markets_lab/research/outcome_discovery_analysis.py::build_candidates()` from the
two source files named in DATASET_AUDIT.md. Not persisted to disk as its own file (it is rebuilt
in memory each run from the two existing, already-persisted CSVs it joins) -- this document is its
schema reference.

One row per (match, side), side in {home, draw, away}, 16,893 rows total (5,631 matches x 3).

| Column | Type | Description |
|---|---|---|
| `match_id` | str | Same match_id as the source predictions/features files |
| `competition_code` | str | E0 / E1 / SC0 |
| `season` | str | e.g. `2020_21` |
| `side` | str | `home` / `draw` / `away` -- which candidate this row represents |
| `target` | int (0/1) | 1 iff `side` is the side that actually occurred |
| `prob_market` | float or None | Model A: de-vigged consensus probability for `side` |
| `prob_elo_poisson` | float or None | Model D: frozen Elo+Poisson blend probability for `side` |
| `prob_fundamentals` | float or None | Model B: 9-feature fundamentals-only probability for `side` |
| `prob_market_fundamentals` | float or None | Model C: market+fundamentals probability for `side` |
| `prob_ensemble` | float or None | Calibrated blend-weight-search ensemble probability for `side` |
| `signed_elo_gap` | float or None | Elo advantage oriented toward `side` (home: as-is, away: negated, draw: -abs) |
| `signed_diff_goals_for_last10` | float or None | Same signing convention, last-10-match rolling goals-for diff |
| `signed_diff_shots_for_last10` | float or None | ...rolling shots-for diff |
| `signed_diff_points_per_game_last10` | float or None | ...rolling points-per-game diff |
| `signed_diff_goals_for_last5` | float or None | Last-5-match rolling goals-for diff |
| `signed_diff_shots_for_last5` | float or None | Last-5-match rolling shots-for diff |
| `signed_diff_points_per_game_last5` | float or None | Last-5-match rolling points-per-game diff |
| `signed_diff_sot_for_last10` | float or None | Last-10-match rolling shots-on-target-for diff (derived: home minus away, from the two raw columns) |
| `signed_diff_sot_against_last10` | float or None | Last-10-match rolling shots-on-target-against diff (defensive) |
| `signed_diff_corners_for_last10` | float or None | Last-10-match rolling corners-for diff |
| `signed_diff_cards_for_last10` | float or None | Last-10-match rolling cards-for diff |

**Signing convention** (Section 6's "winners vs losers" framing requires a consistent orientation):
for the home candidate, a signed feature keeps its raw home-minus-away value (positive = advantage
for home). For the away candidate, the same raw value is negated (positive = advantage for away).
For the draw candidate, the signed value is `-abs(raw)` -- i.e. closer matches (smaller absolute
gaps) score higher for the draw candidate, reflecting the intuitive hypothesis that draws are more
likely between evenly-matched sides (tested, not assumed -- see DRAW_ANALYSIS.csv).

**None handling**: a `None` signed feature means the underlying engineered-feature file has no row
for that match (2025/26 holdout candidates) or a genuinely missing rolling value (very early
matches in a competition-season before 5/10 prior matches exist for a team). `None` values are
excluded from every mean/effect-size calculation, never treated as zero -- verified by
`test_cohens_d_skips_none_values` and `test_build_candidates_missing_features_are_none_not_zero` in
`tests/unit/test_outcome_discovery_analysis.py`.
