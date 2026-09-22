# Gate 1b (Football O/U 2.5) -- Leakage Audit

Reviewed every field this cycle uses against `docs/DATA_LEAKAGE_RULES.md`.

## Target

`outcome_full_time_home_goals` / `outcome_full_time_away_goals` are explicitly `outcome_`-prefixed in
the source file precisely so they are never accidentally used as a model input -- this cycle's code
(`ou25_probability_architecture.build_candidate`) reads them ONLY to construct `target` and
`total_goals`, never passes them into `FUNDAMENTALS_FEATURES`, and no other function in the new module
references them.

## Fundamentals features

All 19 features are last-10-match ROLLING averages computed by Cycle 2's existing leakage-safe feature
pipeline (`features/football_leakage_safe_features.py`, already tested), which by construction excludes
the match being predicted from its own rolling window (a "last 10" window at match N covers matches
N-10..N-1, verified originally when this file was first built for Gate 1's own use). This cycle
introduced no new feature computation -- it only selects a subset of already-verified columns.

## Market probability field

`market_ou25_closing_source_avg_over_probability` is a CLOSING-snapshot price. Per this project's
established convention (`docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`, restated in Backtest Phase 1's
own feasibility audit), football-data.co.uk's closing prices are themselves pre-kickoff information (not
post-match), so using them as a pre-match feature is not a leakage risk in the timestamp sense -- the
same reasoning Cycle 2's own feature-build docstring already states for why opening/closing market
fields need no additional lagging (only match STATISTICS, i.e. goals/shots/etc from the match itself,
require lagging). This is unchanged reasoning, not a new judgment call introduced by this cycle.

## Chronological ordering

The expanding walk-forward fold construction (`generate_expanding_walk_forward_folds`, reused unchanged
from `validation/time_splits.py`) guarantees every fold's training seasons are strictly earlier than its
evaluation season by season-label ordering, identical to Gate 1's own use of this exact function. No
match's target or features from an evaluation season ever appears in that fold's training data.

## Verdict

No leakage identified. No new leakage-audit code was needed beyond reusing the existing, already-tested
season-ordering and rolling-feature-window guarantees this project established for the 1X2 cycles.
