# Props Cycle 1 — bounded team-stat predictability probe (PRE-REGISTRATION)

Written 2026-10-02 before any target/feature computation. Research only (Track B/C). No prop paper betting,
no SGMs, no production prop model, no paid data. Track A is separate.

## Question
With data already held (xgabora `Matches.csv`, Football-Data derived team match stats), can pre-match
information predict **match total corners**, **match total cards** and **team shots on target** better than a
naive league baseline, and are the outcome distributions well-calibrated by a simple count model?
This measures *predictability only*. No historical prop prices are held, so **no value/EV claim is possible**.

## Data
- Rows with non-null HomeCorners/AwayCorners (corners), HomeYellow/AwayYellow/HomeRed/AwayRed (cards),
  HomeTarget/AwayTarget (SOT). Divisions: E0 E1 SC0 N1 D1 F1 SP1 I1 P1 B1 (project coverage Tiers 1–2 that are
  in the file).
- `C_*` columns excluded (possible post-match leakage). Bookmaker 1X2 / O/U 2.5 closing-ish odds in the file are
  used only as an *optional* market-prior feature in model B and flagged: their timestamp is not guaranteed
  pre-match-decision, so model B is an upper bound, not deployable as-is.

## Targets (fixed)
- T1 total corners; lines 9.5 and 10.5.
- T2 total cards = yellows + reds (1 per card); lines 3.5 and 4.5. (Bookmaker card-market settlement varies:
  booking points, second-yellow handling — recorded as a settlement-rule caveat.)
- T3 home-team SOT and away-team SOT; line 4.5.

## Features (strictly prior matches only, same division)
Per team: rolling mean (last 10 league matches, min 5) of stat-for and stat-against, home/away pooled;
league-season-to-date mean of the target (prior matches only); Elo difference (file Elo, pre-match).

## Models (fixed)
- Baseline (M0): Poisson with mean = league rolling mean of the target (prior 380 matches of that division).
- M1 (sports data only): Poisson GLM, log-link, features above (no prices).
- M2 (M1 + market prior): adds implied home win prob from OddHome/OddDraw/OddAway (proportional) and
  implied P(over 2.5 goals). Flagged upper bound (price timing).
- P(over line) from the fitted Poisson mean. Overdispersion (var/mean of residual) reported; if >1.15 a
  negative-binomial variant is reported as a secondary row (not a model selection by test outcome).

## Chronology
Train: seasons ending ≤ 2022 (match_date < 2022-07-01). Test: 2022-07-01 to latest. No refits on test. One run.

## Metrics
Log loss and Brier for each binary line vs M0; paired bootstrap 95% CI (match-level, 1000 resamples, seed 7)
for Δlogloss (M1−M0, M2−M0); calibration by decile (max abs gap); N per target.

## Decision rule (pre-set)
A target is "predictable beyond baseline" if Δlogloss CI upper < 0 for M1 at both lines. That only promotes it to
the *candidate* list for prospective price observation; it is not a betting signal.
Negative results are recorded.
