# Phase 5 — BTTS Data Feasibility Audit (2026-09-22)

Inspected directly from files in the repo and one live API probe, not from memory.

## Outcome-prediction feasibility: READY
| item | finding |
|---|---|
| Source | `data/processed/football/cycle_002_discovery_features.csv` (unchanged) |
| Matches | 5,800 (E0 1,900 · E1 2,760 · SC0 1,140) |
| Seasons | 2020/21 – 2024/25 (1,160 per season). 2025/26 raw files exist but are not in the feature build (known gap, shared with 1X2/OU2.5) |
| Goal-result coverage | 5,800 / 5,800 (100%) → BTTS label constructible for every match |
| BTTS YES base rate | 50.50% overall; drifts by season: 45.6% (2020/21, empty-stadium season), 49.1%, 49.7%, 55.0%, 53.2% (2024/25) |
| By competition | E0 53.9% · E1 48.9% · SC0 48.6% |
| Full pre-match feature coverage | 5,759 / 5,800 (99.3%) for the 29 data features |
| Market-derived inputs | closing de-vigged 1X2 consensus 5,763/5,800; closing OU2.5 source-average probability on all rows (2–3 bookmakers; 12 rows with 1) |

## Historical betting-replay feasibility: BLOCKED
football-data.co.uk carries **no BTTS odds** in any of the 18 raw E0/E1/SC0 season files (header scan for
`BTTS/BTS/GG/both` returned zero columns). No opening/closing BTTS prices, no bookmaker depth. A true BTTS
"market-only" model (Model A) and "BTTS market + data" (Model C) therefore **cannot be built historically and
were not fabricated**. The market-derived estimator used instead (λ solved from 1X2 + OU2.5 prices) is labelled
MARKET-DERIVED and is not a BTTS price.

## Live availability: CONFIRMED (probe 2026-09-22, `LIVE_BTTS_PROBE_2026-09-22.json`)
- The Odds API market key `btts` is an *additional market*: only via `/v4/sports/{sport}/events/{eventId}/odds`,
  one event per call. Cost = markets × regions → **1 credit per event** for `btts`/`uk`. `/events` listing is free.
- Probe (Arsenal v Leeds, EPL): **9 UK bookmakers** quoted BTTS, including **Betfair Exchange** (`betfair_ex_uk`),
  plus Betfred, LeoVegas, William Hill, Paddy Power, Virgin Bet, LiveScore Bet, Ladbrokes, Coral. Quotes were fresh
  (last_update within ~2 minutes).
- Credit budget: the free tier is 500/month; 41 were used at probe time. The current scan uses ~180/month. Adding BTTS
  for every fixture (~28–40 fixtures per week across the 3 leagues ≈ 120–170 credits/month) fits only if restricted to fixtures inside the 24h money
  window. It must not be added to the scan without an explicit credit-budget decision (see
  `PROBABILITY_ENGINE_ARCHITECTURE.md` §4).
