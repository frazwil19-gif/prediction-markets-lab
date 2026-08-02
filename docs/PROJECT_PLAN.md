# Project Plan

## Objective

Identify positive expected value opportunities in sports and prediction
markets while preserving a very small bankroll (£5–£10), and collect
enough evidence to determine whether the process has genuine
predictive value.

This is explicitly **not** about betting every day or maximising win
rate. A successful day may produce one qualified live trade, one or
more paper trades, or no trade at all. No trade should ever be forced
merely to create daily activity.

## What the project optimises for

- Expected value (commission-adjusted)
- Probability calibration
- Closing-line value (CLV)
- Controlled drawdown
- Disciplined execution (fixed rules, no discretion under pressure)
- Transparent, complete records of every decision
- Repeatable research (so results can be audited and improved)

## Roles

| Role | Responsibility |
|---|---|
| **Claude** | Lead developer, repository/file manager, calculator builder, Google Sheets architect, testing engineer. Not the daily betting decision-maker. |
| **ChatGPT** | Daily research operator: screens markets, evaluates odds, calculates probabilities/EV, grades opportunities, reviews performance. |
| **User** | Operates from a phone: checks live prices, manually places bets, confirms exact prices received, records/approves trades, makes the final call. |

The system must never depend on unrestricted automated execution.

## Execution venues

- **Primary:** Smarkets
- **Secondary (comparison):** Betfair Exchange

The user manually checks both and uses whichever offers the best
executable net price. No exchange API is assumed to be available;
prices are entered manually.

## Staged delivery

See [`ROADMAP.md`](ROADMAP.md) for the full stage breakdown. In brief:

1. **Foundation** (this release) — calculation engine + tests
2. **Manual workflow** — CSV templates, daily report, Sheets structure
3. **Football baseline** — data loader + Elo/Poisson models
4. **Tennis baseline** — data schema + Elo/surface Elo models
5. **Reporting** — daily/weekly/monthly reports, performance attribution
6. **Optional free automation** — only after manual operation works

Automation is never the starting point.
