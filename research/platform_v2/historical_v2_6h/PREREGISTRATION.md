# V2-6H — Historical Bet-Selection Backtest: Pre-registration (2026-09-29, before any betting result was computed)

**Scope.** This is a retrospective research simulation. It is **not** paper betting: nothing is written to `paper_betting_v2/`,
and nothing here counts toward the live gate. The frozen engines, sealed holdouts, thresholds, ledgers and workflows are
unchanged. Rules are V2-6 `bsv2-1` exactly as committed in `config/bet_selection_v2.yaml`. There is no threshold search.

## Data (read-only snapshots from Fraser's local repo, hash-versioned where the repo has hashes)
- **Football 1X2:** `cycle_001_*_full.csv` (data_version `cycle_001_v1.0.0-20260910T234139`): E0/E1/SC0, 2020/21–2024/25, 5,800
  matches, per-book 1X2 odds at two football-data.co.uk snapshots. `opening` is football-data's *pre-closing* collection
  (documented as Friday afternoon for weekend fixtures, Tuesday for midweek). `closing` is taken at kick-off. The 2025/26
  season comes from `h_fb2_002_sealed_oos_2025_26_*` (already opened once in H-FB2-002; used here only as a later period).
- **Tennis ATP/WTA:** `data/interim/v2_tennis_market_dataset.csv` (12,202) and `v2_wta_market_dataset.csv` (10,352). Betfair
  last-traded prices (LTP) only.
- **NBA:** wippa OddsPortal *average* closing moneyline, one price per side.

## Probability (frozen engine definitions, no refitting)
- Football: the median across books of per-book proportional (multiplicative) de-vig at the **same snapshot**; ≥ 3 books
  (`data_quality.min_bookmakers`).
- Tennis: the multiplicative de-vig of the LTP pair (the frozen historical estimator). NBA: the proportional de-vig of the
  average odds.

## Executable price rule
Only an individual, named book's quote at the same snapshot counts. Aggregates (Max, Avg) are never executable.
- **Primary UK-executable set:** Bet365 (B365), William Hill (WH), Bet&Win/bwin (BW), and Betfair exchange (BF, 5% commission).
- Pinnacle (PS) and 1xBet (1XB) are excluded from the primary set because UK retail availability can't be verified. They
  are reported as a **sensitivity only**.
- Best price = the highest net-EV book at that snapshot. This is an as-of-time choice among quotes that coexisted at the
  collection time, not a hindsight maximum across times.

## Decision rule (bsv2-1, unchanged)
PAPER_BET-equivalent = P ≥ 0.50, net EV ≥ 2%, odds ≥ 1.33, and a VALIDATED engine.
- **Primary analysis A (closing snapshot):** the decision is treated as taken just before kick-off, so the ≤ 24 h horizon holds
  and the price is fresh. **Limitation, stated before results:** closing quotes are recorded at kick-off, so they are the most
  optimistic executable timing.
- **Secondary analysis B (opening/pre-closing snapshot):** the exact collection timestamp is unknown, so the 24 h horizon gate
  is **not evaluable** and is reported as such (not treated as passed). Results are descriptive only. CLV is measured as
  selection odds against the closing consensus fair odds of the same match.

## Reporting (all pre-committed)
- Per season, league, P band, odds band and book: candidates, qualifying rate, selections/day, mean estimated net EV,
  realised ROI, and a match-level bootstrap 95% CI (2,000 resamples, seed 20260929).
- Max drawdown and longest losing streak (units), plus existing `bankroll.simulate_all` paths.
- **Descriptive sensitivities** (never used to pick a rule): leave-one-out consensus (the priced book excluded from P); EV
  floors of 0% and 5%; the primary set plus PS/1XB.
- Tennis and NBA: the self-source EV structure is quantified. A betting backtest is declared infeasible where no independent,
  named, as-of executable price exists.
- Chronology: the 2020/21–2023/24 development-era seasons are reported separately from 2024/25 (Cycle-1 sealed holdout, already
  opened) and 2025/26 (H-FB2-002 OOS, already opened). A consistent sign across all periods is required before any statement of
  historical support.

Code: `scripts/v2_6h_historical_backtest.py`. Outputs: `research/platform_v2/historical_v2_6h/`.
