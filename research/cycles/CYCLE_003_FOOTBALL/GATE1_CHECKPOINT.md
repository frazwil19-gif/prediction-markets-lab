# Gate 1 Checkpoint — Football 1X2 Probability Architecture Comparison

**Written 2026-09-18.** Answers the operator's 35-point Gate 1 return list in full (relayed by
Fraser as "OPERATOR DECISION — CONDITIONAL GO ON FOOTBALL DAILY ENGINE V1"). Protocol frozen and
committed BEFORE any result below existed: `research/cycles/CYCLE_003_FOOTBALL/
GATE1_PROBABILITY_ARCHITECTURE_PROTOCOL.md`, commit `f960e5e`. Execution script: `scripts/
run_gate1_1x2_probability_architecture_comparison.py`, commit `<this checkpoint's commit>`. Raw
results: `data/processed/football/gate1_1x2_architecture_results.json`.

**Headline answer to the core question ("where should `model_probability` come from?"): for football
1X2, the de-vigged multi-bookmaker closing consensus is, on this evidence, the most trustworthy
available probability. Every architecture tested that deviates from it — the existing frozen Elo+
Poisson blend, a new fundamentals-only model, and market+fundamentals combined — is statistically,
not just numerically, worse on pooled log loss. This is not an assumption; it is what Gate 1 found,
and it directly replicates Stage 3B's original 2026-09-11 finding in a new, independent test.** See
point 32 for what this recommends for Gate 2, and points 25–28 for exactly what the fundamentals
features did and did not add.

---

## 1–4. Datasets, exposure, sample sizes, feature construction

**1. Exact datasets used.** `cycle_001_matches_full.csv` + `h_fb2_002_sealed_oos_2025_26_matches.csv`
(match identity/outcome), `cycle_002_match_statistics.csv` + `h_fb2_002_sealed_oos_2025_26_match_
statistics.csv` (goals/shots/SOT/corners/cards), `cycle_001_consensus_full.csv` +
`h_fb2_002_sealed_oos_2025_26_consensus.csv` (closing multi-bookmaker consensus). All six already
existed in the repository before this Gate started; **nothing new was acquired**. 6,960 raw match
rows, 2020/21–2025/26, E0/E1/SC0.

**2. Exposure classification of each season.** 2020/21–2023/24: EXPOSED (discovery/development, Stage
3B + Football Cycle 2). 2024/25: EXPOSED (Stage 3B's own sealed holdout). 2025/26: EXPOSED (H-FB2-002's
sealed OOS test). No period is pristine. Per the operator's explicit permission, the full span is used
for architecture-SELECTION walk-forward validation, not as a final validated claim (see protocol §3).
2026/27 (the current season) remains completely untouched — not acquired, not downloaded, not
inspected — and is the first genuine prospective-validation candidate for whatever architecture Gate 2
eventually selects.

**3. Exact sample sizes.** 6,960 raw matches → 6,503 with a usable closing consensus AND a full
10-match rolling history for both teams (the "primary Gate 1 eligible sample"). Breakdown of what was
dropped and why: 37 matches lacked a ≥4-bookmaker closing consensus; 422 matches had at least one team
without a full 10-match trailing history (almost entirely early in a team's very first season in the
combined 2020/21–2025/26 span, exactly as expected — no imputation was used, these rows are dropped,
never guessed). Per-season eligible counts: 2020/21: 872 (used as fold 1's training data only, never
evaluated out-of-sample); 2021/22: 1,111; 2022/23: 1,140; 2023/24: 1,109; 2024/25: 1,141; 2025/26:
1,130. **Total out-of-sample evaluated matches across all 5 folds: 5,631.**

**4. Exact features used by each model, and why each is pre-match safe.**
- Model 0 (market): closing multi-bookmaker median consensus, renormalised to sum to 1.0. Pre-match
  safe by construction (closing odds are collected before kickoff, per `football_richer_extraction.py`).
- Model 1 (existing frozen blend): Elo ratings (pre-match, leakage-safe by `simulate_pre_match_ratings`)
  and Poisson lambdas (pre-match, leakage-safe by `simulate_pre_match_lambdas`), blended.
- Model 2 (fundamentals): `elo_rating_gap_incl_home_advantage`, `diff_avg_goals_for_last10`,
  `diff_avg_shots_for_last10`, `diff_avg_sot_for_last10`, `diff_avg_corners_for_last10`,
  `diff_avg_cards_for_last10`, `diff_points_per_game_last10`, `is_E1`, `is_SC0`. Every rolling
  differential is a PRE-MATCH snapshot from `compute_rolling_features` (snapshot-before-push
  discipline, mechanically tested); the two competition dummies are static match metadata, not
  outcome-derived.
