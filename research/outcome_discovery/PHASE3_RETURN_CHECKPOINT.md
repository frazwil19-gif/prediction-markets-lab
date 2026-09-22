# Outcome Discovery & Winner/Loser Prediction -- Return Checkpoint

Date: 2026-09-22. This is the operator's second major research-direction instruction of the day
(the first, "PHASE 3 -- DATA EXPANSION & NEXT-MARKET RESEARCH DECISION," is recorded separately
under `research/data_expansion/` and the master directive's §24). To avoid confusion from both
instructions sharing the label "Phase 3," this cycle is referred to throughout its own files as the
**Outcome Discovery & Winner/Loser Prediction cycle**; this checkpoint keeps the exact filename the
instruction specified (`PHASE3_RETURN_CHECKPOINT.md`) but lives in its own directory
(`research/outcome_discovery/`), so nothing from the data-expansion checkpoint is overwritten or
confused with this one. Fraser/ChatGPT should read this as the fourth major research artefact
produced today, after Backtest Phase 1, Phase 2 (football probability model research), and the
data-expansion decision phase.

Answering the instruction's 40-point return checkpoint (Section 34):

**1. Matches analysed**: 5,631 (the same pooled out-of-sample match set Gate 1/Phase 2 already
validated -- reused, not re-collected).

**2. Outcome candidates analysed**: 16,893 (5,631 x 3, one per side per match).

**3. Winners vs losers count**: 5,631 winning candidates, 11,262 losing candidates (each match
contributes exactly one winner and two losers, by construction).

**4. Historical period**: 2020/21 through 2025/26 (6 seasons).

**5. Competitions**: E0 (Premier League), E1 (Championship), SC0 (Scottish Premiership).

**6. Features available**: 5 model architectures' probabilities (market, Elo+Poisson, fundamentals,
market+fundamentals, ensemble) for all 6 seasons; 11 engineered pre-match features (Elo gap, and
5-/10-match rolling goals/shots/SOT/corners/cards/points-per-game diffs) for 5 of 6 seasons
(2020/21-2024/25 only -- see point 35).

**7. Leakage audit result**: no leakage found (LEAKAGE_AUDIT.md) -- no new feature computation or
model fit was performed in this cycle; every input was read verbatim from already-audited files.

**8. Chronological discovery/validation/holdout split**: DISCOVERY 2020/21-2022/23 (6,753
candidates), VALIDATION 2023/24-2024/25 (6,750 candidates), HOLDOUT 2025/26 (3,390 candidates).
Explicitly flagged as not a fully blind holdout relative to prior research's aggregate metrics
(DATASET_AUDIT.md) -- genuinely new here only for the winner/loser feature relationships this cycle
mines, which have not been extracted or reported before.

