# NBA Leakage Audit

| input | pre-game? | control |
|---|---|---|
| rest, b2b, games in 7 days | yes | from strictly earlier dates (`team_state_features`, date-grouped) |
| rolling-10 point diff / win %, season point diff | yes | updated only after all of a date's features are computed; tests prove a game's own score never changes its own features |
| Elo | yes | pre-game rating used, then the result updates (`elo_probabilities`); the test changes a game's result and checks its pre-game probability is unchanged |
| season carry-over | yes | applied when a team's first game of a new season is reached |
| market | closing average odds | a pre-tip snapshot; a declared limitation is that the live scan will see earlier prices |
| fitted models | — | parameters chosen on development only; refit on development+validation before the holdout; holdout seasons never used to fit or choose |
| holdout | — | opened once by a hash-guarded script (a second run is refused) |
Not used anywhere: box scores of the same game, injuries, end-of-season standings, the wippa "advanced features"
parquet (leakage status unverifiable).