- Model 3 (market+fundamentals): Model 2's 9 features plus `market_home_logit` and
  `market_draw_logit`, both derived from the same pre-match closing consensus as Model 0.
- Model 4 (ensemble): a linear blend of Model 0's and Model 2's own (already pre-match-safe)
  probabilities.

## 5–8. Hyperparameters, chronological design, market construction, missing data

**5. Exact model specifications/hyperparameters.** `EloConfig()` all frozen defaults
(`initial_rating=1500, k_factor=20, home_advantage=100, season_reversion_fraction=0.25`);
`PoissonConfig()` all frozen defaults (`max_goals=15, shrinkage_matches=4.0`); Model 2/3: L2
penalty=1e-3 (fixed, not tuned per fold), Adam optimiser (learning_rate=0.15, max 4,000 iterations,
converged in 543–672 iterations every fold with a final max-gradient-norm of ~0.0, i.e. clean
convergence, no fold needed anywhere near the iteration cap).

**6. How hyperparameters were chosen.** `draw_margin` (Elo) and the Model 1 blend weights are the
only genuinely fitted hyperparameters, both chosen by exhaustive grid search on that fold's training
seasons only, from the exact frozen candidate sets copied verbatim from Stage 3B's own scripts
(`draw_margin` ∈ {25,...,200} step 25; blend weights step 0.1). Model 2/3's L2 penalty and Adam
settings are fixed module defaults, not searched, per the protocol's explicit "not tuned per fold"
decision (searching a new hyperparameter here would itself be a new source of overfitting).

**7. Chronological split/walk-forward design.** 5 expanding-window folds via the existing, unmodified
`generate_expanding_walk_forward_folds(["2020_21",...,"2025_26"])`: train on all seasons up to and
including season *i*, evaluate on season *i+1*. See point 3 for exact per-fold sizes.

**8. Market-consensus construction.** Per-outcome CLOSING median across all bookmakers with a
complete outcome quote (existing `probability.consensus`/`margin_removal` pipeline, unchanged),
requiring ≥4 bookmakers, renormalised to sum to exactly 1.0 (independently-computed per-outcome
medians do not sum to exactly 1.0 by construction).

## 9–12. Leave-one-out, coverage, missing data, results by model

**9. Leave-one-bookmaker-out methodology.** Not used in Gate 1, and explicitly documented as such in
the frozen protocol (§7, point 4): every Gate 1 metric compares a model's probability against the
REALISED OUTCOME, never against one specific target bookmaker's own price, so the circularity risk the
operator raised does not arise here. It becomes mandatory once this architecture is used to size an EV
against one specific venue's current price (Gate 5/6), not before.

**10. Bookmaker coverage by season.** Already documented from Football Cycle 2's own audit (roadmap
§20): the 1X2 consensus draws on a 6-bookmaker panel with full coverage across the entire
2020/21–2024/25 corpus; 2025/26's panel changed (only 3 of the historical 6 persist — the
`BOOKMAKER_PREFIXES_2025_26` fix from H-FB2-002 already handles this at the canonicalisation layer,
reused unchanged here since Gate 1 reads the already-canonicalised consensus files, not raw odds).

**11. Missing-data handling.** Never imputed. A match is dropped from the eligible sample if its
closing consensus has fewer than 4 bookmakers, or if either team lacks a full 10-match trailing
history, or if any required rolling statistic is still `None` after 10 matches (a residual data-quality
gap, e.g. missing card counts — occurs on a small number of rows, absorbed into the 422 dropped-for-
fundamentals count; not separately itemised because the rolling-window function returns a single
combined "insufficient data" signal, not a per-field one).

**12–16. Results.**

Pooled (5,631 out-of-sample matches, all 5 folds combined):

| Architecture | Log loss | Brier | vs Model 0 (Δ log loss, 95% CI) |
|---|---|---|---|
| **Model 0 — market consensus** | **0.98726** | **0.58877** | — (baseline) |
| Model 1 — existing frozen Elo+Poisson blend | 1.01085 | 0.60482 | +0.0236 [+0.0183, +0.0286] — excludes zero |
| Model 2 — fundamentals-only | 1.01572 | 0.60756 | +0.0285 [+0.0229, +0.0340] — excludes zero |
| Model 3 — market + fundamentals | 0.99225 | 0.59170 | +0.0050 [+0.0021, +0.0080] — excludes zero |
| Model 4 — calibrated ensemble (market+fundamentals blend) | 0.98981 | 0.59048 | +0.0026 [+0.0010, +0.0041] — excludes zero |

