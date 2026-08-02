# Roadmap

## Stage 1 — Foundation ✅ (this release)

- Repository structure, README, documentation
- Configuration files
- Odds conversion, proportional margin removal, consensus engine
- Commission-adjusted EV, edge, break-even
- Bankroll, staking, exposure, loss-lock, combined risk-gate logic
- A+/A/B/C/Reject grading
- Unit tests for every calculation
- Sample football and tennis fixtures

## Stage 2 — Manual workflow (not started)

- Manual odds CSV template + loader
- Exchange price CSV template + loader
- Daily report generator (`reports/daily_report.py`)
- Google Sheets workbook creation (Settings, Markets, Bookmaker Odds,
  Daily Shortlist, Bets, Paper Trades, Results, Bankroll, Performance,
  Weekly Reviews tabs)
- Daily shortlist process
- Trade logging process
- Result settlement process

## Stage 3 — Football baseline (not started)

- Football-Data.co.uk loader
- Team-name normalisation
- Elo model
- Basic Poisson model
- Blended model
- Historical backtest
- Calibration report

## Stage 4 — Tennis baseline (not started)

- Tennis data schema
- Player-name normalisation
- Elo model
- Surface Elo model
- Match-winner probability output
- Validation report

## Stage 5 — Reporting (not started)

- Daily/weekly/monthly reports
- Performance attribution
- Bankroll and drawdown reports
- ROI, CLV, Brier score, log loss, calibration

## Stage 6 — Optional free automation (not started, optional)

Only after manual operation works:

- Limited free API ingestion (e.g. The Odds API free allowance)
- GitHub Action tests
- Optional scheduled report generation
- Optional Google Sheets synchronisation

Automation is never the starting point, and remains optional even in
Stage 6 — the manual mobile workflow must remain fully functional
without it.

## Open questions to resolve before Stage 2

1. Which specific bookmakers will be checked for consensus (populate
   `config/bookmakers.yaml`)?
2. Confirm current Smarkets and Betfair commission rates on the user's
   actual account (`config/commissions.yaml` currently holds commonly
   cited standard rates as a placeholder).
3. Does the user want the Google Sheets workbook created via a
   connected Google Sheets/Drive integration, or described for manual
   setup?
4. What exact Grade C net-EV floor is wanted, if not the conservative
   0.00 default currently assumed in `config/thresholds.yaml`?
