# Football Double Chance — sealed-holdout no-peek design (V2-13)

**Holdout.** `research/platform_v2/double_chance/HOLDOUT_SPEC.json` (sha256 verified, unchanged):
- E0/E1/SC0, matches dated 2026-08-01 to 2026-12-31;
- estimator: closing B365/BW/PS, multiplicative de-vig, mean, DC = pairwise sums;
- `open_not_before` 2027-01-03; open once.

**Conflict.** Prospective DC collection (approved 2026-10-01, shadow only) runs from about 8 Oct 2026 on **the same matches**. Live DC rows will be settled from the same football-data.co.uk results while the holdout is still sealed. Reporting their calibration would let the analyst see DC calibration on holdout matches before the holdout is opened.

## Controls

1. **Automatic masking** (`config/holdout_guards.yaml`, `prediction_platform/performance.py::HoldoutGuard`).
   - While `research/platform_v2/double_chance/HOLDOUT_RESULTS.json` does not exist, every settled row of `football_double_chance.derived_1x2` with an event date inside the window is excluded from every unified performance output: pooled, by-dimension, the ≥80 decomposition, engine maturity and alarm, and timing buckets.
   - Excluded rows are only counted (`holdout_masked`, `settled_rows_masked_no_peek`). The Prediction Board's "prospective evidence" section is built from the same report, so it is masked too.
   - Tested in `tests/unit/test_v2_13_football.py`.
2. **Raw data untouched.** `predictions/unified_settlements.csv` still records the settlements (append-only).
   - **Process rule:** no one computes DC performance on window dates from raw files before the holdout is opened.
   - Any exception requires your written approval and is logged as a holdout contamination event.
3. **Guarded one-shot opener** (`scripts/open_dc_holdout.py`). It refuses unless:
   - today ≥ `open_not_before`;
   - the spec matches its frozen hash;
   - no results file exists;
   - the three raw 2026/27 CSVs are supplied, with their SHA-256 recorded.

   It applies exactly the spec's estimator and pass criteria using the frozen V2-4 functions. It writes `HOLDOUT_RESULTS.json`, which also flips the masking guard to OPENED. **It has not been run.**

## Residual leakage — DECIDED 2026-10-01: Option L1 (1X2 reporting stays ON)

**Decision.** Football 1X2 prospective reporting stays ON. It is a separate experiment testing a different (live) estimator.

**What stays masked or forbidden until the guarded opener runs (on or after 2027-01-03):**
- every aggregate or performance analysis of DC on window dates;
- DC calibration, Brier score, log loss, win rates, band tables, and any other outcome-derived DC statistic;
- any DC tuning from Aug–Dec 2026 outcomes.

**What does not open the holdout.** Ordinary knowledge of match results, or of 1X2 prospective results, does **not** constitute an authorised quantitative opening of the DC holdout. Opening means running `scripts/open_dc_holdout.py`, and nothing else counts.

**Disclosure.** The eventual holdout report must state that live-estimator 1X2 calibration on overlapping matches was visible before opening.

(Option L2, masking 1X2 as well, was considered and rejected.)
