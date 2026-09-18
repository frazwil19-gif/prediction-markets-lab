# Daily Probability & Bet-Selection Engine — V1 Design & Migration Report

**Date:** 2026-09-18
**Status:** AUDIT AND REDESIGN ONLY, per the operator's explicit instruction. No new models built,
no data acquired, no bets placed, no automation implemented, no Cricket work started.
**Trigger:** Operator's "MAJOR PROJECT DIRECTION CHANGE — DAILY PROBABILITY & BET-SELECTION ENGINE"
instruction (relayed by Fraser, 2026-09-18), correcting the project's drift toward proving
persistent market inefficiency as an end in itself.

This document answers the operator's 34-point required return in full, in order. It also carries a
finding the operator did not anticipate and that materially changes the shape of the work ahead:
**most of the infrastructure this new objective requires already exists**, built in Stage 1-2 before
the project ever acquired historical data, and left dormant while Cycles 1-2 pursued pure
market-inefficiency research. This is a reconnection project more than a from-scratch build.

---

### 1. Confirmation that Cricket has been PAUSED

Confirmed. Cricket T20 was never started — no acquisition, no code, no data. It was next in the
research-pipeline queue (per the roadmap's §6) only because Football Cycle 2 and Tennis Workstream B
had both closed. That queue position is now irrelevant: Cricket does not begin, and no repository
work of any kind touches it, until the daily engine's V1 scope is settled and this audit's decision
gate is resolved.

### 2. Confirmation that previous Football/Tennis results are preserved

Confirmed, and verified directly against the repository: nothing has been deleted, rewritten, or
reframed as a failure. `research/cycles/CYCLE_001/`, `research/cycles/CYCLE_002_TENNIS/`, and
`research/cycles/CYCLE_003_FOOTBALL/` remain exactly as committed — including Stage 3B's
MARKET DOMINATES / NULL RESULT verdict, Tennis Cycle 1's PARTIAL holdout verdict, Tennis Workstream
B's clean 13-for-13 REJECT, and Football Cycle 2's H-FB2-001 DEVELOPMENT-REJECT / H-FB2-002
sealed-OOS FAIL. These answered a real, well-posed question — *can a specific information/hypothesis
family systematically beat the market's own price?* — and the honest null/negative answers they
returned are permanent scientific record, not discarded work. The new objective asks a different
question (see §3) and does not require any of these verdicts to be different, better, or reopened.

### 3. Exact restatement of the new project objective

**Old (implicit) objective**: model probability > market probability → prove systematic mispricing →
validate out-of-sample → trade the mispricing.

**New objective**: build an automated, multi-sport **daily probability and bet-selection engine**
that, every day: discovers today's events and markets → estimates the probability of every
proposition the project has a validated model for → ranks by probability → retrieves current odds →
computes break-even probability, fair odds, and EV → rejects propositions whose price is
uneconomical however likely → ranks the remainder on probability, EV, uncertainty, calibration,
sample support, data quality, liquidity, and risk → produces a Daily Card of BET / WATCH / REJECT →
lets Fraser manually place approved bets → logs every recommendation, price, execution, result, CLV,
stake, and P&L → feeds results back into monitoring/recalibration.

The operative sequence is **probability first, price/value second, risk third, decision last** — not
"prove the market is wrong." A model's probability is not required to disagree with, let alone beat,
the market's own probability; it is required to be *trustworthy* (well-calibrated, honestly
uncertain where sample support is thin). Value comes from comparing a trustworthy probability against
a **specific, currently obtainable price**, which can come from price dispersion across venues just
as validly as from a genuinely independent statistical model. §12-13 below make this operational.

### 4. Existing infrastructure reusable for the new objective

This is the audit's central finding. A full repository walk (`src/prediction_markets_lab/`, `docs/`,
`config/`, `templates/`, `scripts/`) shows a substantial, already-tested production layer was built in
**Stage 1 (calculation engine) and Stage 2 (manual workflow + research governance)**, *before* any
historical data was acquired, then never connected to a live feed because Cycle 1's research found no
edge to power it with and the project moved into pure hypothesis-testing mode (Cycles 1-2). None of
this needs to be rebuilt:

- **Calculation engine (Stage 1, fully tested)**: `probability/odds_conversion.py`,
  `probability/margin_removal.py` (proportional overround removal, corrected to per-bookmaker
  grouping), `probability/consensus.py`, `probability/market_pipeline.py`, `probability/uncertainty.py`
  — everything needed to turn a set of bookmaker/exchange prices into a de-vigged consensus
  probability. `ev/break_even.py`, `ev/edge.py`, `ev/expected_value.py`, `ev/commission.py` —
  commission-adjusted EV exactly as the operator's worked examples require
  (`EV = model_probability × O - 1`, adjusted for exchange commission where relevant).
  `decisions/grading.py` — deterministic, config-driven A+/A/B/C/Reject grading
  (`config/thresholds.yaml`: e.g. Grade A+ requires net EV ≥ 8%, edge ≥ 4pp, ≥5 bookmakers).
  `decisions/confidence.py`, `decisions/data_quality.py`, `decisions/liquidity.py`,
  `decisions/recommendation.py`. `risk/staking.py` (fixed stake per grade, hard-capped),
  `risk/bankroll.py`, `risk/exposure.py`, `risk/loss_locks.py`, `risk/decision_gates.py`
  (martingale/loss-chasing explicitly forbidden by construction, matching the master directive).
