# DAILY PREDICTION BOARD — 2026-10-20

_Paper research board: what is most likely to happen. Not a betting card (see the Money Card)._

Upcoming events: 17 · Valid predictions: 23 · Sports: basketball, football, tennis
Counts: >=70: 6 · >=75: 5 · >=80: 2 · >=85: 1 · >=90: 0 · >=95: 0
Settled yesterday: 2 · System: **HEALTHY** · API credits (last observed): 181

## Top predictions (P ≥ 80%)

| Sport | Event | Start (UTC) | Market | Selection | P | Fair | Band | Engine | Evidence | Price (source) | Single | Multi-research |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tennis | Elena Rybakina v Polina Kudermetova | 2026-10-22T04:00 | match_winner | Elena Rybakina | 88.7% | 1.13 | 85-89.9% | wta_match_winner.betfair_market@1 | VALIDATED_HISTORICAL | 1.10 (betfair_ex_uk back (odds_api)) | no | yes |
| football | Wolverhampton Wanderers v Portsmouth | 2026-10-20T18:45 | double_chance | 1X | 82.9% | 1.21 | 80-84.9% | football_double_chance.derived_1x2@1 | PROSPECTIVE_SHADOW_LEAGUE | 1.19 (SYNTHETIC_DUTCH_BEST_1X2) | no | yes |

## Prospective evidence

| Engine | Status | Predictions | Settled | Maturity | ≥80% settled | ≥80% pred → actual |
|---|---|---|---|---|---|---|
| football_1x2.market_consensus | VALIDATED_HISTORICAL / COLLECTING | 612 | 129 | COLLECTING | 1 | 82.3% → 100.0% |
| football_ou25.market | VALIDATED_HISTORICAL / COLLECTING | 72 | 42 | COLLECTING | 0 | — → — |
| football_btts.market_implied_poisson | RESEARCH_VALIDATED / NOT_WIRED | 0 | 0 | COLLECTING | 0 | — → — |
| atp_match_winner.betfair_market | VALIDATED_HISTORICAL / COLLECTING | 158 | 146 | EARLY | 25 | 87.7% → 76.0% |
| wta_match_winner.betfair_market | VALIDATED_HISTORICAL / COLLECTING | 182 | 144 | EARLY | 26 | 89.2% → 80.8% |
| nba_moneyline.market | VALIDATED_HISTORICAL / AWAITING_SEASON | 8 | 0 | COLLECTING | 0 | — → — |
| nhl_moneyline.market | PROVISIONAL_PROSPECTIVE / COLLECTING | 85 | 63 | EARLY | 0 | — → — |
| nfl_moneyline.market | VALIDATED_HISTORICAL / COLLECTING | 28 | 15 | COLLECTING | 0 | — → — |
| football_double_chance.derived_1x2 | PROVISIONAL_PROSPECTIVE / COLLECTING | 612 | 9 | COLLECTING | 1 | 80.2% → 0.0% |

## System health

- daily_scan: OK (last 2026-10-20T06:16:30.358400+00:00)
- settlement: OK (last 2026-10-20T00:15:26.208907+00:00)
- tennis_board: OK (last 2026-10-20T15:16:36.492430+00:00)
- ci_tests: OK (last 2026-10-20T15:16:37.358267+00:00)

⟳ = start rescheduled since first observation; the current provider start is shown (rule est-1).

Single = passes the engine money status and payout floor pre-filter only; the Money Card decides bets. Double Chance is PROVISIONAL_PROSPECTIVE (exposed-data history; sealed holdout opens 2027-01-03).
