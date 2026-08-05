# Cycle 1 — Research Plan

**STATUS: STAGE 3A PIPELINE VALIDATED — FULL DATASET ACQUISITION PENDING**

## Purpose

Determine whether a conservative bookmaker-consensus baseline plus
simple football strength models can improve probability calibration
or identify repeatable pricing deviations in pre-match 1X2 markets,
across English Premier League, English Championship, and Scottish
Premiership.

Cycle 1 does **not** attempt to maximise historical ROI. It answers,
for each selected hypothesis, whether it deserves continued testing,
paper trading, rejection, or deferral (see
`research/cycles/CYCLE_001/HYPOTHESIS_SELECTION.csv`).

## Scope

- **Market:** Football pre-match 1X2 only.
- **Competitions:** Premier League (E0), Championship (E1). Scottish
  Premiership (SC0) — feasibility **confirmed** (full 2024/25 season
  fetched and verified, identical schema to E0/E1) but not yet
  acquired at full 5-season scale.
- **Seasons (target):** 2020/21 through 2024/25 (5 seasons).
- **Hypotheses selected:** see `HYPOTHESIS_SELECTION.csv` and
  `DATA_FEASIBILITY_DECISIONS.md` — of the four originally proposed,
  two are testable as defined (bookmaker disagreement, short-rest/
  congestion), one needs a pre-registered popularity proxy, and one
  (exchange-price value) is confirmed not testable from this data
  source and excluded from Cycle 1.

## Current status (accurate as of this document's last update)

- ✅ SC0 feasibility passed (full season verified live).
- ✅ Pipeline (loader → bookmaker extraction → normalisation →
  consensus → canonical schemas) validated end-to-end against 29 real
  matches (`data/samples/excerpt_validation/`,
  `reports/audits/excerpt_validation/`).
- ❌ Full historical acquisition (15 files: E0/E1/SC0 × 5 seasons)
  **remains outstanding.**
- ❌ Dataset version **is not frozen** — the only `data_version` that
  exists is `cycle_001_v0.1.0-partial`, explicitly marked as excerpt/
  pipeline-validation scale, not a Cycle 1 dataset release.
- ❌ Chronological split (`DATA_SPLIT_PLAN.md`, `data_splits.csv`) is
  **provisional** — season boundaries are a design proposal, not
  confirmed against real full-season row counts.
- ❌ **No model has trained or may train on the excerpt.** The 29-match
  sample exists solely to prove the pipeline mechanics are correct.
- ❌ **No hypothesis has been tested.** All entries in the Hypothesis
  Registry remain at `IDEA` or `DATA_REQUIRED`.
- ❌ **Behaviour Atlas remains empty** — correctly so; no hypothesis
  has earned evidence.

## Path to full acquisition

Because this project is intended to run without requiring a laptop or
continuous developer environment, the actual full-scale download (15
paced HTTP requests, ~6 seconds apart, several minutes total) is
designed to run via a manually-triggered GitHub Actions workflow
(`.github/workflows/cycle_001_data_acquisition.yml`) rather than
requiring the user to run scripts locally. See
`docs/PHONE_ONLY_DATA_ACQUISITION.md` for the exact phone-only steps,
and `scripts/run_cycle_001_data_acquisition.py` for the orchestration
logic the workflow calls.

## Definition of done for Cycle 1 (not yet reached)

1. All 15 target files acquired or explicitly excluded with reasons.
2. Complete raw-file manifest with real hashes.
3. Full cross-season schema inventory.
4. Complete bookmaker coverage and duplicate review at full scale.
5. Canonical processed datasets (Parquet) covering all acquired data.
6. Frozen `data_version` (immutable once referenced).
7. Finalised chronological split plan with real row counts.
8. Final hypothesis feasibility decisions confirmed at full scale.
9. Bundle validation result `VALID` or `VALID_WITH_NONCRITICAL_WARNINGS`
   (`scripts/validate_cycle_001_data_bundle.py`).

Only after all of the above is Cycle 1 ready for Stage 3B (Elo/Poisson
baseline models) — which has not begun and is out of scope for this
document.
