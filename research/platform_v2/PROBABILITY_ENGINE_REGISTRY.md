# Probability Engine Registry (source of truth; 2026-09-24)

| engine | version | status | best estimator | sample | holdout | prospective | ≥80% share | calibration | live source | money | multi research |
|---|---|---|---|---|---|---|---|---|---|---|---|
| football_1x2.market_consensus | v1 (production) | VALIDATED (Gate 1, Stage 3B) | de-vigged multi-book consensus (proportional) | 5776 | done (2024/25; football seasons all exposed since) | LIVE production (Daily Card / Money Card / paper ledger) | 0.033 | slope 1.06-1.09 (slightly flat); de-vig study verdict C | Odds API h2h (3 leagues) | PRODUCTION money gate (unchanged) | candidate legs (heavy favourites) |
| football_ou25.market | v1 | VALIDATED (Gate 1b) | consensus | 4640 | done | LIVE production (totals) | 0.001 | good | Odds API totals | PRODUCTION money gate | rarely strong |
| football_btts.market_implied_poisson | v1 | VALIDATED, low-confidence (Phase 5) | market-implied Poisson (1X2+OU) | 4595 | done (opened once) | NOT STARTED | 0.0 | slope 0.93 | Odds API btts per-event (1 credit/event), not wired | NOT ELIGIBLE | not useful |
| atp_match_winner.betfair_market | 1 (frozen) | VALIDATED (V2-1 sealed 2024-25) | Betfair LTP / live exchange back-lay midpoint | 12202 | done n=5066 | COLLECTING (0 predictions; workflow outage 22-24 Sep) | 0.198 | slope 0.986; >=80% 87.6->87.4 | Odds API covered tournaments (betfair_ex_uk) | NOT ELIGIBLE (paper) | strong leg pool |
| wta_match_winner.betfair_market | 1 (frozen) | VALIDATED (V2-2 sealed 2024-25) | Betfair LTP / live exchange midpoint | 10352 | done n=4339 | COLLECTING (6 predictions, 0 settled) | 0.177 | slope 0.979; >=80% 86.9->87.0; watch 2025 + grass | Odds API covered tournaments | NOT ELIGIBLE (paper) | strong leg pool |
| nba_moneyline.market | 1 (frozen) | VALIDATED CANDIDATE (V2-3 gate A) | average closing moneyline, proportional | 12825 | done n=2629 | DESIGNED, not active (season from late Oct) | 0.209 | slope 1.046; >=80% 85.5->87.5; >=90% small n, monitor | Odds API basketball_nba h2h (1 credit/scan) | NOT ELIGIBLE | strong leg pool, independent sport |
| football_double_chance.derived_1x2 | pending | IN RESEARCH (V2-4) | derived from 1X2 consensus (candidate) | — | pending | NOT STARTED | — | pending | to audit | NOT ELIGIBLE | potential |

Updated each phase. Validation status ≠ money eligibility; promotion follows `MODEL_PROMOTION_STANDARD.md`.
