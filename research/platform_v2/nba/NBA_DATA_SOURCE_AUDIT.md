# NBA Data Source Audit (Stage 0, 2026-09-24) — **Data decision B: ready using free new data**

Network reality (tested): from both the Mac VM and the cloud sandbox, **only GitHub (and PyPI) are reachable**.
sportsbookreviewsonline.com, stats.nba.com, cdn.nba.com, basketball-reference.com, fivethirtyeight.com,
kaggle.com and historicdata.betfair.com are all refused by the organisation allowlist.

| # | source | coverage | fields | cost / licence | reachable | verdict |
|---|---|---|---|---|---|---|
| 1 | repository / local | none for NBA | — | — | — | nothing existing |
| 2 | **Betfair historical (BASIC, basketball)** | Exchange basketball incl. NBA; BASIC = last-traded price at 1-min resolution (same format as tennis) | MATCH_ODDS, runner names, LTP series | free BASIC tier; personal use under Betfair's historical-data terms | **no** (site blocked). Fraser would download manually, as for tennis | **not needed** for Stage A; an optional later check of exchange-vs-bookmaker calibration |
| 3 | **wippa-studios/wippa-nba-data** (GitHub) | **2016-17 → 2025-26**, all games incl. playoffs/play-in (pre-season/All-Star excluded by us) | date, teams, final score, OT flag, **OddsPortal average closing decimal moneyline** | free, MIT (README) | yes | **PRIMARY** |
| 4 | **flancast90/sportsbookreview-scraper** (GitHub) | 2011-12 → 2021-22 | results, quarter scores, closing American moneyline, spreads, totals | free, MIT | yes | Elo warm-up (pre-2016) + **independent cross-check** |
| 5 | wippa `player_gamelogs_2025-26.csv`, `nba_advanced_features.parquet` | 2025-26 only / derived | player logs; derived features of unknown leakage status | MIT | yes | **not used** (single season; leakage unverifiable) |
| 6 | NBA Stats API, Basketball-Reference (box scores, injuries) | full | everything | free but blocked / ToS forbids scraping (B-Ref) | no | unavailable |

**Cross-check (data quality, 2016-17 → 2021-22 overlap, 7,395 games matched on date ±1):** final scores agree 99.6%,
**winners agree 99.8%**, implied home-win probabilities correlate 0.997 (mean absolute difference 0.010). OddsPortal
dates are +1 day versus US dates for 97% of games (a consistent timezone offset).

**Sample (primary, after eligibility):** 2016-17 1,309 · 2017-18 1,308 · 2018-19 1,312 · 2019-20 1,143 (COVID;
172 bubble games flagged neutral) · 2020-21 1,171 (72-game season) · 2021-22 1,321 · 2022-23 1,320 · 2023-24 1,312 ·
2024-25 1,314 · 2025-26 1,315 → **12,825 games** (11,955 regular season · 834 playoffs · 36 play-in; per-season table
in `NBA_DATA_SCHEMA.md`). Warm-up 2011-12 → 2015-16: 6,326 SBR games. Odds missing in the primary source: 0.

**Historical odds:** one OddsPortal *average* closing price per side (median two-way book sum 1.042). No per-book
panel, no timestamps, no opening prices. **Sports features:** scores and schedule only, so no shooting, rebounds,
pace or possessions (no reachable box-score source). **Injuries/rosters:** not available historically, a stated
limitation (see `NBA_CURRENT_CONTEXT_DESIGN.md`). **Outcome-prediction feasibility:** READY.
**Historical betting-replay feasibility:** PARTIAL. There is a single average closing price, so no best-price,
timing or CLV replay; not attempted this phase.
Manual download by Fraser: **none required**. Cost: £0.
