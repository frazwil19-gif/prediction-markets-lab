# Model Governance

**Status: planned for Stage 3+ (`models/model_registry.py`). Stage 1
has no models to govern yet — only the bookmaker consensus is
calculated end-to-end.**

## Required fields per model

Every model, once introduced, must record:

- Model ID
- Version
- Creation date
- Feature list
- Training period
- Validation period
- Methodology
- Assumptions
- Limitations
- Calibration results
- Performance results
- Promotion status
- Rollback status

## Status lifecycle

```
RESEARCH → BACKTEST → PAPER → EXPERIMENTAL_LIVE → APPROVED_LIVE
                                                        ↓
                                                     RETIRED
```

No model should be promoted to `APPROVED_LIVE` merely because it had a
profitable short period — see `docs/VALIDATION_PLAN.md` for the actual
promotion criteria (historical backtest + paper-trading targets).

## Stage 1 note

Because no model exists yet, `config/model_weights.yaml` currently
blends `P_consensus` with a `P_model` that has not been implemented.
Do not treat `P_final` as available until a model reaches at least
`BACKTEST` status and `models/model_registry.py` exists to track it.