- **Manual workflow (Stage 2, fully tested)**: `ingestion/manual_odds_loader.py` and
  `ingestion/exchange_price_loader.py` (CSV templates already exist:
  `templates/manual_odds_entry.csv`, `templates/exchange_price_entry.csv`), correctly grouped by
  bookmaker for margin removal. `reports/daily_report.py`, `reports/markdown_renderer.py`,
  `scripts/generate_daily_shortlist.py`, `scripts/settle_results.py`,
  `storage/csv_store.py`/`storage/sqlite_store.py`/`storage/google_sheets_adapter.py`. A Google
  Sheets workbook already exists (10 operational + 5 research tabs). Templates for the daily scan,
  trade record, and even a `chatgpt_daily_prompt.md` already exist.
- **Persisted schemas already matching almost exactly what the operator's point 19 asks for**
  (`storage/schemas.py`, Pydantic models, already tested): `BookmakerOddsRecord`, `MarketRecord`,
  `DailyShortlistRow` (rank, event, selection, odds, probability, net EV, grade, stake, expiry note,
  action, status — this **is** the Daily Card row schema, already built), `BetRecord` (execution
  price, requested vs. matched odds, stake, estimated/implied probability, grade, bankroll
  before/after, result, gross/net profit, commission, **closing odds/probability/CLV fields already
  present**), `ResultRecord`, `BankrollTransaction`, plus the historical-data schemas from Cycle 1.
- **Football historical infrastructure (Cycles 1-2, fully tested)**: the E0/E1/SC0 acquisition,
  audit, canonicalisation, and margin-removal pipeline; leakage-safe rolling features
  (`features/football_leakage_safe_features.py`); the frozen, unmodified Elo (`models/football_elo.py`)
  and Poisson (`models/football_poisson.py`) baselines; chronological split enforcement
  (`validation/time_splits.py`); calibration/Brier/log-loss/AUC machinery
  (`performance/calibration.py`, `brier.py`, `log_loss.py`, `binary_classification.py`); bootstrap
  CI methodology used consistently across every cycle to date.
- **Tennis historical infrastructure (Cycle 2, fully tested)**: TML-Database ATP results
  2021-2025 with rank/age/hand/height/country and full match-level serve/return stats
  (aces, double faults, serve points, break points); the frozen Global Elo model
  (`models/tennis_elo.py`, k_factor=32.0); Betfair historical market data 2021-2025 plus a
  Jan-Sep-2026 BASIC-tier sample, with tested linkage (`normalisation/tennis_betfair_linkage.py`)
  and schema parsing (`ingestion/betfair_historical_schema.py`, `betfair_market_index.py`,
  `exchange_price_loader.py` for manual exchange-price entry).
- **Research governance layer**: `research/schemas.py` (Hypothesis pydantic model, legal-transition
  enforcement), `research/registry.py`, `research/behaviour_atlas.py`, `research/evidence_grading.py`,
  `research/research_prioritisation.py`, the verdict classifiers (`development_verdict.py`,
  `holdout_verdict.py`, `oos_verdict.py`) — this stays exactly as-is and continues to govern any
  future *research* claim (a new hypothesis, a new model, a new market family). It is not replaced by
  the production layer; the two are distinct and must stay distinct (see §26).

**718/718 tests pass across all of this today.** The daily engine does not start from zero; it starts
from reconnecting a tested calculation/decision/persistence layer to (a) a trustworthy probability
source and (b) a today's-events-and-prices intake process — both currently missing, and both scoped
below (§17-20).

### 5. Existing infrastructure to deprioritise

Nothing is deleted. Deprioritised, in the sense of "not the next thing built or extended":

- Any further pure market-inefficiency hypothesis testing under the Cycle 1/2/Workstream-B pattern —
  H-FB-001 through H-FB-006 and H-TN-001 through H-TN-005 remain seeded in
  `research/hypotheses/hypothesis_registry.csv` at IDEA/DATA_REQUIRED, exactly as Stage 2 left them,
  and stay there. They are not deleted, but they are not the next research priority either — see §12.