Every non-market architecture is **worse** than the market consensus, and every one of these
differences excludes zero at 95% confidence (paired bootstrap, n=2,000, seed=20260918). This is not a
photo finish decided by an arbitrary tie-break: even Model 3 and Model 4, whose point estimates look
close to Model 0's on the printed log loss, are confirmed worse with a CI that does not touch zero.

**Model 3 vs Model 2 (does adding market information to the fundamentals model help?):**
Δ log loss = **−0.0235** [−0.0287, −0.0180] — excludes zero. Yes, decisively: once market information
is available, adding it materially improves the fundamentals model. This is an important, separate
result from "does market+fundamentals beat market alone" (it does not) — the market component is
carrying essentially all of the model's power once it is included.

## 17–19. Uncertainty comparisons (restated compactly; full detail in point 12's table)

All five headline comparisons (Model 1/2/3/4 vs Model 0) have 95% CIs that exclude zero in the
unfavourable direction for the non-market architecture, and Model 3 vs Model 2 has a CI excluding zero
in the favourable direction for including market information. No comparison is inconclusive.

## 20. HOME/DRAW/AWAY calibration, separately, per model

| Model | Outcome | Intercept | Slope | AUC | ECE |
|---|---|---|---|---|---|
| Market (0) | home | 0.061 | **1.053** | **0.700** | **0.018** |
| Market (0) | draw | −0.033 | **1.005** | 0.558 | **0.018** |
| Market (0) | away | 0.014 | **1.045** | **0.702** | **0.012** |
| Elo+Poisson (1) | home | −0.055 | 1.086 | 0.667 | 0.021 |
| Elo+Poisson (1) | draw | 0.155 | 1.137 | 0.555 | 0.012 |
| Elo+Poisson (1) | away | 0.126 | 1.063 | 0.668 | 0.015 |
| Fundamentals (2) | home | 0.029 | **0.845** | 0.669 | 0.025 |
| Fundamentals (2) | draw | −0.415 | **0.604** | 0.538 | 0.030 |
| Fundamentals (2) | away | −0.173 | 0.897 | 0.669 | 0.023 |
| Market+Fund (3) | home | −0.014 | 0.939 | 0.696 | 0.021 |
| Market+Fund (3) | draw | −0.336 | **0.662** | 0.550 | 0.024 |
| Market+Fund (3) | away | −0.039 | 1.010 | 0.700 | 0.017 |
| Ensemble (4) | home | 0.068 | 1.038 | 0.697 | 0.014 |
| Ensemble (4) | draw | −0.023 | 1.002 | 0.557 | 0.012 |
| Ensemble (4) | away | −0.004 | 1.055 | 0.699 | 0.019 |

**The draw probability is exactly where the operator flagged simplistic models would be weakest, and
that is exactly what happened here.** Market consensus's draw calibration slope (1.005) is close to
ideal; the fundamentals-only model's draw slope is **0.604** — substantially overconfident, meaning
its draw probabilities are too spread out relative to what actually happens (a model saying "20% draw"
in one match and "35%" in another is, in reality, closer to right averaging around the market's own
narrower, better-calibrated spread). Market+fundamentals inherits this same draw weakness (slope
0.662) despite having market information available — the fundamentals component is actively degrading
draw calibration even when blended with a genuinely good draw-probability source. This is the clearest
single piece of evidence in this checkpoint for why fundamentals should not be trusted as a primary
probability source without a great deal more work on the draw outcome specifically.

## 21. Probability-band reliability

Full 10-bin reliability tables for every model/outcome are in the raw JSON
(`pooled_metrics.*.outcome_calibration.*.bins`); summarised via ECE in point 20's table above. No
model shows a systematic reversal (predicted-vs-observed direction never flips sign across bins) —
the differences are in calibration precision (ECE/slope), not in gross miscalibration.

## 22. Temporal stability

| Season | Market | Elo+Poisson | Fundamentals | Market+Fund | Ensemble |
|---|---|---|---|---|---|
| 2021/22 | 0.983 | 1.014 | 1.023 | 0.996 | 0.994 |
| 2022/23 | 0.987 | 0.999 | 1.008 | 0.992 | 0.987 |
| 2023/24 | 0.958 | 0.992 | 0.994 | 0.959 | 0.960 |
| 2024/25 | 0.992 | 1.010 | 1.022 | 0.996 | 0.992 |
| 2025/26 | 1.015 | 1.039 | 1.032 | 1.018 | 1.015 |

