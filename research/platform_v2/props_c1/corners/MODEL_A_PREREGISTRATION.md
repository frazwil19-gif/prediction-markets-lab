# Corners Model A — sports-only probability model (PRE-REGISTRATION, final)

Written and committed 2026-10-02 BEFORE any feature-discovery or model-fitting computation for this cycle.
Authority: Fraser's directive "CONTINUE PROGRESS NOW — PARALLEL PROBABILITY RESEARCH" (2026-10-02), which replaced
"no Phase 2/3 before Gate 0" with "no MARKET COMPARISON or FINANCIAL corners research before Gate 0".
This document supersedes the Phase 2–4 sections of `PREREGISTRATION.md` (797b443) for Model A; the Gate 0 rule
there still governs Models B/C. Research only: no prices, no EV, no paper betting, no production use.

## 0. Disclosure of prior exposure (no fully unseen historical period exists)
- The C1 probe (one pre-registered run, untuned) evaluated a simple corners Poisson GLM on 2022-07 → 2026-09 in
  aggregate (Δlogloss vs league mean −0.0024 / −0.0032).
- The Phase 1 audit (descriptive, all periods) reported means, line frequencies and the home/away correlation
  (−0.22) on all data.
Nothing in this cycle's development uses any statistic computed on the sealed period below; the holdout is
"sealed for this model", not pristine. A genuinely prospective check (matches after 2026-09-03, when new data is
ingested) is added as a later confirmation, not a precondition.

## 1. Data
- `Matches.csv` (xgabora, Football-Data derived). Evaluation divisions: E0 E1 SC0 N1 D1 F1 SP1 I1 P1 B1.
- Team histories (rolling features) use every match of that team in any division of the file that has corners
  data, strictly before kickoff (so promoted/relegated teams keep their history).
- Evaluation sample: matches in the 10 divisions on/after 2005-07-01 with both corner counts present.
- `C_*` columns are never used (possible post-match). Bookmaker odds columns are never used (Model A is sports-only).

## 2. Periods (season = 1 July – 30 June)
- DISCOVERY: 2005-07-01 → 2019-06-30 — raw behaviour analysis and feature screening only.
- DEVELOPMENT (walk-forward): evaluation seasons 2019-20, 2020-21, 2021-22, 2022-23, 2023-24. Each fold is trained
  on all evaluation-sample matches from 2005-07-01 up to that season's start. All model choices use these folds only.
- SEALED HOLDOUT: 2024-07-01 → end of data (2024-25, 2025-26, 2026-27 partial). Trained on everything before
  2024-07-01 with the frozen specification. Opened ONCE by a guarded script after `FROZEN_SPEC.json` is committed.

## 3. Targets and lines
- Total corners T = HC + AC; binary lines 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5.
- Team corners (secondary): home HC and away AC at 3.5, 4.5, 5.5, 6.5.
- Full-distribution log score of T (−log P(T = t)) is reported as a diagnostic and is the selection criterion
  for features (§5) and families (§6).

## 4. Candidate features (pre-match only; let the data decide)
Rolling means use a team's prior matches only, min_periods = 3; when unavailable they are filled with the prior
rolling mean of that statistic in the match's division (no indicator). Groups (each adds its listed columns, log for
rates):
- G1 corners5, G2 corners10, G3 corners20: home-team corners for/against, away-team corners for/against (4 cols each)
- G4 venue10: home team's home-only corners for/against, away team's away-only corners for/against (window 10)
- G5 shots10, G6 sot10, G7 goals10: for/against for both teams (4 cols each)
- G8 elo: (EloH − EloA)/100 and ((EloH + EloA)/2 − 1500)/100 (file Elo is pre-match; missing → team's last known)
- G9 rest: log(1 + min(days since team's previous match in file, 14)) for both teams (league matches only — caveat)
- G10 stage: month-of-season index (Jul = 0 … Jun = 11) / 11
- G11 league: division dummies (E0 reference)
Always included (base): intercept + log(division rolling mean of the target over its previous 380 matches).

## 5. Discovery analysis and feature selection
- DISCOVERY set, descriptive: Spearman correlation of each feature with HC, AC and T; per-season correlation
  (sign consistency, sd); per-league correlation; feature–feature correlation (redundancy). Exploratory label.
- Selection (confirmatory procedure, development folds only): forward stepwise over groups using the NB2 total
  model (§6 MA2). A group is added if it improves the mean development log score of T by ≥ 0.0005 nats AND improves
  it in ≥ 4 of 5 folds; best qualifying group added first; stop when none qualifies or 6 groups are in.

## 6. Model families (on the selected groups)
- MA1 Poisson GLM on T.
- MA2 NB2 on T (mean by log-link GLM, dispersion α by maximum likelihood on the training fold).
- MA3 team-split, independent: NB2 for HC and for AC (each with the same groups), T by convolution assuming
  independence.
- MA4 team-split, dependent: NB2 marginals for HC and AC joined by a Gaussian copula; ρ estimated on the training
  fold (normal scores of randomised PIT residuals); T distribution by Monte-Carlo (common random numbers,
  20,000 draws, seed 11).
Family choice: best mean development log score of T; a simpler family (MA1 < MA2 < MA3 < MA4) is preferred if within
0.0005 nats. Team-corner probabilities come from the NB2 marginals (MA3/MA4 marginals) regardless of family.
Independence is TESTED (MA3 vs MA4), never assumed.

## 7. Baselines (non-market)
- B0 league rolling-mean Poisson (division prior-380 mean of T).
- B1 team historical-rate Poisson: μ = ½(h_cf10 + a_ca10) + ½(a_cf10 + h_ca10) (no fitting).
- B2 league rolling-mean NB2 (α fit on the training fold).
The primary comparator is the baseline with the best mean development primary metric (chosen before the holdout).

## 8. Metrics and uncertainty
- PRIMARY: mean binary log loss over lines 8.5, 9.5, 10.5, 11.5 (per match, averaged over the 4 lines).
- Secondary: log loss and Brier at every line; full log score of T; calibration intercept and slope (logistic
  regression of outcome on logit p) at each line; reliability by probability decile; AUC; team-line metrics;
  breakdown by league and by season; high/low probability regions (p < 0.25, p > 0.75).
- Uncertainty: match-level bootstrap, 1,000 resamples, seed 7 (one row per match; ESS = N).

## 9. Continuation and verdict rules (fixed now)
- Proceed to the holdout only if, in development, Model A beats the primary comparator by Δprimary ≤ −0.001 (mean
  over folds) AND in ≥ 4 of 5 folds. Otherwise STOP: record NULL; the holdout stays sealed.
- HOLDOUT verdict PROBABILITY_VALIDATED iff all hold:
  1. Δprimary vs primary comparator ≤ −0.001 with bootstrap 95% CI upper < 0;
  2. calibration at 9.5 and 10.5: slope in [0.85, 1.15] and |intercept| ≤ 0.10;
  3. Δprimary < 0 in ≥ 7 of 10 leagues and in every holdout season with ≥ 1,000 matches.
  Otherwise NULL (reported in full). No retuning after opening; any change is a new cycle.
- PROBABILITY_VALIDATED ⇒ status "PROBABILITY_VALIDATED / PRICE_GATE_PENDING". No EV claims, no betting.

## 10. Reproducibility
Script `scripts/corners_model_a.py` (modes: `discovery`, `develop`, `holdout`). Outputs under
`research/platform_v2/props_c1/corners/model_a/`. The holdout mode refuses to run without a committed
`FROZEN_SPEC.json` and refuses a second opening (marker file).