- `docs/ARCHITECTURE_FREEZE_V1.md`, which froze new-infrastructure-building in favour of
  evidence-generation back at Stage 2. That freeze explicitly says it can be "revisited once
  [Cycle 1's] findings identify a genuine, specific gap in the existing architecture — not before."
  This objective change **is** that genuine, specific gap (a live-data intake layer that never
  existed), so the freeze needs an explicit supersession note, not a violation — see §30.
- `ingestion/odds_api_loader.py` remains a Stage-6 placeholder (confirmed empty on inspection,
  containing only a docstring) — it is not wired to any real API yet and is not the recommended next
  build (see §11/§27: The Odds API's free tier is real but narrow, and doesn't cover exchange prices
  or prop markets at all).
- The formal, heavier `research/behaviours/behaviour_atlas.csv` (still empty — header row only) stays
  reserved for hypotheses that survive formal pre-registration; it is not repurposed as the daily
  engine's model registry (that is a new, separate concern — see §14/§19).

### 6. Existing historical datasets available

| Sport | Dataset | Depth | Notes |
|---|---|---|---|
| Football | Football-Data.co.uk E0 (Premier League), E1 (Championship), SC0 (Scottish Premiership) | 2020/21-2025/26, ~6,960 matches total (5,800 through 2024/25 + 1,160 for 2025/26) | 1X2 (6-bookmaker panel through 2024/25, 8-bookmaker panel from 2025/26 — see the schema-drift fix in commit `adcc1aa`), Over/Under 2.5, Asian Handicap (Bet365+Pinnacle only, full corpus), shots, shots-on-target, corners, fouls, cards, referee — all at opening and closing prices. |
| Tennis | TML-Database ATP tour-level | 2021-2025, 14,668 matches | Rank/age/hand/height/country/surface/tournament-level at time of match, plus **post-match** serve/return stats (aces, double faults, serve points, 1st/2nd serve won, break points saved/faced) — useful for building historical rolling player-quality features, not usable as pre-match predictors directly. |
| Tennis | Betfair Historical Stream data (BASIC/free tier) | 2021-2025 (996,779 files, 88.96% MATCHED to TML) + Jan-Sep 2026 sample (161,025 files, 100% MATCHED) | Confirmed real market types beyond Match Odds: `SET_WINNER`, `SET_BETTING`, `HANDICAP` (and very likely totals/game-handicap variants, unconfirmed at the granularity needed for a market inventory — flagged for the V1 audit task, not yet done). BASIC tier: last-traded-price only, no back/lay ladder, no volume — a research proxy, not an executable price. |

No new historical data has been acquired for this report. This table is what already exists; §7-11
assess what it can and cannot support.

### 7-11. Football and tennis proposition/market inventory

This is the operator's own required audit (points 7-11: which propositions can be reconstructed
historically, which have predictor data, which have historical prices, which can obtain current
prices). Answered per candidate family, football first:

