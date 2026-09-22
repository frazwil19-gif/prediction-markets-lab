# Phase 2 Leakage Audit (Section 8)

**Written 2026-09-22.** Extends, rather than repeats, Gate 1's own leakage audit
(`GATE1_PROBABILITY_ARCHITECTURE_PROTOCOL.md` and `GATE1_CHECKPOINT.md` points 4 and 29), which
already covers every feature this phase uses.

## Features reused from Gate 1 -- leakage safety already established and re-confirmed here

Every fundamentals feature (Elo pre-match rating, Poisson pre-match lambda, rolling last-10
goals/shots/SOT/corners/cards differentials, points-per-game differential) is computed by a
**continuous chronological replay** that processes matches strictly in `(match_date, match_id)` order
and snapshots each team's state immediately BEFORE pushing that match's own result into the rolling
window (`features/football_leakage_safe_features.py`, `models/football_elo.py`,
`models/football_poisson.py` -- all mechanically tested for this exact property in their own test
files). This phase did not re-derive these features from raw data; it reused the already-computed,
already-tested `cycle_002_discovery_features.csv` and the same replay functions Gate 1 called
directly. No new feature-engineering code was written, so no new feature-level leakage risk was
introduced.

## New code added in this phase -- leakage risk assessment

1. **`scripts/run_gate1_1x2_probability_architecture_comparison.py`'s additive CSV-dump extension**
   (gated behind an unset-by-default environment variable) only writes out predictions the script
   already computes in its existing, unmodified fold loop -- it does not change what data any model
   sees, when it sees it, or how folds are constructed. It was verified byte-for-byte reproducible:
   rerunning the extended script reproduces Gate 1's exact published pooled log-loss and Brier figures
   for every model (0.98726 / 1.01085 / 1.01572 / 0.99225 / 0.98981), confirming the extension changed
   no modelling behaviour.

2. **`research/probability_model_v2_diagnostics.py`'s bucketing functions** (`high_probability_region_
   report`, `disagreement_band_report`) take already-computed, already-out-of-sample predictions as
   plain floats/booleans. They perform no data loading, no model fitting, and no access to
   `full_time_result` beyond the `actual_outcomes` argument the caller already derived from an
   out-of-sample row. There is no mechanism by which these functions could see a match's own outcome
   before the prediction they are diagnosing was made -- the ordering guarantee lives entirely in the
   upstream Gate 1 fold loop, which was not modified.

## Residual risk, stated rather than hidden

The disagreement-band and high-probability-region analyses are computed on the SAME pooled 5,631
out-of-sample predictions Gate 1 already used for its headline comparison -- they are a different
SLICE of the same evidence, not independent new evidence. This is appropriate for "how is this result
distributed" questions (Sections 13, 15) but means these diagnostics cannot be treated as an
independent replication of Gate 1's core finding -- they are a closer look at the same result, and are
presented as such throughout `PHASE2_RETURN_CHECKPOINT.md`.

## Conclusion

No new leakage risk was found or introduced. The one genuine, previously-stated leakage-adjacent
limitation carried forward from Gate 1 unchanged: none of 2020/21-2025/26 is a pristine holdout for
this question (see `EXPERIMENT_PLAN.md`'s chronological-design section) -- this is a validation-design
limitation, not a leakage defect, and is why no new claim in this phase is described as "OOS-validated
on a sealed holdout."
