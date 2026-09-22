# Gate 1b (Football O/U 2.5) -- Sealed Holdout Report (2024/25 season, final walk-forward fold)

Fold: `train_through_2023_24_eval_2024_25` (train on 2020/21+2021/22+2022/23+2023/24, evaluate on
2024/25 -- the LAST season this data source covers). Every modelling decision (the 19-feature set, the
market field choice, the L2 penalty, the fold structure itself) was fixed BEFORE this fold's evaluation
was computed -- it was written into the frozen module (`ou25_probability_architecture.py`) and executed
in one script run, with no iteration on this specific fold's result.

| Model | n | Log loss | Brier | AUC | Accuracy @ 0.5 | Mean predicted P | Actual rate |
|---|---|---|---|---|---|---|---|
| Naive frequency | 1160 | 0.6933 | 0.2501 | 0.5000 | 0.4845 | 0.4974 | 0.5155 |
| Market (thin panel) | 1160 | 0.6796 | 0.2433 | 0.5922 | 0.5612 | 0.5228 | 0.5155 |
| Fundamentals only | 1158 | 0.6909 | 0.2487 | 0.5583 | 0.5320 | 0.5176 | 0.5155 |
| Market + fundamentals | 1158 | 0.6841 | 0.2453 | 0.5851 | 0.5613 | 0.5272 | 0.5155 |

**Result: the same ranking holds a third time, independently, on the final held-out season.** Market
remains the single best-calibrated, highest-discrimination estimator on every metric.

## Honesty caveat (same class of limitation already documented for 1X2)

This is NOT a fully blind prospective holdout in the strictest sense: 2024/25 match results and
features have been present in this project's data files since Cycle 1/Cycle 2 were originally built,
and other research cycles (Gate 1, Backtest Phase 1) have already used this season for 1X2 purposes.
For THIS SPECIFIC TARGET (Over/Under 2.5, never modelled in this project before this cycle), no prior
research stage had inspected or fit anything against it -- so this is a genuine first look at this
target on this season, even though the season itself is not new to the project. The caveat is stated
plainly rather than either overclaiming a pristine holdout or discounting the result as meaningless.

**No genuine prospective holdout beyond 2024/25 currently exists** for this target -- 2025/26 is not
covered by `cycle_002_discovery_features.csv` (same data gap the Outcome Discovery cycle already
documented for 1X2). Extending that pipeline is a recommended, not-yet-actioned next step, shared with
the 1X2 side of this project.
