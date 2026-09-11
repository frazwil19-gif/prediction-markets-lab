# Changelog

All notable changes to this project are documented here. Format is
loosely based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — Stage 3A frozen, Stage 3B Checkpoints 1-5 complete

### Added (Checkpoint 5 — STAGE 3B PRE-HOLDOUT FREEZE)

- `research/cycles/CYCLE_001/results/FINAL_HOLDOUT_PROTOCOL.md` --
  pre-registration for Checkpoint 6: frozen code commit and data version,
  predeclared holdout coverage (1,160 matches, all 3 competitions, full
  coverage = common sample uniquely for this season), the exact procedure
  (fit on all 4 development seasons as one final fold, evaluate once),
  the exhaustive 8-candidate predeclared list, and a mechanical verdict
  rubric (STRONG SIGNAL / WEAK-UNCERTAIN SIGNAL / MARKET DOMINATES-NULL
  RESULT / INVALID) fixed before any result can be seen.
- `reports/audits/STAGE_3B_PRE_HOLDOUT_FREEZE.json` +
  `scripts/verify_pre_holdout_freeze.py` -- hash-seals the protocol
  document itself (mirroring `verify_frozen_data_hashes.py`'s pattern for
  the raw data), so Checkpoint 6 can mechanically refuse to proceed if the
  protocol changed after pre-registration.
- Checkpoint 6 (opening the sealed 2024/25 holdout) has NOT been run and
  requires explicit go-ahead -- this commit only locks the procedure in
  place, it does not open the holdout.

### Added (Checkpoints 2-4)

- `models.football_elo` -- Stage 3B Model 1: standard 2-outcome Elo rating
  update plus a closed-form 3-way (draw_margin) prediction transform,
  calibrated per-fold on training data only. Global ratings across
  competitions (promotion/relegation continuity), fixed season-transition
  mean reversion.
- `models.football_poisson` -- Stage 3B Model 2: independent-Poisson
  attack/defence model (Maher 1982-style), tracked per competition,
  shrinkage-regularised team ratios, truncated/renormalised scoreline grid.
- `models.football_blended` -- Stage 3B Model 3: convex-combination
  probability blending with an exhaustive predeclared weight grid search
  (never an open-ended optimiser), calibrated on training data only.
- `probability.uncertainty.paired_bootstrap_delta` -- paired bootstrap
  confidence intervals (match-level and block-by-date resampling, both
  always reported) for any model-vs-market metric delta.
- `performance.calibration` -- raw (no recalibration fit) reliability
  diagnostics: equal-count-bin calibration reports and Expected Calibration
  Error, per outcome, per model.
- `scripts/run_stage_3b_checkpoint2_elo.py`, `..._checkpoint3_poisson.py`,
  `..._checkpoint4_blends_and_uncertainty.py` -- orchestration for each
  checkpoint, all verifying the frozen-data hash record before reading
  anything.
- `research/cycles/CYCLE_001/results/{ELO_MODEL_REPORT,POISSON_MODEL_REPORT,BLEND_REPORT,CALIBRATION_REPORT,MODEL_COMPARISON}.md`.

### Fixed (Checkpoints 2-4)

- Poisson `league_averages()` divided by zero when a competition's computed
  average was exactly 0.0 (a degenerate small sample) -- now falls back to
  configured defaults.
- Poisson's default scoreline truncation (`max_goals=10`) lost up to 0.1%
  of probability mass for realistic lambdas -- raised to 15, verified
  >0.99998 for the measured worst case rather than assumed.
- `probability.uncertainty.paired_bootstrap_delta` originally recomputed
  `multiclass_log_loss`/`multiclass_brier_score` (which revalidate every
  probability dict) from scratch on every one of `n_resamples` iterations --
  correct but impractically slow on the real ~3,446-match pooled sample
  (discovered when Checkpoint 4's first real run did not finish inside a
  180-second budget). Rewritten to compute each match's per-observation
  loss once, then resample over the resulting float arrays -- algebraically
  identical (log loss/Brier are simple per-match means), ~7x faster in
  practice (26s vs. non-terminating), no change to any test's expected
  values.
- Removed dead/duplicate `train_common_ids` computation in
  `run_stage_3b_checkpoint4_blends_and_uncertainty.py` (the first
  computation was immediately overwritten by a second, correct one).

### Findings (Checkpoints 2-4)

- Elo (pooled, N=3,446): log loss 1.0233, Brier 0.6133 -- clears the naive
  floor, does not close the gap to market.
