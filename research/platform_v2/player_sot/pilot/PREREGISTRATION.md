# Player SOT pilot — signal test on openly licensed data (PRE-REGISTRATION)

Written and committed 2026-10-02 after the data audit (`WYSCOUT_AUDIT.json`) and before any model computation.

The audit gate passed:
- 40,172 starter observations;
- exactly 11 starters in every team-match;
- no duplicates or SOT/goal violations;
- derived SOT per match within 1–3% of Football-Data in all 5 leagues.

**Data:** Wyscout public dataset (CC BY 4.0), 2017-18, EPL / LaLiga / Serie A / Bundesliga / Ligue 1.

**Scope:** research only. No odds of any kind enter any model. The result labels a PILOT outcome on one historical
season. It is not a validation of a current-season production model.

## Question
Using sporting information known before kickoff plus the confirmed starting XI (post-lineup design), can P(player
1+ SOT) and P(player 2+ SOT) for starters be predicted materially better than simple non-market baselines?

## Population and targets
- **Population:** starting outfield players (GK excluded; their 1+ SOT base rate is 0.03%).
- **History requirement:** the player has ≥ 3 prior appearances this season.
- **Actual minutes:** never a feature. Minutes are the exposure only.
- **Targets:**
  - `sot_1plus` (PRIMARY);
  - `sot_2plus` (secondary).

## Periods
- **TRAIN:** matches before 2018-01-01.
- **DEVELOPMENT:** 2018-01-01 to 2018-02-28. All model choices are made here.
- **SEALED HOLDOUT:** 2018-03-01 to the end of the season.
  - It is opened once, after `FROZEN_SPEC.json` is committed.
  - It is refit on TRAIN + DEVELOPMENT.

## Features (built by `research_shadow/player_sot.prior_features`; strictly earlier matches only)
- Player's prior SOT per 90 and shots per 90 over the last 10 appearances. Both are shrunk toward the
  role × competition rate with 450 minutes of prior weight.
- Prior starts share.
- Role dummies.
- Team's prior SOT for per match, and opponent's prior SOT conceded per match.
- Home flag and competition dummies.

## Models (fixed, no search)
- **A1:** logistic regression for each target on the features above (log1p for rates).
- **A2:** Poisson regression for the player's SOT count, using the same features; P(≥k) taken from the Poisson
  distribution.
- **Family choice:** best mean development log loss over the two targets. A1 is preferred if within 0.0005.

## Baselines
- **B0:** starter rate by competition × role (TRAIN).
- **B1:** the player's shrunk prior SOT per 90, giving a Poisson P(≥k) over a full 90 minutes.
- **Comparator:** the better baseline on development log loss for `sot_1plus`.

## Rules (fixed)
- **Proceed to the holdout** only if, on development, Model A beats the comparator by Δlogloss ≤ −0.002 for
  `sot_1plus`. Otherwise record NO_SIGNAL and keep the holdout sealed.
- **PILOT_SIGNAL**, judged on the holdout `sot_1plus`, requires all three of:
  1. Δlogloss vs comparator ≤ −0.002 with match-bootstrap 95% CI upper < 0 (1,000 resamples, seed 7);
  2. calibration slope in [0.85, 1.15] and |intercept| ≤ 0.10;
  3. Δ < 0 in ≥ 4 of 5 leagues.
- Otherwise NO_SIGNAL. `sot_2plus` is reported as secondary.
- No retuning after opening.
- **If PILOT_SIGNAL:** a current-season Model A cycle (data source per the licensing decision) and a Betfair market
  comparison become justified.
