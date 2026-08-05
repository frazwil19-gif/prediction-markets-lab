# Changelog

All notable changes to this project are documented here. Format is
loosely based on [Keep a Changelog](https://keepachangelog.com/).

## [0.4.0] — Stage 3A: pipeline validated, full acquisition pending

**Status: STAGE 3A PIPELINE VALIDATED — FULL DATASET ACQUISITION PENDING.**

### Added

- Feasibility audit confirming Football-Data.co.uk access for E0, E1
  (direct fetch) and SC0 (full 2024/25 season verified live, identical
  schema).
- `ingestion.football_data_loader` — paced, retry/backoff-aware,
  HTML-error-rejecting, hash-verifying, atomic-write acquisition
  loader. 15 mocked-HTTP tests (cannot be tested against the live site
  from this project's own CI, per project instructions).
- `ingestion.football_bookmaker_extraction` — reconstructs
  per-bookmaker H/D/A triplets, separates opening/closing, rejects
  incomplete triplets, never counts Avg*/Max* as a bookmaker. Verified
  against genuine historical rows including a real missing-bookmaker
  case.
- `normalisation.team_names` / `competition_names` + `config/football_team_aliases.yaml`
  (76 real aliases seeded from observed data).
- `ingestion.match_identity` — deterministic match IDs, 5-way duplicate
  classification.
- `validation.time_splits` / `leakage_checks` — chronological split
  enforcement and reusable leakage guards for future model code.
- Canonical schemas: `HistoricalMatchRecord`,
  `HistoricalBookmakerMarketRecord`, `HistoricalConsensusRecord`.
- `docs/DATA_LEAKAGE_RULES.md`, `docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`
  (defines `proxy_clv` vs `true_execution_clv` — Football-Data prices
  are never to be reported as true exchange execution CLV).
- **29-match excerpt validation** (E0×10, E1×10, SC0×9), verbatim from
  live fetches, real SHA-256 hashes — proves the full pipeline
  (loader → extraction → normalisation → consensus) end-to-end.
  **Explicitly not the Cycle 1 dataset** — all artifacts under
  `excerpt_validation/` paths / `EXCERPT_VALIDATION_ONLY` suffixes.
- `research/cycles/CYCLE_001/` — CYCLE_PLAN.md, CYCLE_CONFIG.yaml,
  DECISION_LOG.md, HYPOTHESIS_SELECTION.csv, DATA_SPLIT_PLAN.md,
  DATA_FEASIBILITY_DECISIONS.md (all provisional pending full
  acquisition).

### Not done in this release

- Full 5-season × 3-competition acquisition (~15 files).
- Frozen `data_version`.
- Confirmed chronological split with real row counts.
- Any hypothesis test, model, or Behaviour Atlas entry.

### Test suite

179 (Stage 2) → **229 tests passing**, 0 failures.

## [0.3.0] — Stage 2 completion + Research Engine

### Fixed

- **Critical: corrected bookmaker consensus calculation.**
  `scripts/generate_daily_shortlist.py` previously computed a
  "consensus" probability from raw implied probabilities grouped only
  by `(market_id, selection)` — bookmaker margin was never actually
  removed, despite `probability.margin_removal` existing and being
  correctly unit-tested in isolation since Stage 1. This meant every
  daily shortlist recommendation was graded against an inflated
  probability estimate.
  - Root cause: `ingestion.manual_odds_loader` only exposed a
    per-selection view of the data, which loses the per-bookmaker
    grouping margin removal requires.
  - Fix: added `ingestion.manual_odds_loader.load_manual_odds_by_bookmaker`
    (groups by bookmaker first) and
    `probability.market_pipeline.compute_market_consensus` (performs
    per-bookmaker margin removal, then cross-bookmaker aggregation,
    rejecting any bookmaker that quoted an incomplete outcome set
    rather than silently using partial data).
  - Verified against hand-calculated examples in
    `tests/unit/test_market_pipeline.py` (7 tests) and an end-to-end
    integration test showing the corrected script no longer
    recommends a live bet on a case where the old buggy version
    would have (`tests/integration/test_corrected_daily_shortlist.py`).
- Fixed `storage.csv_store.read_records` to correctly round-trip empty
  optional numeric fields (previously failed to parse blank CSV cells
  for `Optional[float]` fields).
- Fixed a pydantic v2 deprecation warning in `storage.schemas.BankrollTransaction`.

### Added — Stage 2 manual workflow

- `utils.dates`, `utils.money`, `utils.validation` — timestamp/staleness
  helpers, GBP rounding, shared validators.
- `storage.schemas` — pydantic schemas for every Sheets tab (Markets,
  Bookmaker Odds, Bets, Paper Trades, Results, Bankroll).
- `storage.csv_store` — CSV read/append/overwrite for those schemas.
- `ingestion.manual_odds_loader`, `ingestion.exchange_price_loader`,
  `ingestion.schema_validation` — manual entry parsing and validation.
- `reports.daily_report` + `reports.markdown_renderer` — generates the
  Stage 1 daily report format from real opportunity data.
- `scripts/generate_daily_shortlist.py`, `scripts/import_manual_odds.py`,
  `scripts/settle_results.py` — Stage 2 CLI entry points.
- Google Sheets workbook (`Prediction Markets Lab.xlsx`): 10 operational
  tabs (Settings, Markets, Bookmaker Odds, Daily Shortlist, Bets, Paper
  Trades, Results, Bankroll, Performance, Weekly Reviews), generated,
  recalculated with zero formula errors, and uploaded to Google Drive.

### Added — Research Engine

- `docs/RESEARCH_ENGINE.md` — full design: purpose, OBSERVE→...→RETIRE
  lifecycle, hypothesis/behaviour distinction, in-sample/out-of-sample
  separation, multiple-testing handling, promotion/rejection rules.
- `research/hypotheses/hypothesis_registry.csv` + `src/.../research/schemas.py`
  (`Hypothesis`) + `research/registry.py` — typed, validated hypothesis
  registry with enforced status-transition graph
  (`research/hypothesis_validation.py`). Seeded with **11 unvalidated
  research hypotheses** (6 football, 5 tennis) — see CYCLE_001 for
  which four are selected for the first research cycle.
- `research/behaviours/behaviour_atlas.csv` + `Behaviour` schema +
  `research/behaviour_atlas.py` — intentionally empty; no hypothesis
  has yet earned evidence to graduate into a tracked behaviour.
- `research/evidence_grading.py` + `config/research_thresholds.yaml` —
  configurable A/B/C/INSUFFICIENT evidence grading, including an
  extra-scrutiny flag for large multiple-testing families.
- `research/research_prioritisation.py` — multi-factor priority
  scoring (P1/P2/P3/DEFER/DO_NOT_RETEST), explicitly not ranked by
  historical ROI alone.
- `reports/research_report.py` + 4 templates (weekly/monthly research
  report, hypothesis review, behaviour atlas report) — keeps realised
  profit and estimated EV visually and structurally separate; a
  profitable period never auto-promotes a hypothesis.
- `research/RESEARCH_SAFEGUARDS.md` + `research/rejected_ideas/`,
  `research/near_misses/`, `research/do_not_retest/` — guards against
  silently re-testing rejected ideas and against multiple-testing
  curve-fitting.
- `config/research_metrics_buckets.yaml` — categorical analysis
  buckets (odds bands, favourite/underdog, bookmaker count/dispersion
  bands, time-before-event bands) for future breakdowns.
- `docs/ARCHITECTURE_FREEZE_V1.md` — change-control policy: new
  infrastructure modules require a named research task, a reason
  existing components don't suffice, a test proving necessity, a
  stated maintenance cost, and confirmation it's needed before the
  next research decision.

### Test suite

- 79 (Stage 1) → **179 tests passing**, 0 failures, 0 warnings.

## [0.1.0] — Stage 1: Foundation

### Added

- Repository structure per project instructions section 11.
- Core documentation: PROJECT_PLAN, OPERATING_MANUAL, DAILY_WORKFLOW,
  MOBILE_WORKFLOW, DATA_DICTIONARY, PROBABILITY_METHODOLOGY,
  EV_METHODOLOGY, RISK_MANAGEMENT, VALIDATION_PLAN, MODEL_GOVERNANCE,
  MARKET_RULES, ROADMAP.
- Configuration files: bankroll, thresholds, commissions, competitions,
  bookmakers, data_sources, model_weights, logging.
- `probability.odds_conversion` — decimal odds to raw implied
  probability.
- `probability.margin_removal` — proportional margin removal (V1
  default).
- `probability.consensus` — cross-bookmaker median/mean/std/IQR
  consensus.
- `ev.expected_value` (+ `ev.commission`, `ev.edge`, `ev.break_even`) —
  commission-adjusted EV, gross EV, expected ROI, break-even
  probability, probability edge, relative edge.
- `risk.bankroll` — bankroll state and drawdown tracking.
- `risk.staking` — grade-based fixed stake recommendation.
- `risk.exposure` — daily exposure and open-bet-count limits.
- `risk.loss_locks` — daily/weekly loss-stop checks.
- `risk.decision_gates` — combined pre-trade risk gate.
- `decisions.grading` — A+/A/B/C/Reject grading engine.
- Documented placeholder modules for all Stage 2+ components
  (ingestion, normalisation, models, performance, reports, storage,
  utils, confidence/data_quality/liquidity/recommendation scoring).
- Unit tests for every Stage 1 calculation module.
- Sample football and tennis fixtures.

### Known limitations

See README.md "Known limitations" section.

