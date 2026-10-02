# Goals / team totals — EXPLORATORY raw-predictability probe (plan written before computation)

Label: EXPLORATORY. Not confirmatory; no holdout is opened; results only decide whether a full pre-registered cycle
is justified. Written and committed 2026-10-02 before running `scripts/goals_totals_probe.py`.

Prior evidence reused, NOT re-run: O/U 2.5 (`research/ou25_discovery/`) — market best on every split, fundamentals
worse; BTTS (`research/btts_outcome_prediction/`) — market-implied Poisson selected, data-only model REJECTED on its
sealed holdout (AUC 0.496).

Question: for TEAM goal targets (home > 0.5, home > 1.5, away > 0.5, away > 1.5) and total > 1.5 / > 3.5 — targets not
previously modelled — does independent sporting data beat simple baselines, and how close does it get to a
market-implied Poisson derived from 1X2 + O/U 2.5 prices (used here only as a benchmark of what is already
priceable)?

Data: `Matches.csv`, divisions E0 E1 SC0 N1 D1 F1 SP1 I1 P1 B1. Walk-forward evaluation seasons 2019-20 … 2023-24
only (the same development window as corners; 2024-07+ untouched).
Models:
- N0 league rolling-mean Poisson per side (prior 380 matches).
- D1 data-only Poisson GLM per side: log rolling (prior 10) goals for/against, shots for/against, SOT for/against of
  both teams, Elo difference, league mean (fixed specification, no selection).
- M1 market-implied independent Poisson: (λH, λA) fitted per match to the proportional de-vigged 1X2 and O/U 2.5
  probabilities (least squares). Upper-bound benchmark (price timing in this file is closing-ish).
Metrics: binary log loss per target, Brier, calibration slope; paired Δ D1−N0 and D1−M1 with match bootstrap CIs.
Decision rule (pre-set): a full cycle for a team-total target is justified only if D1 beats N0 (CI upper < 0) AND is
within 0.002 log loss of M1, or beats it. Otherwise team totals are best served by the market-implied estimator
(already priceable) and a data-only cycle is NOT justified.