- Poisson (pooled, N=3,446): log loss 1.0097, Brier 0.6037 -- clears both
  the naive floor and Elo.
- `elo_poisson` blend (pooled, N=3,446): log loss 1.0035, Brier 0.5995 --
  beats both individual fundamentals models, and is the best-calibrated
  model-based candidate on every outcome (see CALIBRATION_REPORT.md),
  substantially correcting a specific away-outcome miscalibration bias in
  Elo (ECE 0.0605 -> 0.0128).
- Every market-inclusive blend (`market_elo`, `market_poisson`,
  `market_elo_poisson`) calibrates to 100% market weight in every one of
  the 3 development folds -- no positive weight on Elo or Poisson ever
  reduces in-sample log loss once market is available as a component.
- Paired bootstrap (match-level and block-by-date, 95% CI, n=2000,
  seed=42): the market's advantage over Elo, Poisson, and `elo_poisson` is
  statistically confirmed -- every CI lies entirely above zero for both
  metrics and both resampling methods, which agree closely throughout.
- No model or blend has beaten the market on the development folds. See
  `MODEL_COMPARISON.md` for the full consolidated ranking; this is
  provisional pending the sealed 2024/25 holdout (Checkpoints 5-6, not yet
  started).

## Stage 3A frozen, Stage 3B Checkpoint 1

### Fixed

- Cycle 1 acquisition script wrote real downloaded raw CSVs to a path the
  GitHub Actions workflow's raw-files artifact upload never globbed
  (missing a `raw` path segment) -- every prior run's `cycle_001-raw-files`
  artifact silently contained only stale excerpt-validation stubs, never a
  genuine download. Fixed, with a regression test tying the two together.
- `.gitignore` never allowlisted `reports/audits/*.json`, so the new Stage
  3A freeze record was silently excluded on first commit. Fixed.

### Added

- `reports/audits/CYCLE_001_FREEZE_RECORD.json` -- git-committed provenance
  anchor for the frozen Cycle 1 dataset (`cycle_001_v1.0.0-20260910T234139`):
  SHA-256 hashes for all 15 raw source files, all 3 processed tables, and
  the alias config, plus code commit, validator result, and known
  limitations.
- `scripts/verify_frozen_data_hashes.py` -- verifies a local working copy
  against a freeze record before any modelling script reads it.
- `performance.log_loss`, `performance.brier` -- multiclass log loss and
  (vector) Brier score, both with full input validation.
- `validation.time_splits.generate_expanding_walk_forward_folds` --
  expanding-window walk-forward fold generator (season-label based).
- `models.football_naive_frequency` -- Stage 3B Baseline 0: leakage-safe,
  per-competition, Laplace-smoothed expanding H/D/A frequency baseline.
- `scripts/run_stage_3b_checkpoint1_baselines.py` -- computes Baseline 0
  and Baseline 1 (market closing consensus) across the 3 development
  walk-forward folds; generates
  `research/cycles/CYCLE_001/results/NAIVE_BASELINE_REPORT.md` and
  `MARKET_BASELINE_REPORT.md` from machine-readable output, never
  hand-transcribed.
- `research/cycles/CYCLE_001/STAGE_3B_PLAN.md` -- predeclared Stage 3B
  protocol: research question, dataset/fold definitions, baseline order,
  price-timing classification, common-sample rule, metric/delta
  convention.
- Python 3.11 / `uv` environment setup documented in `CONTRIBUTING.md`.

### Changed

- `research/cycles/CYCLE_001/DATA_SPLIT_PLAN.md` superseded by the
  walk-forward fold design in `STAGE_3B_PLAN.md` (2024/25 remains the
  sealed final holdout; the single fixed train/validation split originally
  proposed there is replaced by 3 expanding-window development folds).

### Findings

- Naive frequency baseline (pooled, N=3,480): log loss 1.0692, Brier 0.6470
  -- only marginally better than a uniform 1/3-1/3-1/3 prediction
  (ln(3)≈1.0986 / 2/3≈0.6667).
- Market closing consensus (pooled common sample, N=3,446): log loss
  0.9773, Brier 0.5815 -- beats the naive baseline on every one of the 3
  development folds individually and pooled. No significance testing yet
  (paired bootstrap CIs are a later Stage 3B checkpoint).

## [0.4.0] — Stage 3A: pipeline validated, full acquisition pending

**Status: STAGE 3A TOOLING COMPLETE — FULL ACQUISITION PENDING.**

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