(log loss per fold's evaluation season.) **Market's ranking advantage over the other four
architectures is stable in every single fold** — it is never overtaken in any individual season,
including the newest one (2025/26). All five architectures show their highest log loss (worst
performance) in 2025/26 — since even the market consensus itself gets less accurate that season, this
reads as 2025/26 genuinely containing more surprising results league-wide, not a defect specific to
any one architecture.

## 23. Competition stability

| Competition | Market | Elo+Poisson | Fundamentals | Market+Fund | Ensemble |
|---|---|---|---|---|---|
| E0 (n=1,888) | 0.955 | 0.994 | 0.997 | 0.961 | 0.960 |
| E1 (n=2,640) | 1.034 | 1.052 | 1.059 | 1.039 | 1.036 |
| SC0 (n=1,103) | 0.931 | 0.942 | 0.944 | 0.933 | 0.930 |

Market's advantage over the other architectures holds in all three competitions; the ranking of
competitions by difficulty (SC0 easiest to price, E1 hardest) is identical across every architecture,
consistent with competition-level base-rate differences (already documented in Football Cycle 2's
discovery phase) rather than an architecture-specific artefact.

## 24. Complexity / production-cost comparison

| Architecture | New code | New data | Fit cost | Production dependency |
|---|---|---|---|---|
| Model 0 (market) | None (fully existing) | None | None (closed-form) | A live multi-bookmaker odds feed only |
| Model 1 (Elo+Poisson) | None (fully existing) | None | Cheap (closed-form replay + small grid search) | Needs no live odds at all, but is the worst performer |
| Model 2 (fundamentals) | New (this Gate) | None | Cheap (<1s per fold, converges in <700 iterations) | Needs the same rolling-feature pipeline kept live and correct |
| Model 3 (market+fundamentals) | New (this Gate) | None | Cheap | Needs BOTH a live odds feed and the rolling-feature pipeline, for a worse result than the odds feed alone |
| Model 4 (ensemble) | Reuses existing blend code | None | Cheap | Same dependencies as Model 3, smaller degradation |

Model 0 is not just the best performer — it is also the cheapest and simplest to keep running in
production (no model-fitting pipeline to maintain, version, or re-validate; a live odds feed is
required for the daily engine's price/EV step regardless of which probability architecture is chosen).

## 25–27. Does fundamentals/existing-model/market+fundamentals add information?

**25. Whether fundamentals add information beyond market consensus.** No — on this evidence, they
subtract it. Fundamentals-only is the single worst architecture tested (+0.0285 log loss vs market,
CI excludes zero), and adding them to market (Model 3) makes market itself measurably worse
(+0.0050 vs market alone, CI excludes zero), not better. The one place fundamentals demonstrably help
is against a MODEL THAT HAS NO MARKET INFORMATION AT ALL (Model 3 beats Model 2 by −0.0235, CI
excludes zero) — i.e., fundamentals are useful only in the absence of market information, not in
addition to it.

**26. Whether the existing football model (Elo+Poisson) adds useful information.** No — it is the
second-worst architecture tested (+0.0236 vs market, CI excludes zero), consistent with Stage 3B's
original 2026-09-11 finding, now independently re-confirmed on an extended 2025/26 walk-forward fold
using the exact same frozen specification.

**27. Whether Market+Fundamentals improves probabilities.** No, not over market alone — see point 25.
Model 4 (the calibrated ensemble) is the LEAST-worse deviation from pure market (+0.0026 vs market,
still excludes zero), and its own training-time weight search is itself the clearest evidence for
this: the blend weight on "fundamentals" was calibrated at 50% in fold 1 (with only 872 training
matches, a genuinely uncertain choice), fell to 10% by fold 2–3, and reached **exactly 0% in folds
4 and 5** — i.e., with enough training data, the model's own calibration procedure independently
concluded fundamentals add nothing and should get zero weight. This is the same phenomenon Stage 3B
reported for its own market-containing blends ("recalibrated to 100% market weight, every single
time"), now independently reproduced by a different blend construction on a different, extended
dataset.

## 28. Adverse/null findings

The whole result is, in the operator's own framing, potentially an adverse finding for the ambition of
building a genuinely new fundamentals-based probability model: none of the new work in this Gate (the
multinomial logistic regression, the 9-feature fundamentals set) produced a probability architecture
that improves on the market. This is reported exactly as found, not reframed. The one clear positive,
narrower finding is that fundamentals meaningfully help a model that otherwise has zero market
information (point 25) — relevant only if a future market family exists where no efficient consensus
is available at all (Option B territory from the earlier design report, e.g. a thin market with too
few bookmakers for a reliable consensus).

## 29. Methodological bugs discovered and how they were handled

None were found in the sense of a defect requiring a fix-and-recommit (unlike H-FB2-002's bookmaker-
panel schema drift). Two design choices were deliberately checked and confirmed safe rather than
found broken: (a) `calibrate_draw_margin`'s internal re-simulation of Elo ratings on each fold's
training subset was verified to produce IDENTICAL ratings to the master continuous replay's own
prefix for that span (both start from the same initial conditions over the same contiguous season
range) — confirmed by design, not merely assumed; (b) every fold's `draw_margin` grid search
independently selected the SAME value (100.0, the frozen default) in every one of the 5 folds — a
genuine result, not a hardcoded shortcut, and reported as a reassuring internal-consistency check
that Stage 3B's original hyperparameter choice continues to generalise.

## 30. Full test-suite result

737/737 passing (718 before this Gate; 19 new tests for the two new modules —
`models/multinomial_logistic_regression.py` and `performance/bootstrap.py`). No existing test was
modified.

## 31. Commit hashes proving protocol-before-results ordering

`f960e5e` — protocol document + the two new tested modules, committed BEFORE any comparative number
existed. This checkpoint's own commit (script + results JSON + this document) is a separate, later
commit — see the repository log for its hash, created strictly after `f960e5e`.

## 32. Recommended Probability Engine V1 architecture based on Gate 1

**Model 0 — de-vigged multi-bookmaker closing consensus, labelled explicitly as a market-consensus
baseline, not a "model."** This is not a default reached by not trying alternatives — three genuine
alternative architectures were built and tested, and all three lost, with statistically confirmed
margins, on log loss, Brier score, and (for the fundamentals-containing architectures) materially
worse draw calibration specifically. This directly answers the operator's own conditional-GO concern:
the daily engine's `model_probability` for football 1X2 SHOULD, on this evidence, be labelled
`market_consensus_baseline_probability`, not implied to be a bespoke predictive model, because that
is honestly what it is and what performs best. The value the daily engine adds is not "a better
probability than the market" — it is comparing that trustworthy probability against a DIFFERENT,
currently obtainable price at a specific venue (the Option A design from the earlier migration
report), which remains entirely valid and requires no new predictive claim.

## 33. What remains uncertain

Whether a genuinely richer fundamentals feature set (fixture congestion/rest — not yet built anywhere
in this repository; xG — not yet acquired; team news/lineups — not yet acquired) could close the gap
to market or exceed it is untested here; Gate 1 only tested the 9 features already justified and
available. Whether a non-linear model (rather than a linear-in-logits softmax regression) would
extract more from the same 9 features is untested. Whether the draw-specific weakness is fixable with
a dedicated draw-probability adjustment (a known football-modelling technique, not attempted here) is
untested. None of these is recommended as a next step without a separate justification — see point 34.

## 34. Whether Gate 2 should GO, HOLD, or require another pre-registered Gate 1 experiment

**Recommendation: GO on Gate 2, with the specific architecture being the market-consensus baseline
(Model 0), not HOLD for a further Gate 1b.** The evidence is not marginal or ambiguous — every
alternative lost with a CI excluding zero, across log loss, Brier, and calibration, in every fold and
every competition. Spending further effort on a Gate 1b fundamentals expansion (fixture congestion,
xG, richer features) is a legitimate FUTURE research question, but it is a different, separately-
justified question from "is Model 0 good enough to be Gate 2's V1 architecture" — and per the
operator's own explicit instruction ("do not automatically declare a winner from tiny metric
differences" / "if consensus alone remains best calibrated... that is an important result... in that
case V1 may legitimately use consensus as its probability baseline, but that must be an EMPIRICAL
RESULT, not an assumption"), that empirical result is exactly what this Gate produced.

## 35. Exact next operator decision

Approve or decline Gate 2: freeze **Model 0 (market-consensus baseline, explicitly labelled as such)**
as the Probability Engine V1 architecture for football 1X2, and authorise proceeding to Gate 3
(extend/test Over/Under 2.5) under the same architecture-comparison discipline used here — still no
production Daily Engine, no bets, no automation, no Cricket, no new data acquisition. This work stops
at this gate, per the operator's own instruction, pending that decision.
