# Probability Engine Registry (generated from PROBABILITY_ENGINE_REGISTRY.json, the source of truth; 2026-09-24, schema v2)

Machine fields added in V2-5; the V2-4 descriptive fields stay in the JSON for provenance. Validation status ≠ money eligibility.

| engine_id | ledger_version | status | prospective_status | probability_source | historical_sample | sealed_holdout_status | ge80_historical_coverage | historical_calibration | settlement_source | money_eligible | multi_research_eligible | snapshot_rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| football_1x2.market_consensus | 1 | VALIDATED_HISTORICAL | COLLECTING | daily_scan 1X2 multi-book proportional consensus | 5776 | DONE (2024/25) | 0.033 | slope 1.06-1.09 (slightly flat); de-vig study verdict C | football_data_co_uk | True | True | FIRST_SCAN_WITHIN_48H |
| football_ou25.market | 1 | VALIDATED_HISTORICAL | COLLECTING | daily_scan totals 2.5 consensus | 4640 | DONE | 0.001 | good | football_data_co_uk | True | False | FIRST_SCAN_WITHIN_48H |
| football_btts.market_implied_poisson | 1 | RESEARCH_VALIDATED | NOT_WIRED | market-implied Poisson (1X2+OU) | 4595 | DONE (opened once) | 0.0 | slope 0.93 | None | False | False | None |
| atp_match_winner.betfair_market | 1 | VALIDATED_HISTORICAL | COLLECTING | Odds API betfair_ex_uk back/lay midpoint (frozen hierarchy) | 12202 | DONE (2024-25, n=5066) | 0.198 | slope 0.986; >=80% 87.6->87.4 | TennisCourtLog | False | True | TENNIS_FIRST_VALID_SNAPSHOT |
| wta_match_winner.betfair_market | 1 | VALIDATED_HISTORICAL | COLLECTING | Odds API betfair_ex_uk back/lay midpoint (frozen hierarchy) | 10352 | DONE (2024-25, n=4339) | 0.177 | slope 0.979; >=80% 86.9->87.0; watch 2025 + grass | TennisCourtLog | False | True | TENNIS_FIRST_VALID_SNAPSHOT |
| nba_moneyline.market | 1 | VALIDATED_HISTORICAL | AWAITING_SEASON | Odds API basketball_nba h2h: mean decimal odds per side over >=3 books, proportional | 12825 | DONE (2024-26, n=2629) | 0.209 | slope 1.046; >=80% 85.5->87.5; >=90% small n, monitor | odds_api_scores (fallback, budgeted) | False | True | FIRST_SCAN_WITHIN_36H |
| football_double_chance.derived_1x2 | 1 | PROVISIONAL_PROSPECTIVE | COLLECTING | pairwise sums of renormalised daily_scan 1X2 consensus (0 credits) | 5897 | SEALED, NOT OPENED (2026/27 Aug-Dec; opens >= 2027-01-03) | 0.315 | slope 1.09 val / 0.95 conf (CIs incl. 1); >=80% 86.3->87.1; >=90% 92.8->95.0 (under-confident at top, reported not corrected) | football_data_co_uk | False | True | FIRST_SCAN_WITHIN_48H |

NBA activation date: 2026-10-20 (regular-season opening night).
