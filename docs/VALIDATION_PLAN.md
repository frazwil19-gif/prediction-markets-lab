# Validation Plan

**Status: planned. No historical or paper-trading validation has been
run yet — Stage 1 delivers unit-tested calculation logic only, not
validated predictive performance.**

## Historical testing (Stage 3+)

- At least three football seasons, where data availability allows.
- Chronological train/test split — no random leakage across time.
- Realistic commission assumptions (see `config/commissions.yaml`).
- Realistic price assumptions (i.e. prices that would actually have
  been available, not closing lines used as if tradable pre-match).
- Comparison against a market-only baseline (i.e. no edge — does the
  model beat just following the consensus?).
- Calibration analysis (Brier score, reliability curves).
- Sensitivity analysis on model weights and thresholds.

## Paper trading (Stage 2+ operational, Stage 5 measured)

Initial targets before live betting is treated as meaningful:

- 200 market predictions recorded.
- At least 50 qualifying paper trades (Grade B or better).
- Positive or neutral closing-line value (CLV).
- Stable calibration across the sample.
- No major data-quality failures.

## Tiny live stage

The user may choose to place tiny live bets earlier than validation
would otherwise justify, purely for engagement/enjoyment. Any such
bets must be clearly labelled **"Experimental live trades — not
validated strategy deployment"** in the Bets tab, and tracked
separately from paper trades in all performance reporting.

## Promotion gating

No model or strategy version should be promoted to `APPROVED_LIVE`
status (see `docs/MODEL_GOVERNANCE.md`) merely because it had a
profitable short period. Promotion requires passing the historical and
paper-trading criteria above.
