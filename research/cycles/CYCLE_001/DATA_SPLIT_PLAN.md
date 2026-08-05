# Cycle 1 Data Split Plan

**Status: design only. No model has been trained or evaluated against
these splits. This plan must be finalised BEFORE any model fitting
begins, and the test period must remain untouched until final
evaluation (see `docs/DATA_LEAKAGE_RULES.md`).**

## Coverage confirmed so far

Only the 2024/25 season has been acquired (at excerpt scale — see
`reports/audits/CYCLE_001_DATA_ACQUISITION_REPORT.md`). The full
5-season target (2020/21–2024/25) has not yet been downloaded, so the
exact season boundaries below are a **provisional design**, to be
confirmed once full acquisition completes and `football_data_quality_by_season.csv`
shows real row counts for every target season.

## Preferred design (pending full acquisition)

| Split | Seasons | Purpose |
|---|---|---|
| Training | 2020/21, 2021/22, 2022/23 | Model fitting (Elo/Poisson parameters), hypothesis backtesting (in-sample) |
| Validation | 2023/24 | Threshold tuning, model selection, out-of-sample hypothesis testing |
| Test | 2024/25 | Final, untouched evaluation only — no fitting, no tuning, no threshold selection may use this period |

Rationale: three training seasons gives Elo/Poisson-style models
enough matches to stabilise (a full Premier League + Championship
season is ~760 matches; three seasons ×2 competitions ≈ 2,280+
matches), one validation season for tuning, and the most recent
complete season held out entirely for the final test — consistent with
`config/research_thresholds.yaml`'s Grade A bar of ≥100 out-of-sample
observations, comfortably exceeded even by Premier League alone.

Scottish Premiership (SC0), once its full multi-season coverage is
confirmed, would follow the same season boundaries.

## Enforcement

- `src/prediction_markets_lab/validation/time_splits.py::SplitPlan` enforces
  that training ends strictly before validation starts, and validation
  ends strictly before test starts (raises `ValueError` otherwise).
- `validate_test_period_untouched()` must be called and must return
  `True` before any test-period result is generated or reported.
- Any research result computed against 2024/25 (the test period)
  before the training/validation seasons are fully acquired and
  modelling is complete would itself be a form of test-set leakage
  (using the "final answer" data to shape earlier decisions) — this
  is why Stage 3A stops before any model development, per project
  instructions section 16.

## Next step

Once `reports/audits/football_data_quality_by_season.csv` shows all
five target seasons acquired with acceptable row counts, populate
`data_splits.csv` (in this directory) with real row counts per
competition/season/split, and only then proceed to Stage 3B (Elo/
Poisson baselines).