| Proposition | Historical outcome constructible? | Predictor data (leakage-safe)? | Historical price? | **Current/live price obtainable?** | Verdict |
|---|---|---|---|---|---|
| Match result (1X2) | Yes — full 2020/21-2025/26 corpus | Yes — Elo, Poisson, market consensus, rolling form (all already built) | Yes — 6-8 bookmaker panel, both opening/closing | **Yes** — every mainstream bookmaker/exchange prices this; manual entry today, The Odds API could automate this specific market (see §27) | **Immediately usable for V1.** No model has beaten market here (Stage 3B), but the market's own de-vigged consensus is itself a trustworthy probability — see §12's Option A. |
| Over/Under 2.5 goals | Yes | Yes — same infra as 1X2 | Yes — Bet365+Pinnacle full corpus | Yes — widely quoted by every bookmaker/exchange | **Immediately usable for V1**, same reasoning as 1X2. |
| Asian Handicap | Yes — a tested settlement function exists (whole/half/quarter lines, built for H-FB2-001) | Yes | Yes — Bet365+Pinnacle full corpus | Yes — widely quoted, though line selection (which handicap value) must match exactly between probability source and price | **Usable for V1** with care on exact-line matching; H-FB2-001's own research found no *signed* mispricing here, but that doesn't block using the market's own AH consensus as a trustworthy probability, same as 1X2/O-U. |
| Team goals / total match goals variants (O/U at other lines, both-teams-to-score) | Partial — goals-scored data exists, so any total-goals line is constructible historically, but only the 2.5 line has been extracted/priced so far | Yes, same underlying data | **Not yet extracted** — Football-Data.co.uk carries only the 2.5 line for O/U in the current canonicalisation | Plausible (bookmakers quote multiple lines and BTTS widely) but unverified for our specific sources | Requires a small, scoped extraction extension (reuse `football_richer_extraction.py`'s pattern) before it can join V1 — not zero-cost, but low-cost and low-risk. |
| Corners | Yes — raw corner counts exist for the full corpus (already extracted as `HC`/`AC` columns, feeding `cycle_002_match_statistics.csv`) | Yes — rolling corner-differential features could be built the same way SOT rolling features were (this exact leakage-safe pattern is proven, from H-FB2-002) | **No** — Football-Data.co.uk does not publish historical corners *odds*, only the raw match-report count | **Uncertain.** Corners markets exist on some bookmakers/exchanges but no confirmed free bulk historical price archive, and no confirmed reliable live-price source either (flagged as unverified in §19 of the earlier roadmap, unchanged). | **Feature-only for now, not a V1 market.** Corner counts can improve 1X2/O-U models as predictors; corners cannot be a *tradable proposition* in V1 without a verified live price source, which does not currently exist for free. |
| Cards | Yes — raw yellow/red counts exist | Yes, same pattern as corners | **No**, same as corners | Same uncertainty as corners | Same verdict as corners: feature-only, not V1-tradable. |
| Shots / shots-on-target (team totals, as their own market) | Yes — raw counts exist | Yes — this is exactly H-FB2-002's now-closed research feature | **No** — no historical SOT-market odds exist in our sources | Same uncertainty as corners/cards; shots/SOT player- or team-total props exist at some bookmakers but are thin, low-liquidity, and have no confirmed free price feed | **Feature-only, not V1-tradable.** This is the single most important correction to the operator's own worked example (Barcelona SOT market): the *feature* is real and already built; a *tradable SOT market* with a genuine current price is not currently available to this project for free. |
| Player props (goals, shots, cards) | No — Football-Data.co.uk is match-level only, no player-level data in any acquired source | No | No | No | **Out of scope entirely until a new data source is acquired and separately justified**, per the master directive's cost/evidence-value rule (§11 of that document). |

Tennis:

| Proposition | Historical outcome? | Predictor data? | Historical price? | Current price? | Verdict |
|---|---|---|---|---|---|
| Match winner | Yes — full corpus | Yes — Global Elo (frozen, PARTIAL-validated), ranking baseline, market consensus | Yes — Betfair BASIC last-traded-price, 2021-2025 + Jan-Sep 2026 | Plausible via Betfair Delayed App Key (free, see §27) or manual entry | **Immediately usable for V1**, same "market consensus as trustworthy probability" reasoning as football 1X2. |
| Set winner / set betting | Outcome constructible from TML score strings (not yet parsed to per-set granularity) | Not yet built | Confirmed present in real Betfair data (`SET_WINNER`, `SET_BETTING` market types, per the Workstream B sample audit) but never linked or modelled | Same uncertainty as historical price — unconfirmed live availability | **Requires new, scoped work** (per-set outcome parsing + a simple model) before it could join V1; not zero-cost but plausible given Betfair already covers it. |
| Handicap (games) | Not yet — would need game-by-game score parsing from TML's `score` field | Not yet built | Confirmed present in real Betfair data (`HANDICAP` market type) | Unconfirmed | Same as set betting: real candidate for a later V1 iteration, not immediately available. |
| Total games / games props | Not yet | Not yet built | Unconfirmed presence in the Betfair sample (not specifically checked this audit) | Unconfirmed | Needs its own scoped audit before any commitment — explicitly not assumed favourable, per this project's standing discipline. |

### 12. Ranked V1 market-family candidates

1. **Football 1X2** — full historical depth, full predictor/model infrastructure, full historical
   price coverage, current prices obtainable today (manually, at minimum). Highest rank.
2. **Football Over/Under 2.5** — same reasoning, same infrastructure, tied for highest rank.
3. **Tennis Match Winner** — same reasoning; Global Elo is only PARTIAL-validated (2025 holdout CI
   narrowly included zero) but that is *irrelevant* to using the market's own consensus as the
   probability source (see §13's Option A) and still relevant as a secondary diagnostic.
4. **Football Asian Handicap** — same infrastructure, slightly more execution complexity (exact-line
   matching between probability source and price).
5. *(lower rank, requires new scoped work before inclusion)* Football Over/Under at additional lines,
   Both Teams To Score.
6. *(lower rank, requires new scoped work)* Tennis Set Betting / Handicap.
7. *(not a V1 market under any current data)* Football corners/cards/shots as their own tradable
   propositions — real, already-built features, but no current price source.

### 13. Recommended initial V1 scope

**Two genuinely different ways to generate a "model probability," and V1 should use both, kept
explicitly separate and separately labelled on the Daily Card:**

- **Option A — Sharp-consensus-vs-price-dispersion screening.** The probability estimate for a
  proposition *is* the de-vigged consensus computed from the sharpest available prices (existing
  `probability/consensus.py` + `margin_removal.py`, unchanged). The "value" comes from comparing that
  consensus against a *different, currently obtainable* price — a softer bookmaker's price, or a
  stale/mispriced line — never against the same source's own price (that would be EV≈0 by
  construction, minus margin). This is classical price-shopping/soft-book value-hunting: **zero new
  modelling risk, zero new research debt, 100% already-built and already-tested infrastructure.**
  It requires no probability model to "beat the market" — it only requires enough independent price
  quotes to detect where one quote disagrees with the consensus of the others. This is the
  **recommended V1 core**, because it is provably buildable this week from existing, tested code.
- **Option B — Genuine statistical models for markets thin enough that no efficient consensus
  exists.** This is where the frozen Elo/Poisson models, and any future model built on the SOT/corner/
  card features already extracted, belong. Stage 3B's null result means Option B is **not** expected
  to add value on football 1X2 specifically (the market there is efficient against these particular
  models) — but that finding says nothing about thinner markets (a niche competition, an unusual
  line) where Option A's price-dispersion signal may be weak or absent. Option B candidates must go
  through this project's existing research discipline (pre-register, backtest, chronological OOS,
  calibrate) before joining the daily scanner — they are not exempt from that process just because
  the objective changed.

