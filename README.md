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

## Scope

**Stage 1 (complete)** delivered the calculation foundation:

- Odds conversion (decimal odds → raw implied probability)
- Proportional margin removal (V1 default method)
- Cross-bookmaker consensus (median, mean, std dev, min, max, IQR)
- Commission-adjusted expected value, edge, and break-even probability
- Bankroll, staking, exposure, and loss-stop logic
- A+/A/B/C/Reject grading against configurable thresholds
- Unit tests and sample football/tennis fixtures for all of the above

**Stage 2 (complete)** added the manual workflow and research
governance layer:

- **Corrected** per-bookmaker margin removal (see "How fair
  probabilities are calculated" below — an earlier version of the
  daily shortlist script had a bug here; it's fixed and tested)
- Manual odds/exchange CSV ingestion, daily report generation, trade
  settlement scripts
- Google Sheets workbook (operational + research tabs)
- Research Engine: Hypothesis Registry, Behaviour Atlas, evidence
  grading, research prioritisation (see "Research Engine status"
  below)

**Stage 3A status: STAGE 3A TOOLING COMPLETE — FULL ACQUISITION
PENDING.** Scottish Premiership feasibility confirmed;
loader, bookmaker-extraction, normalisation, chronological-split, and
canonical-schema pipeline validated end-to-end against 29 genuine
historical matches (`data/samples/excerpt_validation/`). The complete
5-season × 3-competition dataset (~15 files) has **not** been
acquired; no data version is frozen; no model exists; no hypothesis
has been tested; the Behaviour Atlas remains empty. See
`research/cycles/CYCLE_001/CYCLE_PLAN.md` for full detail and
`docs/PHONE_ONLY_DATA_ACQUISITION.md` for how the full acquisition is
intended to run (a manually-triggered GitHub Actions workflow, since
this project must remain operable without a laptop).

Deliberately **not** included at any stage so far: paid API
integrations, automated bet placement, machine learning, or a web
dashboard. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full plan
and [`docs/ARCHITECTURE_FREEZE_V1.md`](docs/ARCHITECTURE_FREEZE_V1.md)
for the current change-control policy on adding new modules.

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
for full detail. Summary of the **corrected** pipeline
(`probability.market_pipeline.compute_market_consensus`):

1. Group all odds by **bookmaker**, not just by selection — margin
   removal requires one bookmaker's full outcome set together.
2. For each bookmaker, convert decimal odds to raw implied probability:
   `q_i = 1 / O_i`
3. Remove that bookmaker's margin proportionally:
   `p_i = q_i / Σ q_j`
4. Reject any bookmaker that did not quote every expected outcome for
   the market — an incomplete market cannot have its margin correctly
   removed, and is excluded rather than silently treated as valid.
5. Take the cross-bookmaker **median** of the remaining margin-free
   probabilities as the V1 consensus estimate (also reports mean,
   weighted mean, std dev, min, max, IQR, and bookmaker count).

**Note on history:** an earlier version of
`scripts/generate_daily_shortlist.py` computed "consensus" from raw
implied probabilities grouped only by outcome, without ever removing
bookmaker margin. This has been corrected (see CHANGELOG.md) and is
covered by tests proving the fix against hand-calculated examples
(`tests/unit/test_market_pipeline.py`).

4. (Stage 3+) Blend consensus with a category-specific model using
   configured weights to produce a final probability — not yet
   implemented; no model exists yet.

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

## Research Engine status

Stage 2 added a lightweight research-governance layer
(see [`docs/RESEARCH_ENGINE.md`](docs/RESEARCH_ENGINE.md)) so the
project can distinguish a genuinely repeatable edge from noise, rather
than only looping "collect odds → calculate EV → place bets → track
profit". Current status:

- **Hypothesis Registry**
  (`research/hypotheses/hypothesis_registry.csv`): 11 seeded
  hypotheses (6 football, 5 tennis), all at status `IDEA` or
  `DATA_REQUIRED`. **None have been tested. None are validated. None
  should be treated as a trading signal.**
- **Behaviour Atlas** (`research/behaviours/behaviour_atlas.csv`):
  intentionally empty — no hypothesis has yet earned enough evidence
  to graduate into a tracked behaviour. An empty atlas is the correct
  state at this point, not a bug.
- **Research module**
  (`src/prediction_markets_lab/research/`): schemas, registry,
  behaviour atlas, hypothesis validation, evidence grading, and
  research prioritisation are implemented and tested — the machinery
  for running a research cycle exists, but no research cycle has been
  run yet.
- **No historical data has been acquired at full scale yet.** Stage 3A
  pipeline validated against a 29-match excerpt; full 5-season ×
  3-competition acquisition pending (see
  `research/cycles/CYCLE_001/CYCLE_PLAN.md`).

**No edge has been validated. No hypothesis has been promoted. Nothing
in this repository currently supports a real-money betting decision
beyond the basic commission-adjusted EV arithmetic on a single quoted
price.**

## Google Sheets workbook status

A workbook (`Prediction Markets Lab.xlsx`) containing all 15 tabs (10
operational + 5 research: Hypotheses, Behaviour Atlas, Research Runs,
Research Priorities, Model Registry) has been generated, recalculated
with zero formula errors, and uploaded to Google Drive. Open it from
Drive and choose "Open with Google Sheets" to edit it as a native
Sheet on desktop or mobile.

## Known limitations

- No live data ingestion — everything is calculation logic, sample
  fixtures, and (for research) seeded-but-untested hypotheses.
- No sport-specific probability model yet (`P_model` is not
  implemented); only the corrected, margin-free bookmaker consensus is
  calculated end-to-end.
- Confidence, data-quality, and liquidity scores are boolean/manual
  inputs in Stage 1–2, not automated numeric scores.
- Bookmaker list (`config/bookmakers.yaml`) and commission rates
  (`config/commissions.yaml`) are placeholders/assumptions — verify
  before relying on them for a real decision.
- No CLI beyond the Stage 2 scripts (`scripts/generate_daily_shortlist.py`,
  `scripts/import_manual_odds.py`, `scripts/settle_results.py`).
- Grade C's exact boundary (a "watchlist" floor below Grade B) is not
  specified in the original brief; a conservative default
  (`grade_c_min_net_ev: 0.00`) has been assumed and documented in
  `config/thresholds.yaml`.
- Historical football data acquisition: STAGE 3A TOOLING COMPLETE —
  FULL ACQUISITION PENDING. Pipeline proven end-to-end against
  a 29-match excerpt (`data/samples/excerpt_validation/`); the full
  ~15-file, 5-season dataset has not been acquired, no data version is
  frozen, and no model or hypothesis test has been run. See
  `research/cycles/CYCLE_001/CYCLE_PLAN.md` and
  `docs/PHONE_ONLY_DATA_ACQUISITION.md`.
- The Research Engine's evidence-grading thresholds
  (`config/research_thresholds.yaml`) are initial research defaults,
  not derived from a formal power analysis — revisit once real
  out-of-sample/paper history exists.

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full Stage 2–6 plan.
