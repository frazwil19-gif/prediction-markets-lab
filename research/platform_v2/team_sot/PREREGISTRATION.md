# Team SOT prediction engine — team-SOT-A (PRE-REGISTRATION)

Written 2026-10-07, before any team-SOT-A model is fitted or evaluated. Direction: "can we predict this outcome?"
(project direction change, 7 Oct). Research predictor only: it never stakes, and no price enters the model.

## Prior evidence and honesty notes
- Props C1 probe (pre-registered, 2 Oct): a Poisson GLM on rolling-10 SOT for/against + league mean + Elo beat the
  league baseline on 2022-07..2026-09 (home SOT>4.5 ΔLL −0.0578 [−0.0631, −0.0525]; away −0.0499), overdispersion
  1.17–1.18, so negative binomial (NB) is preferred.
- **The 2025/26 holdout below overlaps the C1 test window.** It is therefore a confirmation on data a closely related
  model has already been scored on, not a virgin holdout. Stated up front; the verdict wording reflects it.
- While checking data coverage before writing this file, row counts and the mean home/away SOT of 2025/26 were
  printed (3,455 matches; means 4.77 / 3.92). No model output was computed.

## Data
xgabora `Matches.csv` (Football-Data derived; `HomeTarget`/`AwayTarget` = Football-Data `HST`/`AST`), divisions
E0 E1 SC0 N1 D1 F1 SP1 I1 P1 B1, matches from 2005-07-01. Features are rebuilt with the frozen corners-A data
builder (`scripts/corners_model_a.py::build`, strictly prior matches, per team, all venues).

## Fixed specification (no selection)
Per side s ∈ {home, away}, NB2 regression, log link:
log μ_s = b0 + b1·log(league rolling mean of side-s SOT, prior 380 matches of the division, min 50)
        + b2·log(h_tf10) + b3·log(h_ta10) + b4·log(a_tf10) + b5·log(a_ta10)
where h_tf10 = home team's mean SOT for over its previous 10 matches (min 3; division fill), etc. α (NB dispersion)
by maximum likelihood. No Elo (not available from the free daily Football-Data files used in production), no market
information.

## Periods
- TRAIN: matches before 2025-07-01.
- HOLDOUT: 2025-07-01 to 2026-06-30 (one full season), scored ONCE with the TRAIN fit.
- PRODUCTION FIT (only after the holdout verdict): refit on all matches before 2026-07-01 → `team_sot_A_v1_params.json`.

## Targets / lines
P(home SOT > L) and P(away SOT > L), L ∈ {2.5, 3.5, 4.5, 5.5}. Primary lines: home 4.5, away 3.5 (closest to 50% base
rate in the C1 probe). Comparator M0: Poisson with μ = the league rolling side mean (same definition as b1's input).

## Verdict (fixed)
HISTORICALLY_CONFIRMED iff on the holdout, for BOTH primary lines:
1. Δlogloss (team-SOT-A − M0) ≤ −0.005 with match-bootstrap 95% CI upper < 0 (1,000 resamples, seed 7);
2. calibration slope in [0.85, 1.15] and |intercept| ≤ 0.10;
3. Δlogloss < 0 in at least 8 of the 10 divisions.
Otherwise NOT_CONFIRMED (recorded; the engine is not deployed). Secondary lines are reported, not decisive.

## Deployment status if confirmed
RESEARCH predictor on the Daily Prediction Board ("RESEARCH — NOT MONEY ELIGIBLE"; fair odds shown, no betting
instruction). Promotion to money-eligible needs a separate prospective check (pre-registered later) AND a legitimate
price route.