**V1 scope, concretely: Football 1X2 + Over/Under 2.5 + Asian Handicap, via Option A
(price-dispersion/value screening) as the daily scanner's first live capability, with Tennis Match
Winner added once the football path is proven end-to-end.** This is the smallest system that produces
a genuine, economically meaningful Daily Card using only infrastructure that already exists and is
already tested. Option B candidates (SOT-informed 1X2 refinement, once-closed H-FB2-002's feature
without its now-failed hypothesis framing, set betting, etc.) are explicitly V2+ research work, not
blocked from ever happening, but not gating V1.

### 14. Probability-model approach for each V1 family

For the V1 (Option A) scope, the "model" is the existing de-vigged multi-bookmaker consensus — no new
model-fitting is required. The frozen Elo (football) and Global Elo (tennis) models remain available
as **secondary diagnostics** on the Daily Card (labelled as such, never presented as the primary
probability), both because they are already built and because a large model-vs-consensus disagreement
is itself a useful data-quality/sanity flag even without asserting the model is right.

### 15. Chronological/OOS validation design

Not newly required for Option A, because the consensus-probability approach is not a new claim about
predictive skill — it is the market's own probability, whose calibration properties are already
extensively documented across every prior cycle (Stage 3B, Tennis Cycle 1, both Football Cycle 2
hypotheses used market consensus as their benchmark throughout). Any Option B candidate must go
through the existing, unmodified chronological-split + pre-registration + sealed-OOS discipline
before it is added to the scanner — no shortcut is introduced by the objective change.

### 16. Calibration requirements

For Option A, calibration monitoring is still required in production (not development) — track actual
outcome rates within probability bands on every logged recommendation (reusing
`performance/calibration.py`, already built and tested) as a live data-quality check, since consensus
quality can degrade (thin bookmaker panel, stale lines) even though the underlying method needs no new
validation. For any Option B candidate, the existing calibration bar (log loss, Brier, ECE,
calibration slope/intercept, AUC where applicable, pre-registered thresholds) applies unchanged.

### 17. Daily production architecture

```
Historical DB (existing, frozen per cycle)
    |
Feature Engineering (existing, football_leakage_safe_features.py pattern; extend only for new V1 markets)
    |
Validated Probability Source
    -> Option A: live multi-price consensus (NEW: needs a current-price intake step, see below)
    -> Option B: frozen/validated models (existing: football_elo.py, tennis_elo.py; future models per §15)
    |
Model/Method Registry (NEW, small: which method backs which market, its validation status, its version)
    |
Today's Event Scout (see §18 -- for V1, event/market discovery stays operator-assisted, not scraped)
    |
Today's Price Intake (see §20 -- manual entry via the EXISTING templates/manual_odds_entry.csv +
                       exchange_price_entry.csv, unchanged from Stage 2's design)
    |
Probability Engine (existing consensus.py, run on today's prices)
    |
Fair Odds / EV Engine (existing ev/*, unchanged)
    |
Uncertainty / Risk Engine (existing decisions/*, risk/*, unchanged)
    |
Decision Engine (existing decisions/grading.py, unchanged -- config-driven thresholds already in
                  config/thresholds.yaml)
    |
Multi Constructor (NOT built yet -- correctly so, see §22; deferred until singles are proven live)
    |
Daily Card (existing DailyShortlistRow schema + reports/daily_report.py, unchanged)
    |
Manual Execution Log (existing BetRecord schema + scripts, unchanged)
    |
Results / CLV / P&L (existing settle_results.py + BetRecord's CLV fields, unchanged)
    |
Monitoring / Recalibration (existing performance/* modules; needs a new small script to run them
                             on live BetRecord history rather than only backtest output)
```

