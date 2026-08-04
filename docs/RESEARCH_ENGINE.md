# Research Engine

## Purpose

The calculation and workflow layers built in Stage 1–2 answer one
question per market: *"is this specific price mispriced right now?"*
That is necessary but not sufficient. Without a research layer, the
project risks becoming a loop of:

```
collect odds → calculate EV → place bets → track profit
```

— which cannot distinguish a genuinely repeatable edge from noise,
and has no mechanism to learn, retire bad ideas, or avoid re-testing
things already shown not to work.

The Research Engine adds a second question, asked at a slower
cadence: *"which categories of market, priced in which way, show
evidence of a real, repeatable, exploitable pattern — and how
confident are we?"*

## How this differs from the trading and reporting layers

| Layer | Question | Cadence | Output |
|---|---|---|---|
| **Trading** (Stage 1–2: probability, ev, decisions) | Is *this* price mispriced *right now*? | Per market, daily | A+/A/B/C/Reject grade + stake |
| **Reporting** (Stage 2: reports/) | What happened? | Daily/weekly/monthly | Markdown reports |
| **Research** (this document) | Is *this class* of situation *repeatably* mispriced? | Weekly/monthly | Hypothesis and Behaviour status changes |

The trading layer is allowed to act on a single day's numbers. The
research layer is explicitly not allowed to promote anything based on
a single day, a single profitable week, or a subgroup selected after
seeing results (see "Safeguards" below). It exists to slow down and
formalise claims that would otherwise live only in someone's head
("I've noticed home favourites seem overpriced lately").

## Scientific workflow

Every research idea moves through one lifecycle:

```
OBSERVE → HYPOTHESISE → DEFINE TEST → COLLECT DATA → BACKTEST →
OUT-OF-SAMPLE TEST → PAPER TRADE → EXPERIMENTAL LIVE → VALIDATE →
PROMOTE OR REJECT → MONITOR → RETIRE OR IMPROVE
```

- **OBSERVE** — something noticed in the data or the daily workflow
  (a recurring pattern, an anomaly, an external claim worth testing).
- **HYPOTHESISE** — turned into a falsifiable statement with a stated
  economic/market rationale (see Hypothesis Registry).
- **DEFINE TEST** — target metric, minimum sample size, test method,
  and (crucially) the in-sample and out-of-sample periods are fixed
  *before* looking at results.
- **COLLECT DATA** — gather what's needed; a hypothesis can sit here
  indefinitely if data isn't available yet (status `DATA_REQUIRED`).
- **BACKTEST** — evaluate against the pre-declared in-sample period
  only.
- **OUT-OF-SAMPLE TEST** — evaluate against the pre-declared
  out-of-sample period, which must not have influenced the hypothesis
  or its parameters.
- **PAPER TRADE** — evaluate against live, forward-looking paper
  trades (see `docs/VALIDATION_PLAN.md`).
- **EXPERIMENTAL LIVE** — small real-money exposure, clearly labelled,
  tracked separately from paper (as in `docs/VALIDATION_PLAN.md`).
- **VALIDATE** — evidence is assembled and graded (see Evidence
  Grading below).
- **PROMOTE OR REJECT** — a `VALIDATED` behaviour becomes eligible for
  normal-sized use in the trading layer; otherwise the hypothesis or
  behaviour is marked `REJECTED`.
- **MONITOR** — validated behaviours are watched for decay
  (`MONITORING` status).
- **RETIRE OR IMPROVE** — a monitored behaviour that stops working is
  retired; one that could be refined spawns a new, linked hypothesis
  rather than silently mutating the old one.

## How hypotheses are registered

Every research idea is a row in `research/hypotheses/hypothesis_registry.csv`
(schema: `src/prediction_markets_lab/research/schemas.py::Hypothesis`).
A hypothesis must state, before any testing begins:

- a falsifiable `hypothesis_statement`
- an `economic_or_market_rationale` (why would this exist — what
  behavioural, structural, or informational reason would create this
  pattern?)
- `required_features`, `target_metric`, `minimum_observations`,
  `test_method`
- `in_sample_period` and `out_of_sample_period` — fixed up front

See `docs/HYPOTHESIS_REGISTRY.md`-equivalent detail in
`research/hypotheses/hypothesis_registry.csv` itself and
`hypothesis_validation.py` for the enforced status machine.

## How behaviours are defined

A **hypothesis** is a claim to be tested. A **behaviour** (in
`research/behaviours/behaviour_atlas.csv`) is the accumulated evidence
record for a specific, precisely defined market pattern once it has
enough testing to be worth tracking in its own right — e.g. "Football:
short-priced home favourites (implied probability > 70%) in
televised/highly-popular fixtures are overpriced by bookmaker
consensus relative to exchange closing prices." One behaviour can
accumulate evidence from multiple hypotheses/tests over time; a
hypothesis is retired into a behaviour once there's enough to track
persistently, not before.

