# team-SOT-A holdout result: NOT_CONFIRMED (2026-10-07, scored once)

The pre-registered spec (commit 22213f8) was scored once on 2025/26 (3,455 matches; train 56,978). Full numbers are in
`HOLDOUT.json`.

| Primary line | Δlogloss vs league baseline | 95% CI | Cal. slope | Cal. intercept | Divisions better | Criteria |
|---|---|---|---|---|---|---|
| Home SOT > 4.5 | −0.0362 | [−0.0458, −0.0275] | 0.933 | 0.013 | 10/10 | all pass |
| Away SOT > 3.5 | −0.0291 | [−0.0388, −0.0202] | **0.845** | 0.033 | 10/10 | calibration fails (slope < 0.85) |

**Verdict: NOT_CONFIRMED.** The model discriminates strongly (every line and every division beats the baseline).
However, the away-side probabilities are too extreme (slope 0.78–0.88 across away lines), and the pre-registered
calibration gate fails by 0.005 on the primary away line.

As pre-registered, the engine is **not deployed** and nothing here is re-tuned. The finding is kept: team SOT is
highly predictable, and the away model needs calibration. Any follow-up (for example a recalibration layer fitted on
these 2025/26 out-of-sample predictions and judged prospectively on matches after the new pre-registration) is a new,
separately pre-registered cycle.