The only genuinely new pieces are: a current-price intake mechanism (§20, kept deliberately manual for
V1 — this is not a gap, it is a design decision matching the master directive's existing "manual
execution first" doctrine, §9) and a thin Model/Method Registry recording which method backs which
market and its validation status (small, config-driven, not a rebuild).

### 18. Scheduled-task architecture

Per `docs/DAILY_WORKFLOW.md`'s own original (Stage-2, never-implemented) design, event/market
discovery for V1 is **operator-assisted** (the ChatGPT-side research operator screens today's
fixtures and candidate markets in conversation, exactly as originally specified), not a new scraping
service — this avoids a real, unbudgeted new-acquisition cost (a live fixtures API, see §27) and
matches the project's "smallest defensible system" instruction. Proposed task shape, using GitHub
Actions where the workload is deterministic and stays operator-assisted where it isn't:

- **Task A (manual/operator-assisted)** — morning fixture + candidate-market identification for the
  frozen competitions (E0/E1/SC0, ATP).
- **Task B (manual, Fraser)** — current price entry via the existing CSV templates, for exactly the
  candidates Task A flagged (bounded, not a full-market scan, since V1 has no live odds feed).
- **Task C (GitHub Actions, deterministic, new but small)** — run the existing consensus/EV/grading
  pipeline on Task B's CSV, produce the Daily Card via the existing `reports/daily_report.py`.
- **Task D (manual, Fraser)** — place any BET-grade recommendation manually; log via the existing
  `BetRecord` schema/template.
- **Task E (GitHub Actions, deterministic, extends the existing `settle_results.py` +
  `weekly_report.yml`/`data_validation.yml` pattern)** — nightly settlement, CLV computation,
  calibration/performance monitoring on the accumulating live `BetRecord` history.

No task in this list requires automated execution, browser automation for staking, or a paid data
feed. This is deliberately the *smallest* automatable slice — Tasks A/B remain manual exactly because
no free, verified, sufficiently-covering live odds/fixtures API exists yet for every V1 market (see
§27); automating them further is a §33 concern, not a V1 requirement.

### 19. Proposed database schemas

Almost entirely reuse. `storage/schemas.py` already defines `BookmakerOddsRecord`, `MarketRecord`,
`DailyShortlistRow` (= the operator's `daily_cards`/`bet_candidates`), `BetRecord` (=
`manual_executions` + `settlements`, already includes CLV), `ResultRecord`, `BankrollTransaction` (=
`bankroll_history`). Genuinely new, small additions needed: an `events` table (today's fixture-level
identity, currently implicit rather than modelled explicitly), a `feature_snapshots` table (freezing
the exact predictor values used for a given day's probability, for reproducibility — the existing
research feature-engineering code computes features but has never had to snapshot them for a specific
production run), a `model_predictions` table (recording, per proposition per day, which method
produced the probability, its version/hash, and the raw value — this is the "Model/Method Registry"
output from §17), and a `model_performance` table (aggregating calibration/CLV/ROI over time from
accumulated `BetRecord` rows — the calculation functions already exist, only the aggregation-over-time
table is new). Every recommendation remains reproducible from: timestamp, data version, feature
snapshot, model version/hash, probability, odds, and the exact decision thresholds in force that day
— consistent with the project's existing provenance discipline (frozen data-version hashes, commit
precedence, etc.) used throughout every research cycle to date.

### 20. Odds/value methodology

For V1 (Option A): the probability **is** the de-vigged consensus of all quoted prices for a
proposition (existing method, unchanged); the price compared against it is the single best currently
obtainable price from a different venue/bookmaker (manually entered by Fraser via the existing CSV
templates, exactly as `docs/DAILY_WORKFLOW.md` originally specified). `EV = model_probability × O - 1`
(existing `ev/expected_value.py`), commission-adjusted for exchange bets (existing `ev/commission.py`).
No change to the existing formulas; the change is only in what feeds them daily.

### 21. Recommendation-expiry/staleness methodology

