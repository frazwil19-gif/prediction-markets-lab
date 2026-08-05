# Data Dictionary

## Minimum evidence per opportunity (project instructions, section 5)

Every opportunity recorded by the system — live, paper, or rejected —
must include:

| Field | Description |
|---|---|
| market | The market type (e.g. `pre_match_1x2`, `over_under_2_5_goals`) |
| event | The specific fixture/match |
| selection | The specific outcome being priced |
| timestamp | When the price/data was captured |
| bookmaker consensus probability | Margin-free median across bookmakers (`probability.consensus`) |
| model probability | Category-specific model estimate (Stage 3+) |
| exchange implied probability | `1 / exchange_decimal_odds` |
| probability edge | Estimated vs. market probability, in percentage points (`ev.edge`) |
| commission-adjusted EV | Net EV per unit stake (`ev.expected_value`) |
| confidence score | Manual (Stage 1) or automated (later) confidence rating |
| data-quality score | Manual (Stage 1) or automated (later) data-quality rating |
| liquidity assessment | Manual (Stage 1) exchange depth check |
| recommended stake | From `risk.staking`, capped by `config/bankroll.yaml` |
| decision grade | A+ / A / B / C / Reject (`decisions.grading`) |
| reason | Why this grade was assigned |
| rejection reason | Present when grade is Reject |

This mirrors the Google Sheets **Markets** tab schema — see
`docs/OPERATING_MANUAL.md` and the Google Sheets design in the Stage 1
build report.

## Historical football data (Football-Data.co.uk, Stage 3A — Cycle 1)

**Status: pipeline validated against real data at excerpt scale (29
matches). See `reports/audits/CYCLE_001_DATA_ACQUISITION_REPORT.md`
for exactly what has and hasn't been acquired.**

### Raw source fields (as fetched, confirmed live)

date, time, home_team, away_team, full_time_home_goals,
full_time_away_goals, full_time_result, half_time_home/away_goals,
half_time_result, referee, match statistics (shots, shots on target,
fouls, corners, cards), per-bookmaker opening 1X2 odds (6 bookmakers:
Bet365, BetWin, Betfair Exchange, Pinnacle, William Hill, 1xBet),
per-bookmaker closing 1X2 odds (same 6, "C"-suffixed columns), average
and maximum opening/closing odds (aggregate, NOT individual
bookmakers — see `docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`),
over/under 2.5 goals and Asian handicap odds (opening and closing).
Full column-level inventory: `reports/audits/football_data_schema_inventory.csv`.

### Canonical processed schema

Three related tables (`src/prediction_markets_lab/storage/schemas.py`):

- **`HistoricalMatchRecord`** — one row per unique match. Carries
  identity, normalised team names, result, aggregate odds summaries,
  bookmaker counts, and per-analysis eligibility flags
  (`eligible_outcome_model`, `eligible_consensus_model`,
  `eligible_opening_analysis`, `eligible_closing_analysis`,
  `eligible_clv_proxy_analysis`) — ineligible rows are flagged, never
  silently dropped from the master dataset (project instructions
  section 11).
- **`HistoricalBookmakerMarketRecord`** — one row per (match,
  bookmaker, price timing) complete H/D/A triplet, with raw implied
  and margin-free fair probabilities. Reconstructable back to the full
  per-bookmaker market for any match via `match_id`.
- **`HistoricalConsensusRecord`** — one row per (match, price timing),
  with median/mean/std/IQR/min/max fair probabilities computed **only**
  from complete bookmaker-specific triplets (never from the Avg*/Max*
  aggregate columns, which are not independent bookmakers).

See `data/samples/cycle_001_matches_sample.csv`,
`cycle_001_bookmaker_markets_sample.csv`, and
`cycle_001_consensus_sample.csv` for real, computed (not fabricated)
examples of all three tables.

### Team and competition normalisation

`config/football_team_aliases.yaml` maps raw source team names to a
canonical name (`normalisation.team_names`); unresolved names are
tracked in `reports/audits/unresolved_team_names.csv`, never silently
fuzzy-matched. `normalisation.competition_names` maps Football-Data
competition codes (E0, E1, SC0, ...) to canonical competition metadata.

## Event-level manual features (all sports)

injuries, suspensions, confirmed_lineups, withdrawals, surface,
rest_days, travel, weather, player_availability,
pitch_or_toss_information, polling_information.

All manually entered information must retain its source and timestamp
where practical (`config/data_sources.yaml`,
`manual_entry_policy`).
