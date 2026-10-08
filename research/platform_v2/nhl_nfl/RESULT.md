# NHL + NFL consensus validation — result (2026-10-08, scored once; pre-registration f9ccfd0)

| Sport | Holdout (2020–21) n | Calibration slope [95% CI] | Favourite bands (n ≥ 200) inside 99.5% Wilson | Gate | Status |
|---|---|---|---|---|---|
| NFL | 550 | 1.02 [0.81, 1.27] | none has n ≥ 200 (condition holds vacuously) | **A** | VALIDATED_HISTORICAL; money-eligible (Fraser, multi-sport approval) |
| NHL | 2,350 | 1.22 [1.04, 1.41] | yes (50–60, 60–70, 70–80) | **B** | PROVISIONAL_PROSPECTIVE; paper only |

## Notes
- **NFL:** the A grade rests on the slope interval alone, which is wide because the sample is small. Treat NFL as
  validated with low precision. Prospective data will tighten it.
- **NHL:** the market was *under*-confident in 2020–21. Favourites won more often than priced (slope > 1). The gate
  rules leave it paper-only. That is not tuned or corrected here.
- **Data:** the newest validated season is 2021. Current calibration is confirmed prospectively from the Odds API
  collection (`collect-us`, budget consumer `us_sports_board`, 40 credits/month).