**9. Strongest winner-vs-loser differences (discovery)**: `elo_gap` (Cohen's d = 0.6321),
`diff_shots_for_last10` (0.5366), `diff_sot_for_last10` (0.5318), `diff_corners_for_last10`
(0.5075) -- winners systematically have higher pre-match Elo and rolling attacking-output
advantages than losers. Full table: WINNER_LOSER_ANALYSIS.csv.

**10. Whether those differences survived validation**: yes, all 11 features replicated with closely
matching effect sizes and identical sign (FEATURE_STABILITY.csv, VALIDATION_REPORT.md) -- but see
point 24: this raw replication is expected and does not by itself indicate information beyond the
market.

**11. Favourite winner-vs-loser findings**: favourites (n=5,101 home/away favourites, excluding 530
matches where the market's own top pick was itself a draw) won 2,920 times (57.24%) and lost 2,711
times. Favourites that won had a materially larger average Elo advantage (105.16) than favourites
that lost (70.49, Cohen's d = 0.3258) -- i.e. "stronger" favourites (by underlying stats) win more
often than "weaker" favourites, an intuitive and expected pattern. FAVOURITE_WIN_LOSS_ANALYSIS.csv.

**12. Underdog findings**: underdogs won 1,317 of 5,631 matches (23.39%) -- close to the base rate
implied by their lower market probability. Winning underdogs had a smaller average deficit
(elo_gap -65.01) than losing underdogs (-95.71, Cohen's d = 0.2865) -- weaker underdogs lose more
often than stronger underdogs, again an expected, not surprising, pattern.
UNDERDOG_ANALYSIS.csv.

**13. Draw findings**: draws occurred in 1,394 of 5,631 matches (24.76%). Draw candidates that
occurred had smaller absolute pre-match gaps (closer matches) than draw candidates that did not,
but with small effect sizes (Cohen's d 0.04-0.18 across the 11 features, versus 0.4-0.65 for
home/away winner-vs-loser comparisons) -- a real but much weaker signal. DRAW_ANALYSIS.csv.

**14. Conditional-market findings** (Section 24, the cycle's central test): within the 50-65%
market-probability band, **every one of the 11 features has |Cohen's d| below 0.12** on discovery
data (versus 0.4-0.65 unconditionally) -- essentially no residual winner/loser separation once
market probability is held roughly constant. CONDITIONAL_MARKET_ANALYSIS.csv (all three
partitions).

**15. Stable predictive variables**: all 11 examined features are unconditionally STABLE
(discovery-validation) in raw effect size and direction -- but NONE demonstrated conditional
(market-adjusted) predictive value in the one band tested. "Stable but not incrementally useful
beyond market" is the correct characterisation, not "no stable variables exist."

**16. Rejected/unstable variables**: none of the 11 features were rejected as unstable in the raw
sense (all replicated); all 11 are effectively rejected as SOURCES OF NEW INFORMATION once
conditioned on market probability (point 14).

**17. Models tested**: none newly fit in this cycle -- the 5 already-existing, already-validated
Gate 1 architectures were reused (Model A market, Model B fundamentals, Model C market+
fundamentals, Model D Elo+Poisson, plus the calibrated ensemble).

**18. Market-only predictive performance**: top-pick accuracy 51.86% pooled (52.42% discovery,
52.89% validation, 48.67% holdout); log loss 0.98726, Brier 0.58877 (Gate 1's published pooled
figures, reused, not recomputed).

**19. Historical-data-only (fundamentals) predictive performance**: top-pick accuracy 49.53% pooled
(49.84% discovery, 50.09% validation, 47.79% holdout) -- lower than market throughout; log loss
1.01572, Brier 0.60756 (Gate 1's published figures).

**20. Combined market+historical predictive performance**: top-pick accuracy 51.27% pooled --
between fundamentals-only and pure market, still below pure market; log loss 0.99225, Brier 0.59170
(Gate 1's published figures).

**21. Best supported probability model**: market consensus alone (Model A), on every metric
computed in this cycle (top-pick accuracy) and every metric Gate 1 already published (log loss,
Brier, calibration) -- consistent across discovery, validation, and (with the caveat in point 24 of
this cycle's HOLDOUT_REPORT.md) holdout.

**22. Top-pick accuracy**: market 51.86% pooled (5,631 matches) -- see MODEL_COMPARISON.csv for the
full per-model, per-partition breakdown.

**23. Brier score**: 0.58877 (market, Gate 1's published pooled figure -- not recomputed in this
cycle, reused per this project's "don't repeat exhausted research" discipline).

**24. Log loss**: 0.98726 (market, Gate 1's published pooled figure).

**25. Calibration**: market's calibration error stays within +/-4.3 percentage points across every
probability band from <30% to 80%+ (PROBABILITY_BANDS.csv); fundamentals' calibration error reaches
-3.87pp at 70-79.9% -- consistent with, and extending via a below-50% band this project had not
previously tabulated, Gate 1 and Phase 2's calibration findings.

**26. Actual win rates by predicted-probability band**: full table in PROBABILITY_BANDS.csv,
covering all 9 bands from <30% to 80%+, for both market and fundamentals -- the first time this
project has tabulated the below-50% bands (Phase 2's disagreement/high-probability analysis started
at 50%).

**27. High-probability prediction performance**: at 80%+, market's actual win rate is 88.0% against
a mean predicted 83.7% (a positive 4.3pp calibration error, i.e. slightly under-confident, not
over-confident) -- consistent with the 20 largest misses (ERROR_ANALYSIS.md) all falling within the
range good calibration would predict.

**28. Uncertainty findings**: no new uncertainty measure was fabricated (per Section 20's explicit
prohibition on an arbitrary confidence score). Sample-size-driven uncertainty is visible directly in
the probability-band tables (n ranges from 134 to 9,217 across bands) and in the holdout's smaller
sample (1,130 matches) plausibly explaining some of its accuracy dip (HOLDOUT_REPORT.md) -- stated
as a candidate explanation, not confirmed via a formal interval.

**29. Common characteristics of incorrect predictions**: the 20 highest-confidence market misses are
disproportionately Scottish Premiership matches (14/20) and disproportionately resolve as draws
(13/20) rather than outright reversals -- both reported as hypotheses for possible future
investigation, not acted on (ERROR_ANALYSIS.md).

**30. Sealed-holdout result**: not a fully blind confirmation (point 8's caveat) -- available
metrics (top-pick accuracy) show the same model ranking as discovery/validation (market and
ensemble best) but a several-point accuracy decline for every model, not distinguished here between
sampling noise and genuine drift (HOLDOUT_REPORT.md). The engineered-feature winner/loser analysis
could not be evaluated on holdout at all (data-coverage gap, point 35).

**31. Whether a new probability model is justified**: no. Market consensus remains the strongest
available estimator on every metric examined, in this cycle and every prior one this project has
run (Gate 1, Backtest Phase 1, Phase 2).

**32. Secondary betting-overlay result**: zero money-qualified bets, reusing Backtest Phase 1's
already-published full-period result rather than rerunning it on the holdout subset alone
(BETTING_OVERLAY_REPORT.md) -- a logical consequence of an already-verified null result, not a new
computation.

**33. Money-qualified bets on untouched holdout**: zero (see point 32 -- the holdout period is a
subset of Phase 1's already-evaluated full period, which itself had zero qualified bets).

**34. P&L/ROI**: not applicable -- zero qualified bets produces no P&L to report, consistent with
this project's "No-Bet Day is a valid, expected output" convention.

**35. Limitations**: (a) the 2025/26 season has no engineered-feature join available in the current
pipeline, blocking the deepest winner/loser analysis on the true holdout season; (b) the
discovery/validation/holdout split is not a fully blind confirmation relative to prior research's
own aggregate metrics (point 8); (c) the conditional-market analysis was run for one band
(50-65%) as a proof of the method, not exhaustively across every band; (d) no formal
significance/CI test was run on the holdout accuracy decline (point 30) -- a real limitation for
distinguishing noise from drift.

**36. Tests passed**: 957/957 (940 carried over from Phase 3's data-expansion cycle + 17 new,
covering candidate-label correctness, signed-feature orientation, chronological partitioning,
Cohen's d edge cases, probability-band bucketing, top-pick accuracy, favourite/underdog/draw logic,
conditional-market restriction, and -- specifically -- the discovery-vs-validation stability verdict
bug this cycle caught and fixed in itself before publication). No existing test was weakened.

**37. Files created/changed**: `src/prediction_markets_lab/research/outcome_discovery_analysis.py`
(new, pure functions), `scripts/run_outcome_discovery_analysis.py` (new, orchestration),
`tests/unit/test_outcome_discovery_analysis.py` (new, 17 tests), and the full
`research/outcome_discovery/` package (this checkpoint plus DATASET_AUDIT.md, LEAKAGE_AUDIT.md,
OUTCOME_DATASET_SCHEMA.md, WINNER_LOSER_ANALYSIS.csv, FAVOURITE_WIN_LOSS_ANALYSIS.csv,
UNDERDOG_ANALYSIS.csv, DRAW_ANALYSIS.csv, CONDITIONAL_MARKET_ANALYSIS.csv, FEATURE_STABILITY.csv,
MODEL_COMPARISON.csv, CALIBRATION.csv, PROBABILITY_BANDS.csv, ERROR_ANALYSIS.md,
VALIDATION_REPORT.md, HOLDOUT_REPORT.md, BETTING_OVERLAY_REPORT.md, analysis_summary.json). No
production file was read or written.

**38. Commit hash**: pending -- committed immediately after this checkpoint is written (see below).

**39. Production impact**: none. No file under `decisions/`, `config/`, `scripts/run_daily_scan.py`,
any GitHub Actions workflow, or any paper/real ledger was touched. The live daily scanner and paper
ledger continued running unattended throughout.

**40. Exact recommended next research step**: no new model is justified for football 1X2 (this
question is now EXHAUSTED across four independent lenses this project has run: Gate 1's architecture
comparison, Backtest Phase 1's money-qualification backtest, Phase 2's disagreement/high-probability
diagnostics, and this cycle's winner/loser/conditional-market discovery). Two legitimate, not-yet-
actioned options: (a) extend `cycle_002_discovery_features.csv`'s engineered-feature pipeline to
cover 2025/26 (and future seasons as they complete), closing the specific data gap this cycle hit,
so a genuine holdout-covered winner/loser analysis becomes possible; (b) per the earlier data-
expansion decision phase (`research/data_expansion/PHASE3_RETURN_CHECKPOINT.md`), apply this exact
winner/loser discovery methodology to a genuinely open market/sport -- Tennis Match Winner money-
qualification (using the already-downloaded Betfair archive) remains the strongest-evidenced
candidate for that.

## Decision classification (Section 35)

**B -- Market consensus alone remains the strongest predictor.** No historical or contextual
variable examined in this cycle demonstrated validated incremental predictive value once conditioned
on market probability, on any of the metrics this project's scientific-method discipline recognises
(top-pick accuracy here; log loss, Brier, and calibration already established by Gate 1). This is
consistent with, and adds new evidence for, every prior finding this project has produced on
football 1X2 -- not a new or contradictory result.

## Permanent principle (Section 36) -- reaffirmed, not modified

This cycle's own findings are fully consistent with the sequence Section 36 describes: outcome
probability was estimated and evaluated in full (Sections 1-25 of this checkpoint) before any
betting-value question was asked (Sections 26-34), and the betting layer's answer (zero qualified
bets, reusing an already-verified result) did not feed back into or change the probability findings
above. No threshold was loosened, no model was modified based on individual anecdotes, and no new
sport research cycle was started in producing this checkpoint.
