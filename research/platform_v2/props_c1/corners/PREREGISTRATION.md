# Corners Cycle 1 — data-first probability research (PRE-REGISTRATION)

Written and committed 2026-10-02 BEFORE the corners data audit and before any corners model is fitted or tuned.
Research only. Approved scope: "pre-register the proposed corners research cycle" (Fraser, 2026-10-02).
No prop paper betting, no production model, no SGMs, no recurring price capture, no paid data.

## Research question
Can leakage-safe sporting data produce well-calibrated probabilities for football match corner totals (and team
corners), and — only if executable two-sided prices exist — how does that estimator compare with market consensus?

## Gate 0 (STOP rule, pre-set)
The single approved price probe (≤2 credits) decides price feasibility. If no executable UK venue quotes two-sided
corners totals (or a fair market probability cannot be constructed), the cycle is labelled
**PREDICTABLE BUT CURRENTLY UNPRICEABLE**: the data audit (Phase 1) may still be recorded, Phases 2–4 are NOT run,
and research moves to the next evidence-supported market. No corners model is forced.

## Phase 1 — data audit (descriptive, no modelling)
Source: Football-Data-derived `Matches.csv` (xgabora), divisions E0 E1 SC0 N1 D1 F1 SP1 I1 P1 B1.
Report: N by league and season; missingness; definition consistency (any season/league where HC/AC look
non-comparable, e.g. all-zero or implausible values); distribution, mean, variance, var/mean (overdispersion);
home/away structure (home share, home–away correlation); temporal drift (season means, by league); league
differences; candidate line frequencies (P(total > L) for L = 7.5…13.5, team > 3.5…6.5); anomalies (duplicates,
negative/implausible counts > 25, dates out of order). Script: `scripts/corners_c1_audit.py`. Output: `AUDIT.md`,
`AUDIT.json`. Phase 1 outcomes are descriptive and are NOT used to select features.

## Phase 2 — feature discovery (training data only)
Chronology: TRAIN = matches before 2021-07-01; VALIDATION = 2021-07-01 to 2023-06-30 (feature/model choice);
SEALED TEST = 2023-07-01 onward, touched exactly once after the final specification is committed.
Candidate features (none assumed to matter): team and opponent rolling corners for/against (windows 5/10/20,
prior matches only), rolling shots and SOT for/against, Elo and Elo difference, home/away, league, season-to-date
league mean, rest days, plus (Model C only) market state from 1X2 / O/U 2.5 prices.
Selection: permutation importance and likelihood-ratio tests computed on TRAIN, confirmed on VALIDATION only.

## Phase 3 — models
- MODEL A — sports-only (no bookmaker prices of any kind): Poisson vs negative-binomial GLM for total corners,
  and a team-split model (home and away corners modelled separately, total via convolution). Choice by validation
  log loss.
- MODEL B — market consensus: de-vigged two-sided corners-total prices (exists only prospectively, if Gate 0 passes).
- MODEL C — hybrid: Model A features + market fair probability (prospective only).
Model A is frozen (code + coefficients + git SHA) before any comparison with B. A is NOT preferred automatically;
probability quality decides.

## Phase 4 — evaluation
Lines 8.5, 9.5, 10.5, 11.5 (total) and 4.5, 5.5 (team). Metrics: log loss, Brier, calibration (decile and
reliability slope/intercept), AUC, by-league and by-season stability, N, match-cluster bootstrap 95% CIs
(1000 resamples, seed 7). Baseline: league rolling-mean Poisson (as in the C1 probe).
A vs B (prospective only): paired log-loss difference on the same events and timestamps; review trigger ≥300 priced
events or a protocol INTERIM, whichever comes first — not a calendar duration.

## Not in scope
Betting rules, thresholds, staking, paper bets, SGMs, any production integration. Promotion of anything requires a
separate Fraser approval. Negative results are recorded.
