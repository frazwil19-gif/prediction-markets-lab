# NBA Data Schema (canonical game table, `prediction_markets_lab.nba.data.build_games`)

| column | meaning |
|---|---|
| game_id | `NBA-<date>-<home>-<away>` (unique) |
| date | game date as published by the source (OddsPortal ≈ UTC/European date, +1 vs US for evening games) |
| season | NBA season label (a new season starts 15 Oct; the 2020 bubble to 11 Oct 2020 belongs to 2019-20) |
| home, away | franchise code (30; SBR nicknames mapped incl. New Orleans "Hornets" ≤2012-13, Bobcats→CHA, New Jersey→BKN) |
| home_score, away_score | final score incl. overtime |
| home_odds, away_odds | average closing decimal moneyline (primary) / SBR closing converted from American (warm-up rows, unused) |
| stage | regular / play_in / playoffs (SBR warm-up rows: unknown) |
| overtime | OT flag (primary) |
| neutral | 2020 bubble games |
| home_win | label: 1 if home_score > away_score |
| source | wippa_oddsportal / sbr |

Features (`prediction_markets_lab.nba.features`): rest (cap 5), b2b, games in last 7 days, rolling-10 point
differential and win %, shrunk season point differential per game, season game number, and pre-game Elo; all built
from strictly earlier dates.

## Games per season (primary source, eligible)
| season   |   play_in |   playoffs |   regular |   total |
|:---------|----------:|-----------:|----------:|--------:|
| 2016-17  |         0 |         79 |      1230 |    1309 |
| 2017-18  |         0 |         82 |      1226 |    1308 |
| 2018-19  |         0 |         82 |      1230 |    1312 |
| 2019-20  |         0 |         84 |      1059 |    1143 |
| 2020-21  |         6 |         85 |      1080 |    1171 |
| 2021-22  |         6 |         87 |      1228 |    1321 |
| 2022-23  |         6 |         84 |      1230 |    1320 |
| 2023-24  |         6 |         82 |      1224 |    1312 |
| 2024-25  |         6 |         84 |      1224 |    1314 |
| 2025-26  |         6 |         85 |      1224 |    1315 |

Total primary: 12825 · regular 11955 · playoffs 834 · play-in 36 · warm-up (SBR) 6326
