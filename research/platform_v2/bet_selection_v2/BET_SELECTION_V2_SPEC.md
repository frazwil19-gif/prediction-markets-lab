# Bet-Selection V2 — Specification (Phase V2-6, pre-registered 2026-09-29, rule_version `bsv2-1`)

**Scope:** a PAPER research layer. It reads valid prospective predictions and real price snapshots, and records
immutable paper singles. It never places, stakes or recommends real bets. The Money Card, the frozen engines and
the prospective ledgers are unchanged. Config: `config/bet_selection_v2.yaml`. Committed **before** the first evaluation.

## Central question
Can accurate probabilities be bought at real prices that justify the risk? An accurate prediction (a calibrated P) and
an attractive bet (a real, available price above fair value by enough to pay for commission and risk) are different
things. Both are measured separately.

## Inputs (read-only)
- `predictions/unified_ledger.csv` + `predictions/unified_settlements.csv` (V2-5 platform, first valid snapshot per event).
- Executable price snapshots:
  - tennis exchange back for the predicted side (recorded in the ledger row at prediction time; Betfair, 5% commission);
  - tennis bookmaker h2h prices captured from the **same** paid Odds API response the tennis board already makes
    (`tennis_predictions/price_snapshots.csv`, added in V2-6, 0 extra credits);
  - football: the best available price per selection already on the daily card (`available_odds`, `bookmaker`,
    `price_timestamp`), 0 extra credits.
- Engine registry (`PROBABILITY_ENGINE_REGISTRY.json`) for evidence status.

**Probability-source price vs executable price.** The price used to *estimate* P (for example the Betfair back/lay midpoint)
is kept apart from the price that could actually be *taken* (the back price, or a bookmaker's quoted price). EV is only ever
computed against an executable price. Nothing is reconstructed or invented: a missing price is `NO_EXECUTABLE_PRICE`.

**Structural caveat (recorded before any results).** The validated engines are market-consensus engines. Against its own
source, EV is ≤ 0 by construction: the Betfair back price sits below the midpoint that produced P, and commission is charged
on top. So positive EV can only come from **price dispersion**, meaning one bookmaker quoting above the consensus/exchange
fair price. For tennis, bookmaker prices against a Betfair-derived P are an independent reference. For football, the card's P
is an inclusive bookmaker consensus that contains the priced book, which is a weaker reference, so candidates are tagged
`value_reference=INCLUSIVE_CONSENSUS`.

## Per-candidate fields (one candidate per prediction × executable price source)
P, fair odds `1/P`, decimal odds, source (book/exchange key), is_exchange, commission, snapshot timestamp, minutes to event,
price age, break-even probability `1/((odds−1)(1−c)+1)`, gross EV `P·odds−1`, net EV `P·(odds−1)(1−c)−(1−P)`, engine status,
data quality, value reference, decision and **all** reason codes (not just the first).

## Decision (applied to the best net-EV fresh candidate of each prediction)
Hard **REJECT** (any one): prediction not valid (research-only source) · engine unknown · event started · no executable price ·
price snapshot at/after start · price older than 240 min at evaluation · commission unknown for an exchange · net EV ≤ 0 ·
P < 0.50 · engine status outside WATCH statuses.

Otherwise:
- **PAPER_BET**: P ≥ 0.50, net EV ≥ 2%, odds ≥ 1.33, ≤ 24 h to start, price ≤ 240 min old, engine VALIDATED_HISTORICAL(+PROSPECTIVE).
- **MULTI_RESEARCH_ELIGIBLE**: not a PAPER_BET, but P ≥ 0.80 from a validated engine with a fresh real price (a research flag; no multi is built).
- **WATCH**: everything else that passed the hard rejections (0 < EV < 2%, outside 24 h, odds < 1.33, or a PROVISIONAL_PROSPECTIVE engine such as Double Chance).

Gates are the existing money gates copied as research baselines (thresholds.yaml). They are never lowered to force
selections; a day with no PAPER_BET is a valid, reported result.

## Immutable paper singles (`paper_betting_v2/`)
- `selections.csv`: append-only. `selection_id = sha256(rule_version | prediction_id)[:16]`, so each prediction can be paper-bet
  at most once per rule version; retries are idempotent. It stores frozen P, odds, source, snapshot time, decision time, minutes
  to event, net EV, stake (1 unit) and rule version. A selection is written only if decision time < event start and snapshot time < event start.
- `price_snapshots.csv`: append-only record of every evaluated real price. `snapshot_id = sha256(prediction_id|source|odds|snapshot_ts)[:16]`.
  Later snapshots never touch a selection. Later snapshots of a selected prediction give a closing-price proxy (CLV) for review.
- `settlements.csv`: append-only, keyed by `selection_id`. It joins the platform's verified settlement for the same `prediction_id`.
  Only `correct ∈ {0,1}` settles (WON/LOST); VOID → VOID; anything else stays PENDING (fail closed). The first settlement wins.
- An existing-row byte-prefix guard raises on any mutation. There is no backfilling: the runner cannot select an event that has started.

## Reporting (`reports/bet_selection_v2.{json,md}`)
Funnel: events scanned → valid predictions → high-P (≥70%) → priced → PAPER_BET / WATCH / MULTI_RESEARCH / REJECT (with reason
counts) plus the existing Money Card's money-qualified count (read, never changed). Results: paper bets, settled, win rate,
average P, average odds, expected vs realised net P&L (units), ROI/yield, max drawdown, longest losing streak, bankroll paths.
Breakdowns by sport, engine, P band, odds band and decision. No-bet days and negative findings are listed explicitly.
There are no profit projections.
