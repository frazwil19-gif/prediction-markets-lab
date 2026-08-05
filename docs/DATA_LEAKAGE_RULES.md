# Data Leakage Rules

Enforced by `src/prediction_markets_lab/validation/time_splits.py` and
`leakage_checks.py`. Any future model (Elo, Poisson, or otherwise)
must be built on top of these helpers, not re-implement its own
chronology logic.

## Prohibited practices

1. **Using closing odds to predict outcomes if the simulated decision
   time is earlier.** A backtest simulating a decision at T-24h must
   only use data available at T-24h — never the closing price, which
   is only known at kickoff.
2. **Using future matches in rolling ratings.** An Elo/form rating for
   team X ahead of match M must only incorporate X's matches strictly
   before M's date. Enforced by
   `leakage_checks.check_rolling_window_uses_only_past_data`.
3. **Random train/test splitting across time.** Splits must be
   contiguous date ranges assigned in advance
   (`validation.time_splits.SplitPlan`), never a random shuffle, since
   a random split would let the model implicitly learn from future
   matches via shared team-form signals.
4. **Fitting preprocessing transformations on the full dataset.** Any
   normalisation, scaling, or parameter fitting (e.g. Elo K-factor
   selection) must use only the training split; applying it to the
   full dataset first (including validation/test) leaks distributional
   information about future data into decisions made "as if" only
   training data were known.
5. **Using post-match statistics as pre-match features.** Columns like
   shots, corners, and cards (HS/AS/HST/AST/HC/AC/HY/AY/HR/AR in the
   Football-Data schema) are POST-match outcomes and must never be
   used as predictive features for that same match's result — they
   are useful only as inputs to rolling, past-only form features for
   *future* matches.
6. **Using final-season standings for earlier matches.** A team's
   final league position for a season is not known mid-season; any
   "current form"/"table position" feature must be computed as of the
   match date, not backfilled from the season's final table.
7. **Tuning thresholds on the final test period.** Grading thresholds,
   evidence-grading cutoffs, or model hyperparameters must be
   selected using training/validation data only. Once the test period
   is used for anything other than final, one-time evaluation, it is
   no longer a valid test.
8. **Creating hypotheses from the out-of-sample results and then
   treating them as pre-specified.** A hypothesis's `in_sample_period`
   and `out_of_sample_period` (Hypothesis Registry) are fixed at
   `DEFINED` status and must not be edited afterward to better fit
   whatever result was observed.

## Enforcement mechanisms

- `validation.time_splits.SplitPlan` refuses to construct a plan with
  overlapping or out-of-order ranges.
- `validation.time_splits.validate_test_period_untouched` must return
  `True` before any test-period result may be generated or reported.
- `validation.leakage_checks.check_chronological_order` verifies a
  processing sequence (e.g. Elo updates) never processes a later-dated
  match before an earlier one.
- `validation.leakage_checks.check_rolling_window_uses_only_past_data`
  verifies every input to a rolling feature predates the match being
  predicted.
- `validation.leakage_checks.check_no_test_period_in_development`
  verifies no development-phase date falls on or after the frozen test
  period's start date.

These are unit-tested against both synthetic and boundary cases in
`tests/unit/test_time_splits_and_leakage.py`.
