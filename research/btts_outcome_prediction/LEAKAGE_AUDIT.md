# Phase 5 — BTTS Leakage Audit

| input | available before kickoff? | control |
|---|---|---|
| 19 Gate-1b fundamentals (rolling last-10 goals/shots/SOT/corners/PPG, Elo gap) | yes | built by Cycle 2's audited shifted pipeline; reused unchanged |
| 10 new rolling scoring / clean-sheet / BTTS-rate features | yes | `build_rolling_btts_features`: matches grouped by **date**; every feature for date D is computed before ANY result from D is added, so neither a match's own result nor a concurrent same-day fixture can leak in. League priors use strictly earlier matches only |
| Poisson λ (goal model) | yes | the project's existing `simulate_pre_match_lambdas` (predict-then-update, chronological-order assertion) |
| Market-implied λ | yes | closing / opening de-vigged prices, a pre-kickoff snapshot; zero parameters fitted to outcomes |
| Fitted models | — | `predict_model` raises if any training date is on or after the first evaluation date; walk-forward trains only on strictly earlier seasons |
| Holdout | — | development stage drops 2024/25 before any computation; holdout stage requires a frozen, hash-matched protocol and refuses a second opening (verified: second run printed `REFUSED`) |

Tests (in `tests/unit/test_btts_outcome_prediction.py`): own-result invariance, same-day-fixture invariance,
future-truncation invariance, bounded window, train-after-eval rejection, holdout-outcome-flip invariance of all
development predictions, determinism.

Residual, declared: closing prices are the last pre-kickoff snapshot, while a live scan sees earlier prices. The
opening-price sensitivity model brackets this (dev log loss 0.6875 vs 0.6867 closing; holdout 0.6853 vs 0.6857), so
the deployable estimator's quality does not depend on having closing prices.
