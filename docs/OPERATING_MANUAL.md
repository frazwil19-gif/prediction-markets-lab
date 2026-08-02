# Operating Manual

## Current status

This document describes the intended full operating model. As of
Stage 1, only the calculation engine (`src/prediction_markets_lab/`)
and its unit tests exist. The manual daily workflow described below
depends on Stage 2 (CSV templates, report generator, Google Sheets
sync) and is **not yet operable end-to-end**.

## Roles in daily operation

- **ChatGPT** runs the daily scan using
  `templates/chatgpt_daily_prompt.md`, screening football and tennis
  markets and producing graded candidates.
- **User** checks live bookmaker and exchange prices on their phone,
  pastes them into ChatGPT or Google Sheets, and manually places any
  qualifying trade.
- **Claude** maintains the underlying calculation engine, repository,
  and Google Sheets schema, and is not the daily decision-maker.

## Standing rules (always apply)

- Never force a trade to create daily activity. "No bets today" is a
  valid and expected outcome.
- Every recommendation must be backed by the full evidence set defined
  in `docs/DATA_DICTIONARY.md` (consensus probability, model
  probability, exchange implied probability, edge, net EV, confidence,
  data quality, liquidity, recommended stake, grade, reason).
- Risk limits in `config/bankroll.yaml` are hard limits, not
  suggestions. See `docs/RISK_MANAGEMENT.md`.
- No martingale, no accumulators, no chasing losses, no automated
  execution — ever.

## What to do if something looks wrong

If the numbers coming out of the calculation engine look inconsistent
with the configuration, stop before placing any live trade and check:

1. Are `config/*.yaml` values what you expect?
2. Does the market actually qualify under `docs/MARKET_RULES.md`?
3. Has a safety/failure condition in `docs/RISK_MANAGEMENT.md` been
   triggered (stale price, low bookmaker count, insufficient
   liquidity, loss stop reached, etc.)?

When in doubt, grade the opportunity down, not up.
