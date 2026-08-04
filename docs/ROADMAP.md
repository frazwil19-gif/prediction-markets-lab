# Roadmap

## Stage 1 — Foundation ✅ COMPLETE

- Repository structure, README, documentation
- Configuration files
- Odds conversion, proportional margin removal, consensus engine
- Commission-adjusted EV, edge, break-even
- Bankroll, staking, exposure, loss-lock, combined risk-gate logic
- A+/A/B/C/Reject grading
- Unit tests for every calculation
- Sample football and tennis fixtures

## Stage 2 — Manual workflow + Research Engine ✅ COMPLETE

- Manual odds CSV template + loader (corrected to per-bookmaker
  grouping so margin removal is calculated correctly — see
  CHANGELOG.md)
- Exchange price CSV template + loader
- Daily report generator (`reports/daily_report.py`)
- Google Sheets workbook created and uploaded to Google Drive
  (10 operational tabs + 5 research tabs, 0 formula errors)
- Daily shortlist process (`scripts/generate_daily_shortlist.py`,
  using the corrected margin-removal pipeline)
- Trade logging process
- Result settlement process (`scripts/settle_results.py`)
- **Research Engine**: Hypothesis Registry, Behaviour Atlas, evidence
  grading, research prioritisation, research reports, safeguards
  against silently re-testing rejected ideas — see
  `docs/RESEARCH_ENGINE.md`
- 11 unvalidated research hypotheses seeded (6 football, 5 tennis) —
  **none tested, none validated**
- `docs/ARCHITECTURE_FREEZE_V1.md` — change-control policy for Stage 3+

## Stage 3 — Historical data, baseline models, first research cycle (ACTIVE, NOT STARTED)

**Immediate next step: a bounded data-feasibility audit** against
Football-Data.co.uk (English Premier League, Championship, Scottish
Premiership) to determine exactly what historical data is genuinely
accessible and consistent, before defining the final Cycle 1 dataset
or writing any model code. See `research/cycles/CYCLE_001/` once
created.

Full Stage 3 scope (only after the feasibility audit confirms
viability):

- Football-Data.co.uk loader with full audit trail (source
  files/timestamps retained, duplicates/incomplete markets rejected
  not silently dropped)
- Team-name and competition-name normalisation
- Chronological time-split helpers + leakage-prevention checks
  (`docs/DATA_LEAKAGE_RULES.md`)
- Baseline 0 (margin-free market consensus — already implemented),
  Baseline 1 (Elo), Baseline 2 (Poisson), Baseline 3 (conservative
  blend) — all with model cards and explicit versioning
- Chronological backtesting framework separating discovery from
  validation periods
- Full evaluation metrics: Brier score, log loss, calibration, CLV,
  betting performance, statistical uncertainty (confidence intervals,
  sensitivity analysis)
- Cycle 1 outputs: CYCLE_REPORT.md, MODEL_COMPARISON.csv,
  HYPOTHESIS_RESULTS.csv, CALIBRATION_SUMMARY.csv, CLV_SUMMARY.csv,
  RISK_SUMMARY.csv, DATA_LIMITATIONS.md, DECISIONS.csv
- Promotion decisions (PROMOTE_TO_PAPER / CONTINUE_RESEARCH /
  NEAR_MISS / REJECT / DEFER) per selected hypothesis — never based on
  ROI alone

**A null result (no hypothesis promoted) is a valid and expected
outcome of Cycle 1.** Live betting does not begin merely because the
code runs or a backtest completes.

## Stage 4 — Tennis baseline (not started)

- Tennis data schema
- Player-name normalisation
- Elo model
- Surface Elo model
- Match-winner probability output
- Validation report

## Stage 5 — Reporting (partially started)

- Daily report generator ✅ (Stage 2)
- Weekly/monthly reports — templates exist (Stage 2 research reports);
  full performance-report generator not yet built
- Performance attribution
- Bankroll and drawdown reports
- ROI, CLV, Brier score, log loss, calibration — schemas and
  placeholders exist; full implementations depend on Stage 3 data

## Stage 6 — Optional free automation (not started, optional)

Only after manual operation works:

- Limited free API ingestion (e.g. The Odds API free allowance)
- GitHub Action tests
- Optional scheduled report generation
- Optional Google Sheets synchronisation

Automation is never the starting point, and remains optional even in
Stage 6 — the manual mobile workflow must remain fully functional
without it.

## Live betting status

**Experimental only, unvalidated.** No hypothesis or model has reached
`VALIDATED` status. No behaviour exists in the Behaviour Atlas yet.
Any live betting under the current grading engine (A+/A/B/C/Reject) is
based only on same-day commission-adjusted EV against a single quoted
price — not on any tested, repeatable edge. This must not be confused
with a validated strategy.

## Open questions

1. Which specific bookmakers will be checked for consensus (populate
   `config/bookmakers.yaml`)?
2. Confirm current Smarkets and Betfair commission rates on the user's
   actual account (`config/commissions.yaml` currently holds commonly
   cited standard rates as a placeholder).
3. What exact Grade C net-EV floor is wanted, if not the conservative
   0.00 default currently assumed in `config/thresholds.yaml`?
4. Football-Data.co.uk feasibility: which seasons/leagues have
   consistent bookmaker-specific and closing-odds coverage? (Answered
   by the Stage 3 feasibility audit, not yet run.)
