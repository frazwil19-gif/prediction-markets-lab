# Phase 3, Section 2 -- Existing Data Inventory

**Written 2026-09-22.** Full inventory of every data family already in the repository or already
downloaded onto Fraser's machine, before any external search. Structured version:
`MARKET_COVERAGE_MATRIX.csv`.

## Football (Cycle 1 / Cycle 2)

| Item | Detail |
|---|---|
| Matches | 5,800 (E0/E1/SC0, 2020/21-2025/26), 5,776 with an eligible closing 1X2 consensus |
| 1X2 bookmaker odds | 49,673 rows, up to 6 bookmakers/match, opening AND closing snapshots -- full coverage 2020/21-2024/25, panel changed (3 of 6 persist) in 2025/26 |
| Over/Under 2.5 odds | Only 2-3 bookmakers/match (2 for 80% of matches) -- below the production `min_bookmakers=3` floor. Cycle 2's own consensus files (`cycle_002_consensus_ou25.csv`) are 0 bytes as a direct consequence |
| Asian Handicap odds | Same bookmaker-depth shortfall as OU2.5; `cycle_002_consensus_ah.csv` also 0 bytes |
| Match statistics | Shots, SOT, corners, cards, fouls, referee -- full coverage, all 5,800 matches (`cycle_002_match_statistics.csv`) |
| Rolling fundamentals | Elo, Poisson, last-5/last-10 rolling differentials, home/away-context splits -- all leakage-safe, all pre-match (`cycle_002_discovery_features.csv`) |
| Kickoff time-of-day | Recovered from raw football-data.co.uk files in Backtest Phase 1 (100% join success, 5,776/5,776) |
| Timestamp quality | Single opening + single closing snapshot per bookmaker per match -- no intraday series. PROXY replay only, confirmed in Backtest Phase 1's feasibility audit |
| Exact-replay capability | NO for any market -- football-data.co.uk never provides intraday price history |

**Live production (The Odds API, 2026-09-19 onward)**: real per-day fixtures/odds for EPL,
Championship, Scottish Premiership; 1X2 and Over/Under 2.5 both operational in the live daily scan;
Asian Handicap not yet wired (needs exact-line matching). One real `over_under_2_5` paper bet has
already been recorded in `paper_ledger/paper_bets.csv` (of 22 total) -- **OU2.5 is already live and
producing real candidates with zero historical backtest validation behind its money-qualification
thresholds**, since Backtest Phase 1 only validated 1X2.

## Tennis (Cycle 2 Workstream B, CLOSED for edge-hunting -- see EXHAUSTED_VS_OPEN_RESEARCH.md)

| Item | Detail |
|---|---|
| Match data | TML Database, ATP, 2021-2026 (`data/raw/tennis/tml_database/atp/{2021..2026}.csv`), 14,564 canonical matches 2021-2025 after normalisation |
| Odds source | Betfair Historical Data, **BASIC (free) tier** -- last-traded-price only, no volume, no order-book depth. Already downloaded, already linked: 12,956 of 14,564 matches linked (88.96%), 12,202 (83.78%) usable at a 30-minute pre-match horizon with a "fresh" price |
| **Location of the raw archive, NOT yet fully re-audited by this phase's team, confirmed to exist by direct inspection this session** | Two connected folders on Fraser's machine, outside the repo: `Downloads/tennis data/data.tar` (4.17 GB, ~996,779 files, Betfair BASIC-tier tennis market streams, 2021 through early-2026) and `Downloads/BASIC/2026/` (already-unpacked continuation, Jan-Sep 2026, ~28,500 event folders, 746 MB). Every sampled file across both locations confirmed `eventTypeId: 2` (Betfair's Tennis code) -- this appears to be a single, ongoing tennis-only historical pull, not yet fully consolidated into the repo's own `data/raw/` or `data/processed/` structure for the 2026 portion |
| Ingestion/linkage pipeline | Already built and tested: `ingestion/betfair_historical_schema.py`, `ingestion/betfair_market_index.py`, `normalisation/tennis_betfair_linkage.py`, `scripts/consolidate_betfair_2021_2025.py`, `scripts/link_betfair_2021_2025.py` |
| Timestamp quality | Intraday last-traded-price ticks (not just open/close) -- genuinely finer-grained than football's single-snapshot data, enabling a real (not proxy-by-necessity) pre-match price at any chosen horizon |
| Exact-replay capability | Materially better than football's proxy limitation for the *money-qualification* question (see HISTORICAL_SOURCE_AUDIT.md), though still last-traded-price only, not full order-book depth (that needs the paid ADVANCED/PRO tiers, not recommended) |
| Live production | Tennis is NOT wired into `decisions/recommendation.py` or `scripts/run_daily_scan.py` at all yet -- no live tennis daily-card candidates exist today |

## Other sports

No basketball or cricket data exists anywhere in the repository (confirmed by a fresh file search this
session, zero matches for either term outside irrelevant substrings). Cricket remains explicitly
PAUSED per the master directive §14. Basketball was never started.

## Non-repo local assets checked and found irrelevant

`Downloads/BASIC` and `Downloads/tennis data` were the only two non-repo connected folders searched.
No other connected folder or repository directory contains sports/market data not already covered
above.