## How tests are conducted

`src/prediction_markets_lab/research/schemas.py::ResearchResult` is
the single record format for any completed test, whether backtest,
out-of-sample, paper, or live. Every `ResearchResult` records which
period it covers (`train_period`/`test_period`), so that a reader can
never confuse an in-sample number with an out-of-sample one.

## In-sample vs. out-of-sample separation

The `in_sample_period` and `out_of_sample_period` fields are set on
the **Hypothesis** at definition time, before any test is run, and are
immutable once status moves past `DEFINED` (enforced in
`hypothesis_validation.py`). A `ResearchResult` tagged as
out-of-sample must fall entirely within the hypothesis's declared
out-of-sample period — this is a data-quality check the Research
Engine can perform, not a formula.

## Paper vs. live evidence separation

Bets and Paper Trades are stored as separate CSV tables/Sheets tabs
(Stage 2), and `ResearchResult` records which the evidence came from.
Evidence grading (below) never merges paper and live samples into one
pooled statistic; it reports them side by side, and a behaviour cannot
reach Grade A on paper evidence alone.

## Multiple testing risk

Every hypothesis is assigned a `multiple_testing_family` — a label
grouping hypotheses that were tested against overlapping data or as
part of the same broad sweep (e.g. all "bookmaker dispersion" ideas
tested against the same football season). `research_prioritisation.py`
and `evidence_grading.py` both take family size into account: a
hypothesis that is the 1st test in its family needs a much lower bar
of statistical surprise to be credible than the 20th. Stage 1 of this
Research Engine does not implement a specific correction procedure
(e.g. Bonferroni, Benjamini-Hochberg) — the `multiple_testing_adjusted_p_value`
field on `ResearchResult` exists as a placeholder for when that's
added, and until it is populated, evidence grading treats an
unadjusted p-value from a large family with extra scepticism (see
`config/research_thresholds.yaml`).

## Promotion, rejection, retirement

- A hypothesis or behaviour is **promoted** only when it reaches
  evidence Grade A (see below) *and* a human reviews and accepts the
  `result_summary`/`promotion_reason`. The Research Engine never
  auto-promotes.
- **Rejected**: failed out-of-sample, paper, or live testing, or
  evidence is Grade C/INSUFFICIENT after a reasonable testing period.
  Rejected ideas move to `research/rejected_ideas/` with a dated note
  explaining why, and are tracked so they are not silently retested
  (see Safeguards).
- **Retired**: was validated and used, but live/paper evidence later
  decayed (`MONITORING` → `RETIRE`). A retired behaviour's history is
  kept, not deleted — it's useful evidence about how long an edge
  lasted.

## How future research priorities are selected

`research_prioritisation.py` scores candidate hypotheses/behaviours on
multiple factors (evidence strength, expected information gain, data
availability, implementation cost, expected signal frequency,
liquidity, independence from already-validated behaviours, overfitting
risk, relevance to current goals) and returns a priority tier
(P1/P2/P3/DEFER/DO_NOT_RETEST) with an explanation — never a ranking
by historical ROI alone, since that would systematically favour
overfit or lucky candidates.

## Staying lightweight

This is a side project run from a phone with a near-£0 budget. The
Research Engine deliberately:

- Uses CSV + a lightweight pydantic schema layer, matching the rest of
  Stage 1–2 — no database, no ML pipeline.
- Runs its heavy lifting (grading, prioritisation, report generation)
  as occasional scripts, not continuous services.
- Is updated mainly during **weekly or monthly reviews**, not daily —
  the daily phone workflow (ChatGPT scan → user checks prices → places
  or rejects → Sheets records the decision) is completely unchanged;
  see `docs/DAILY_WORKFLOW.md`. The Research Engine reads the
  accumulated Markets/Bets/Paper Trades/Results history in bulk,
  weekly, rather than requiring any per-market research bookkeeping
  from the user.
- Explicitly does not build machine-learning models, automated
  execution, paid APIs, or dashboards (see `docs/ROADMAP.md` scope
  boundaries) — it is a governance and bookkeeping layer over the
  calculation engine that already exists, not a new calculation
  engine.

## A note on claims

Building this framework does not itself constitute evidence that any
hypothesis is true. Every hypothesis seeded into the registry (see
`research/hypotheses/hypothesis_registry.csv`) starts at status `IDEA`
with no result — the Research Engine's job is to find out whether each
one holds up, including the likely outcome that most will not.