`DailyShortlistRow.price_expiry_note` already exists as a field but is not yet populated by any rule.
New, small addition: a staleness threshold (config-driven, e.g. "recommendation expires N minutes
after the price was entered, or at kickoff minus M minutes, whichever is sooner") — this needs a
concrete default chosen and documented in `config/thresholds.yaml`, but is a configuration addition,
not new architecture.

### 22. Multi-bet methodology and restrictions

Unchanged from the master directive (§4) and this instruction's own explicit rules: singles only for
V1; a future ≤2-leg multi only from independently-qualified legs, correlation estimated and bounded,
correct joint-probability calculation, combined-margin accounted for, combined EV must beat the
singles; same-game multis remain unsupported until a proper joint-probability framework exists; never
manufacture legs to reach a target price. No multi-constructor code exists yet and none is built for
V1 — this is explicitly deferred, matching the operator's own "multis are secondary" instruction.

### 23. £30 bankroll/manual-execution design assumptions

`config/bankroll.yaml` and `risk/staking.py` already implement fixed-stake-per-grade (not Kelly),
hard-capped by `maximum_stake_gbp`, with daily/weekly loss-stop and max-open-bets gates
(`risk/loss_locks.py`, `risk/exposure.py`) — this already matches the operator's explicit "no
Martingale, no chasing losses, no forced daily bets, £0 profit on a no-opportunity day is correct"
requirements without any new code. The existing `config/bankroll.yaml` values need to be reviewed
against the real ~£30 starting figure and the grade-based stake caps in `config/thresholds.yaml`
(currently £0.25-£0.50 max per grade — very conservative relative to the operator's stated £3-5
comfort level) reconciled with the master directive's own explicit note that the staking layer
"remains unaddressed and unjustified" pending validation. Fractional Kelly is not implemented and
should not be, per both the master directive and this instruction, until staking-simulation work
happens — which is itself gated behind live paper-trading history existing at all.

### 24. Logging/settlement/CLV framework

Already built and tested: `scripts/settle_results.py`, `BetRecord`'s closing-odds/closing-probability/
CLV fields, `performance/clv.py`, `performance/roi.py`, `performance/drawdown.py`,
`performance/attribution.py`. This framework has simply never been run against real live
recommendations, because none has existed since Stage 2. No new code is required to start logging
real Daily Card recommendations and their outcomes; only real data.

### 25. Model-monitoring/recalibration framework

`performance/calibration.py`, `performance/calibration_report.py`, and `reports/monthly_report.py`/
`weekly_report.py` already exist and are tested against synthetic/backtest data. New, small addition:
point these at the accumulating live `BetRecord`/`ResultRecord` history instead of (or alongside)
backtest output, and define an explicit recalibration trigger (e.g. "if realised calibration in any
probability band drifts beyond X over N logged recommendations, flag for review") — a configuration
and orchestration addition, not new statistical machinery.

### 26. Exact distinction between research and production

**Research pipeline** (unchanged, governs any new *claim*): observe → audit → discover → pre-register
→ backtest → chronological OOS → sealed holdout → only then eligible for production. This is what
Cycles 1-2 and Workstream B ran, and what any Option B candidate (a new prop model, a new market
family) must still run through before it can appear on a live Daily Card. **Production pipeline**
(what this report designs): takes only methods that have already cleared the research pipeline (or,
for Option A, that require no new predictive claim at all — the market consensus's calibration
properties are not a new hypothesis) and runs them daily against today's real prices to generate
actionable, logged, EV-ranked recommendations. A method never skips from "looked interesting in
discovery" straight into the Daily Card — Option A's price-dispersion screening is admissible into V1
specifically because it makes no such skip; it doesn't assert any new predictive skill, only that
independently-sourced prices sometimes disagree, which is measurably true by construction whenever it
occurs.

### 27. What new data/APIs are actually required

- **Nothing is strictly required for V1** (Option A, manual price entry, operator-assisted event
  discovery) — this can start today using existing code, existing templates, and Fraser's phone.
- **For semi-automating price/fixture intake later** (explicitly not required for V1, evaluated for
  completeness per the operator's request): `football-data.org`'s free tier gives 10 requests/minute
  and fixture/schedule data for 12 major competitions **including Premier League and Championship,
  but NOT the Scottish Premiership** — SC0 would still need a manual or different source. The Odds
  API's free "Starter" plan gives 500 credits/month (credits = markets × regions per call, not raw
  request count) covering many bookmakers but **explicitly not Betfair/exchange prices**, and there is
  no indication it covers corner/card/shot prop markets at all. Betfair's own API has a genuinely free
  **Delayed** Application Key (read-only market catalogues and prices, at a data delay) — sufficient
  for pre-match screening well before kickoff, but a **Live** Application Key costs a one-off **£499**
  fee and, critically, does **not** permit read-only use at all (betting functionality is required) —
  so there is no free or even one-off-affordable path to low-latency live prices via Betfair's own
  API; manual price-checking at execution time remains necessary regardless of any future automation
  investment. None of this changes the V1 recommendation in §13.
- **Nothing** is required for corners/cards/shots to become tradable propositions, because no free
  historical *or* live price source has been found for them at all — this is a data-availability wall,
  not a budget question, and is why §12 keeps them feature-only.

### 28. Expected monetary cost

**£0 for V1**, per §27 — every component either already exists or uses genuinely free tiers/manual
entry. The only cost identified anywhere in this audit is the £499 one-off Betfair Live Application
Key fee, which is not needed for V1 and is explicitly not recommended until Phase 2/3 execution
automation is separately justified (per §33 and the master directive's existing automation gate).

### 29. Tests/code/docs that can be reused

Essentially all of §4's inventory: 718 passing tests covering the calculation engine, decision/risk
gates, historical ingestion/canonicalisation for both sports, the frozen models, the verdict
classifiers, and the existing manual-workflow scripts (`test_grading.py`, `test_staking.py`,
`test_evidence_grading.py`, `test_daily_report_pipeline.py`, `test_corrected_daily_shortlist.py`,
`test_settlement_script.py`, confirmed present and passing on inspection). Docs: `docs/PROJECT_PLAN.md`,
`docs/ROADMAP.md`, `docs/DAILY_WORKFLOW.md`, `docs/MARKET_RULES.md`, `docs/EV_METHODOLOGY.md`,
`docs/PROBABILITY_METHODOLOGY.md`, `docs/RISK_MANAGEMENT.md`, `docs/OPERATING_MANUAL.md`,
`docs/MOBILE_WORKFLOW.md`, `docs/PHONE_ONLY_DATA_ACQUISITION.md` all describe, in detail, almost
exactly the system the operator is now asking for — they were simply never executed against real
daily data. These should be reviewed and updated for currency (e.g. `MARKET_RULES.md`'s Tier 1
markets already match §12's V1 scope almost exactly) rather than rewritten from scratch.

### 30. Technical debt/risks created by the objective change

- **`docs/ARCHITECTURE_FREEZE_V1.md`** needs an explicit supersession/amendment note: it correctly
  froze new-module creation at Stage 2 pending a "genuine, specific gap," and this objective change is
  exactly that gap (a live-data intake and daily-orchestration layer). Proceeding without amending the
  freeze document would leave a stale, misleading governance record in the repo.
- **Stale config values**: `config/thresholds.yaml`'s stake caps (£0.25-£0.50) and `config/bankroll.yaml`
  need reconciling against the operator's ~£30/£3-5 figures and against whatever real bankroll Fraser
  actually starts with — currently inconsistent placeholders from Stage 1, not yet a considered
  decision.
- **The manual-price-entry bottleneck** is a genuine, honest constraint (not a solvable "todo"): V1
  cannot scan "3,481 markets" the way the operator's illustrative Daily Card implies, because there is
  no free live odds feed covering that breadth. The real V1 Daily Card will scan whatever handful of
  fixtures/markets Fraser and the operator manually identify and price each morning — a materially
  smaller number than the illustrative example, and this should be stated plainly to avoid the Daily
  Card format implying more automation than exists.
- **Dormant-code risk**: the Stage 1/2 modules have not been exercised against real data in roughly
  eight months of project time (by commit history); before trusting them for real recommendations,
  a fresh read-through and a small integration test against one real day's manually-entered prices is
  warranted (this is exactly the "run it once before trusting it" step, not a rewrite).
- **Two parallel "Behaviour Atlas"-shaped registries already exist** (the formal, still-empty
  `research/behaviours/behaviour_atlas.csv`, and the informal `FOOTBALL_CYCLE_2_BEHAVIOUR_ATLAS.md`) —
  the new Model/Method Registry (§19) must be kept distinct from both, or the project will accumulate
  a third, confusing "atlas" concept.

### 31. Smallest implementation sequence from CURRENT STATE to first automatically generated Daily Card

1. Amend `docs/ARCHITECTURE_FREEZE_V1.md` with a supersession note (this report is the "genuine,
   specific gap" it required).
2. Reconcile `config/bankroll.yaml`/`config/thresholds.yaml` stake figures with a real starting
   bankroll and Fraser's actual risk comfort (a decision, not code).
3. Run the existing test suite and do a fresh read-through of the Stage 1/2 modules listed in §4 to
   confirm they still function as documented (no rewrite expected, just verification).
4. Pick one real day and one real fixture (e.g. a single E0 match) for a manual dry run: operator
   identifies the fixture, Fraser manually enters prices from 2-3 real sources into the existing CSV
   templates, run the existing `generate_daily_shortlist.py` → `daily_report.py` pipeline unmodified,
   inspect the output by hand.
5. Fix whatever the dry run surfaces (stale config, a schema mismatch, a rounding issue) — expect
   small issues, not architectural ones, given §4's findings.
6. Add the small, genuinely new pieces from §19 (`events`, `feature_snapshots`, `model_predictions`,
   `model_performance` tables) only once the dry run proves the existing schemas are sufficient
   without them, or once a specific reproducibility gap is actually hit.
7. Wire Task C/E from §18 into GitHub Actions once the manual dry run has been repeated successfully a
   handful of times by hand.
8. Only then extend scope from football 1X2/O-U2.5/AH to tennis match winner, then to any Option B
   candidate — one market family at a time, per §12's ranking.

### 32. What must be validated before Fraser risks £1

- At least a short run (the operator/Fraser should set the actual N, not this report) of **paper**
  Daily Card recommendations logged via the real `BetRecord` schema against real prices, with no money
  staked, to confirm the pipeline produces sane, reproducible EV/grade output on real data — not a
  fixed count invented here, since the master directive already requires paper trading before any live
  stake and this instruction does not relax that gate.
- Confirmation that the manual price-entry process is fast enough to be usable from a phone in the
  time actually available before kickoff (a genuine operational risk, not yet tested against a real
  clock).
- A reviewed, explicit stake-cap decision (§23/§30) so the very first live stake is a deliberate
  number, not a stale Stage-1 placeholder.

### 33. What must be validated before automated execution is ever considered

Unchanged from the master directive §9 and this instruction's explicit Phase 1→2→3 sequence: manual
execution first (measuring observed vs. obtainable odds, slippage, rejected selections, settlement
accuracy, real P&L, CLV) → assisted execution (system computes exact venue/selection/stake/min-price,
Fraser confirms manually) → automated execution only after paper + live validation shows the strategy
holds up (calibration intact, CLV positive, adequate opportunity frequency, execution assumptions
realistic), and even then restricted to Betfair/Betdaq exchange APIs only, never bookmaker bots (per
the master directive §6's automation-legality finding, unchanged and reconfirmed by this audit's
Betfair API research in §27: a Live key requires betting functionality, not just reads, reinforcing
that any automated execution work is a distinct, later, and separately-gated undertaking from V1).

### 34. Exact next decision gate

This report is audit and design only, as instructed — no model was built, no data acquired, no bet
placed, no automation implemented, no Cricket work started. The next decision belongs to
Fraser/the operator: **approve the V1 scope in §13** (Football 1X2 + O/U 2.5 + AH via price-dispersion
screening, manual price entry, operator-assisted event discovery, singles only, existing schemas) and
authorise the implementation sequence in §31 to begin at step 1 — or adjust the scope first. Nothing
in §31 proceeds without that approval, and nothing here reopens Cricket, Football/Tennis market-edge
research under the old objective, or any of the explicit HOLD items this instruction listed (no
purchasing data, no broad model development beyond identifying the smallest rational V1, no live
betting, no automated execution).
