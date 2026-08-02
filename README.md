# Prediction Markets Lab

A lightweight, disciplined, mobile-first system for identifying
potentially mispriced sports and prediction markets, estimating fair
probabilities, and calculating commission-adjusted expected value
against executable exchange prices.

This is a low-cost side project, not a main quantitative trading
system. It is designed to run at as close to £0 ongoing cost as
possible, starting from a bankroll of approximately £5–£10.

> **This system does not guarantee profit. It estimates probabilities
> and expected value under uncertainty. Losing trades and losing
> periods are unavoidable.**

## Project objective

The objective is **not** to bet every day, and **not** to maximise win
rate. The objective is to identify positive expected value
opportunities while preserving a very small bankroll, and to collect
enough evidence to determine whether the process has genuine
predictive value. A successful day may produce one qualified trade,
one or more paper trades, or no trade at all. See
[`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) for the full rationale.

## Scope (Stage 1 — this release)

Stage 1 delivers the calculation foundation only:

- Odds conversion (decimal odds → raw implied probability)
- Proportional margin removal (V1 default method)
- Cross-bookmaker consensus (median, mean, std dev, min, max, IQR)
- Commission-adjusted expected value, edge, and break-even probability
- Bankroll, staking, exposure, and loss-stop logic
- A+/A/B/C/Reject grading against configurable thresholds
- Unit tests and sample football/tennis fixtures for all of the above

Stage 1 deliberately does **not** include: API integrations, automated
bet placement, the daily CLI/report generator, Google Sheets sync, or
any sport-specific probability model (Elo, Poisson, etc.). These are
represented in the repository as documented placeholder modules and
scheduled in [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Cost constraints

| Item | Budget |
|---|---|
| APIs | £0 |
| Subscriptions | £0 |
| VPS / cloud servers | £0 |
| Database | free (local CSV/SQLite) |
| Cloud storage | free (GitHub + Google Sheets free tier) |
| Automated execution | none — manual betting only |
| Starting bankroll | £5–£10 |

## Architecture

```
prediction-markets-lab/
├── config/        # YAML configuration (bankroll, thresholds, commissions, ...)
├── docs/          # Methodology, workflow, risk, and governance documentation
├── data/          # Raw / interim / processed / external / sample data
├── src/prediction_markets_lab/
│   ├── ingestion/       # (Stage 2+) loading manual + free-source data
│   ├── normalisation/   # (Stage 2+) team/player/competition name matching
│   ├── probability/     # odds conversion, margin removal, consensus [Stage 1]
│   ├── models/          # (Stage 3+) Elo/Poisson category models
│   ├── ev/              # commission-adjusted expected value, edge [Stage 1]
│   ├── risk/            # bankroll, staking, exposure, loss-stops [Stage 1]
│   ├── decisions/       # grading (A+/A/B/C/Reject) [Stage 1]
│   ├── performance/     # (Stage 5+) ROI, CLV, Brier, drawdown
│   ├── reports/         # (Stage 2+) daily/weekly/monthly report generation
│   ├── storage/         # (Stage 2+) CSV/SQLite/Google Sheets persistence
│   └── utils/           # (Stage 2+) dates, money, validation, logging
├── scripts/       # (Stage 2+) command-line entry scripts
├── templates/     # CSV/Markdown templates for manual workflow
├── reports/       # Generated daily/weekly/monthly reports and audits
├── research/      # Hypotheses, experiments, findings, model cards
├── notebooks/     # (Stage 3+) exploratory analysis notebooks
└── tests/         # Unit, integration, and fixture data
```

## Supported sports (Stage 1 target: football, tennis)

- **Football**: pre-match 1X2, over/under 2.5 goals
- **Tennis**: pre-match match winner
- Basketball, cricket, and politics are Tier 2 — deferred until the
  football/tennis workflow is proven (see `config/competitions.yaml`).

## Installation

Requires Python 3.11+.

```bash
git clone <this-repo-url>
cd prediction-markets-lab
pip install -r requirements.txt
pip install -e .
```

No API keys are required for Stage 1 — everything runs from unit
tests and sample fixtures.

## Configuration

All thresholds and limits live in `config/*.yaml`, never hard-coded in
Python:

- `bankroll.yaml` — starting bankroll, stake sizes, exposure and loss
  stop limits
- `thresholds.yaml` — grading thresholds for A+/A/B/C
- `commissions.yaml` — Smarkets/Betfair commission rates (verify
  current rates on your own account before live use)
- `competitions.yaml` — active sports, leagues, and market types
- `bookmakers.yaml` — bookmakers used for consensus (populate before
  live use)
- `data_sources.yaml` — data source catalogue
- `model_weights.yaml` — consensus/model blend weights
- `logging.yaml` — logging configuration (Stage 2+)

## Daily mobile workflow (Stage 2+ — not yet implemented)

The intended end-state workflow (see
[`docs/MOBILE_WORKFLOW.md`](docs/MOBILE_WORKFLOW.md)):

```
ChatGPT daily scan
  → Candidate football/tennis events
  → User checks bookmaker and exchange odds on phone
  → User pastes prices into ChatGPT or Google Sheets
  → ChatGPT calculates fair probability and EV
  → ChatGPT returns A+, A, B, C or Reject
  → User manually places any qualifying trade
  → Trade recorded in Google Sheets
  → Result and closing price logged later
```

Stage 1 provides the Python calculation engine this workflow will call
into once the manual CSV/Sheets glue (Stage 2) exists.

## Manual odds workflow (Stage 2+ — not yet implemented)

Templates for manual entry are provided under `templates/` as
placeholders (`manual_odds_entry.csv`, `exchange_price_entry.csv`) and
will be wired up to `ingestion/manual_odds_loader.py` and
`ingestion/exchange_price_loader.py` in Stage 2.

## How fair probabilities are calculated

See [`docs/PROBABILITY_METHODOLOGY.md`](docs/PROBABILITY_METHODOLOGY.md)
for full detail. Summary:

1. Convert each bookmaker's decimal odds to raw implied probability:
   `q_i = 1 / O_i`
2. Remove each bookmaker's margin proportionally:
   `p_i = q_i / Σ q_j`
3. Take the cross-bookmaker **median** as the V1 consensus estimate
   (also reports mean, weighted mean, std dev, min, max, IQR, and
   bookmaker count)
4. (Stage 3+) Blend consensus with a category-specific model using
   configured weights to produce a final probability

## How EV is calculated

See [`docs/EV_METHODOLOGY.md`](docs/EV_METHODOLOGY.md) for full detail.
For a £1 back bet at decimal odds `O`, estimated probability `p`, and
exchange commission `c`:

```
EV = p * (O - 1) * (1 - c) - (1 - p)
```

The system always distinguishes probability edge, expected value,
expected profit, and realised profit — these are never conflated.

## Risk rules

See [`docs/RISK_MANAGEMENT.md`](docs/RISK_MANAGEMENT.md). Defaults for
a £10 bankroll (all configurable in `config/bankroll.yaml`):

- Normal stake: £0.25, maximum stake: £0.50
- Maximum daily exposure: £0.75, maximum 3 open bets
- Daily loss stop: £0.75, weekly loss stop: £2.00
- No martingale, no accumulators, no chasing losses, no automated
  execution

## How to generate a daily report

Not yet available — planned for Stage 2. The target format is defined
in [`templates/daily_scan_template.md`](templates/daily_scan_template.md).

## How to run tests

```bash
pip install -r requirements.txt
pytest
```

All Stage 1 unit tests should pass with no network access and no API
keys.

## Known limitations (Stage 1)

- No live data ingestion — everything is calculation logic plus
  sample fixtures.
- No sport-specific probability model yet (`P_model` is not
  implemented); only the margin-free bookmaker consensus is
  calculated end-to-end.
- Confidence, data-quality, and liquidity scores are boolean/manual
  inputs in Stage 1, not automated numeric scores.
- Bookmaker list (`config/bookmakers.yaml`) and commission rates
  (`config/commissions.yaml`) are placeholders/assumptions — verify
  before relying on them for a real decision.
- No CLI, no report generator, no Google Sheets sync yet.
- Grade C's exact boundary (a "watchlist" floor below Grade B) is not
  specified in the original brief; a conservative default
  (`grade_c_min_net_ev: 0.00`) has been assumed and documented in
  `config/thresholds.yaml`.

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full Stage 2–6 plan.
