# NBA Outcome Discovery + Feature Stability (development seasons 2016-17 → 2021-22 only; n = 7,564)

Home team wins 56.8% overall in development (58–59% pre-COVID, 54.7% in 2019-20/2020-21, 54.7% in 2021-22).
Home-minus-away features, home wins vs home losses (`NBA_OUTCOME_DISCOVERY.csv`):

| feature | mean when home won | mean when home lost | Cohen's d | same sign in all 6 seasons? |
|---|---|---|---|---|
| market logit (closing average) | 0.649 | −0.071 | **0.84** | 6/6 |
| Elo logit (pre-game) | 0.493 | −0.004 | **0.70** | 6/6 |
| season-to-date point diff/game (shrunk) | +1.51 | −2.12 | **0.65** | 6/6 |
| rolling-10 point diff | +1.99 | −2.92 | 0.58 | 6/6 |
| rolling-10 win % diff | +0.059 | −0.088 | 0.53 | 6/6 |
| away team on a back-to-back | 22.2% | 17.7% | 0.11 | 6/6 |
| rest-day difference | +0.15 | +0.07 | 0.08 | 5/6 |
| games in previous 7 days (home − away) | −0.05 | +0.01 | −0.08 | 6/6 |
| home team on a back-to-back | 12.4% | 13.8% | −0.04 | **3/6 (unstable)** |
| season game number | 42.5 | 42.3 | 0.01 | 4/6 (none) |

Reading: team strength (market, Elo, point differential) dominates and is stable in every season. Schedule effects
are real but small, and only the *away* back-to-back and the 7-day load are consistent. Recent form (rolling 10) is
weaker than season-long strength. None of this was used to choose features: the feature list was fixed in the
protocol before these numbers existed.
