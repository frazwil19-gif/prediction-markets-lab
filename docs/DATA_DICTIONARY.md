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

## Historical football data (Football-Data.co.uk, Stage 3+)

date, competition, home_team, away_team, home_goals, away_goals,
result, bookmaker_odds, opening_odds, closing_odds.

## Event-level manual features (all sports)

injuries, suspensions, confirmed_lineups, withdrawals, surface,
rest_days, travel, weather, player_availability,
pitch_or_toss_information, polling_information.

All manually entered information must retain its source and timestamp
where practical (`config/data_sources.yaml`,
`manual_entry_policy`).
