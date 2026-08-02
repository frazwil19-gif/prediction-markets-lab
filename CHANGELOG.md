# Changelog

All notable changes to this project are documented here. Format is
loosely based on [Keep a Changelog](https://keepachangelog.com/).

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
