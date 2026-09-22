# Phase 2 Return Checkpoint -- Independent Football Probability Model Research

**Written 2026-09-22.** Answers the operator's "PHASE 2 -- INDEPENDENT FOOTBALL PROBABILITY MODEL
RESEARCH" instruction (relayed by Fraser immediately after Backtest Phase 1) in full, in the order of
its own Section 23 return-checkpoint list. Supporting documents:
`PHASE1_INDEPENDENT_VERIFICATION.md`, `DATA_AUDIT.md`, `EXPERIMENT_PLAN.md`, `LEAKAGE_AUDIT.md`,
`live_data_feasibility.md`, `high_probability_analysis.csv`, `disagreement_analysis.csv`,
`per_match_predictions_gate1_reproduction.csv`.

**Headline finding, stated up front per this phase's own Section 25 ("do not respond by making
betting easier / improve the information first"): market consensus remains the best available 1X2
probability estimator. This is not a new conclusion -- Gate 1 (master directive §15, 2026-09-18)
already reached it with a pre-registered, chronologically-walk-forward-validated, bootstrap-CI-backed
comparison across four alternative architectures. This phase independently re-verified that result,
extended it with the specific granular diagnostics (high-probability-region reliability, disagreement-
band analysis) this instruction newly asked for, and found nothing in that closer look that overturns
it -- if anything, the disagreement-band analysis makes the case more starkly than Gate 1's pooled
log-loss table alone did (see point 15 below).**

---

## 1-2. Phase 1 result independently verified; closest-miss diagnosed

Fully independent re-derivation from the raw `backtests/money-strategy-v1-frozen/*/predictions.csv`
files, not from prose. Confirmed: 5,776 matches, 17,328 candidates, zero money-qualified bets in both
snapshots, matching config hash, and no implementation bug. One documentation-clarity correction was
found and recorded: the previously reported "closest miss" (Motherwell v Celtic, Celtic to win at
68.6% probability / odds 1.53, net EV 4.99% vs a 5.00% floor) is a **Medium**-confidence candidate
that failed the Medium-confidence net-EV floor specifically, not a High-confidence candidate as the
Phase 1 write-up's phrasing implied. Full detail, including the exact gate-by-gate trace:
`PHASE1_INDEPENDENT_VERIFICATION.md`.

## 3-4. Independent features available; historical coverage

Full inventory in `DATA_AUDIT.md`. Available and already tested: Elo, Poisson, and 9 leakage-safe
rolling fundamentals features (goals/shots/SOT/corners/cards differentials over a last-10 window, plus
points-per-game differential and competition dummies), covering all 6,960 raw E0/E1/SC0 matches
2020/21-2025/26 (6,503 eligible after requiring a full 10-match history and a >=4-bookmaker closing
consensus). Available but unused by any test so far: home/away-context-specific rolling windows, the
last-5 window, conversion rate, goal-diff volatility. Genuinely unavailable without new acquisition:
xG, rest-days/fixture-congestion, promoted-team status, explicit league-position, referee-level
historical statistics, Dixon-Coles scoreline correlation.

## 5. Leakage audit

`LEAKAGE_AUDIT.md`. No new leakage risk found or introduced; every reused feature's leakage-safety was
already mechanically tested by Gate 1's own modules, and the new diagnostic code operates only on
already-computed, already-out-of-sample predictions.

## 6. Chronological split

Gate 1's existing 5-fold expanding walk-forward (2020/21 train-only through 2025/26 final eval season)
is reused. A genuinely new dev/validation/sealed-holdout partition of the SAME historical data was
deliberately NOT constructed, because every season in that span was already exposed to earlier stages
of this project's research -- see `EXPERIMENT_PLAN.md`'s chronological-design section for why
manufacturing an artificial "sealed" holdout from already-inspected data would misrepresent the
result, and why the current 2026/27 season is the correct, still-pending genuine holdout for this
question.

## 7. Models tested

Model A (market consensus), Model B (9-feature fundamentals-only multinomial logistic regression),
Model C (market + fundamentals, both a regression variant and a calibrated linear-blend variant), and
Model D (existing Elo+Poisson blend) -- all four, walk-forward validated, per Gate 1. See
`EXPERIMENT_PLAN.md` for the family-by-family mapping and why they were not re-fitted from scratch.

## 8-11. Performance by architecture (pooled, 5,631 out-of-sample matches)

| Architecture | Log loss | Brier | Δ vs market (95% CI) |
|---|---|---|---|
| Market consensus (A) | 0.98726 | 0.58877 | -- baseline |
| Fundamentals only (B) | 1.01572 | 0.60756 | +0.0285 [+0.0229, +0.0340] -- excludes zero, worse |
| Elo+Poisson (D) | 1.01085 | 0.60482 | +0.0236 [+0.0183, +0.0286] -- excludes zero, worse |
| Market + fundamentals (C, regression) | 0.99225 | 0.59170 | +0.0050 [+0.0021, +0.0080] -- excludes zero, worse |
| Market + fundamentals (C, calibrated ensemble) | 0.98981 | 0.59048 | +0.0026 [+0.0010, +0.0041] -- excludes zero, worse |

Every alternative to market consensus is worse, with every 95% CI excluding zero. Independently
recomputed in this phase (not copied from Gate 1's JSON) via the additive per-match CSV export, and
matched Gate 1's published figures to within 5e-6 in every case -- see the self-verification step
built into `scripts/run_probability_model_v2_diagnostics.py`.

## 12. Calibration results

Reused from Gate 1 unchanged (draw calibration is the weak point: market's draw slope 1.005 vs
fundamentals' 0.604, market+fundamentals inherits 0.662) -- see master directive §15 / GATE1_CHECKPOINT.md
point 20 for the full per-outcome table. Not recomputed here since Gate 1's own reproduction already
confirmed byte-level fidelity to that computation.

## 13. High-probability calibration (NEW this phase)

Computed via `high_probability_region_report` on the fundamentals-only model's own >=50%-probability
candidates, compared against the market's probability for the same (match, outcome):

| Band | n | Mean predicted | Actual win rate | Calibration error | Mean market prob | Diff from market |
|---|---|---|---|---|---|---|
| 50-54.9% | 751 | 52.4% | 48.7% | 3.6pp | 49.4% | +3.0pp |
| 55-59.9% | 548 | 57.4% | 56.8% | 0.6pp | 55.1% | +2.3pp |
| 60-64.9% | 425 | 62.3% | 60.7% | 1.6pp | 60.6% | +1.8pp |
| 65-69.9% | 298 | 67.3% | 68.5% | 1.2pp | 65.2% | +2.0pp |
| 70-79.9% | 338 | 74.3% | 70.4% | 3.9pp | 72.9% | +1.4pp |
| 80%+ | 134 | 84.3% | 87.3% | 3.0pp | 82.1% | +2.3pp |

The fundamentals model's high-probability predictions are not wildly miscalibrated in isolation
(errors mostly 1-4pp on samples of a few hundred), but it is **consistently 1.4-3.0 percentage points
more confident than the market in every single band** -- i.e. it systematically overstates probability
in exactly the region the money-qualification gate cares about, relative to a market that is itself
better calibrated overall (Gate 1 point 20). Full table for all four non-market architectures:
`high_probability_analysis.csv`.

## 14. Betting-threshold optimisation

Not performed, per the instruction's explicit Section 14 prohibition. No probability floor, odds
floor, EV floor, or confidence floor was searched or adjusted in this phase.

## 15. Disagreement analysis (NEW this phase)

Computed via `disagreement_band_report`, bucketing every (match, outcome) candidate by
(fundamentals-model probability − market probability) and comparing each side's calibration error
within that band, across the same 5,631 x 3 = 16,893 candidate rows:

| Disagreement band | n | Model calib. error | Market calib. error |
|---|---|---|---|
| Model ≤ market − 20pp | 125 | 33.3pp | 8.9pp |
| Model 10-20pp below market | 918 | 15.1pp | 1.9pp |
| Model 5-10pp below market | 2,231 | 7.3pp | 0.3pp |
| Model within ±5pp of market | 10,150 | 0.5pp | 0.2pp |
| Model 5-10pp above market | 2,225 | 8.4pp | 1.2pp |
| Model 10-20pp above market | 1,113 | 15.3pp | 1.9pp |
| Model ≥ market + 20pp | 131 | 25.8pp | 1.5pp |

**This is the single clearest result in this phase.** In every band where the fundamentals model
disagrees with the market by more than 5 percentage points, the market's calibration error stays
under 2 percentage points while the fundamentals model's grows to 7-33 percentage points -- and the
size of the market's advantage grows with the size of the disagreement. Disagreement between the
fundamentals model and the market is not prospectively informative in the fundamentals model's favour
at any magnitude tested; it is consistently informative in the MARKET's favour. The calibrated
ensemble (Model C) shows the same pattern far more mutedly, exactly as expected given its own training
weight search already converges toward ~100% market weight (Gate 1 point 27). Full table for all four
non-market architectures, all seven bands: `disagreement_analysis.csv`.

## 16. Model uncertainty findings

No new statistical-uncertainty measure was built beyond what Gate 1 already provides (bootstrap CIs
on pooled metric deltas). Per this instruction's own Section 16 caution against fabricating a
confidence score, and given that the headline result here is a clean, high-confidence negative
finding rather than a close call needing finer uncertainty resolution, no ensemble-dispersion or
per-prediction uncertainty measure was constructed. Production's existing "confidence" label
(High/Medium/Low, from `decisions/confidence.py`) remains what it already was documented to be --
mechanical data-quality/liquidity confidence, not a statistical measure of a probability's own
precision -- and this phase did not conflate the two.

## 17. Whether independent information adds predictive value

**No.** Fundamentals-only is the single worst architecture tested; adding fundamentals to market
consensus makes the result measurably worse, not better; and the new disagreement-band analysis shows
this holds at every magnitude of disagreement, not just on average.

## 18. Best probability estimator supported by evidence

Market consensus (Model A / Model 0), unchanged from Gate 1's conclusion and production's current
architecture. No change to production is proposed or required.

## 19. Whether a V2 research candidate exists

**No.** Per the instruction's Section 17 ("only if an independent or blended model demonstrates
credible chronological OOS performance") and its own Section 25 ("do not manufacture a V2 model
because the project expects progress"), no candidate is nominated. This is Decision Rule A (Section
24), stated plainly rather than forced into a manufactured B or C.

## 20. Live-data requirements for that candidate

N/A -- no candidate exists. For the record, `live_data_feasibility.md` notes that the score/result
side of a live fundamentals pipeline is plausibly feasible (an existing settlement adapter already
covers it) while the shots/SOT/corners/cards side has no live source currently integrated anywhere in
this repository and was not investigated further, since no model needs it.

## 21. Frozen-holdout betting simulation using unchanged V1 money rules

**Not run**, per the instruction's own Section 19 gate ("only after, and only if, a probability model
is selected and frozen using development/validation evidence"). No model was selected. Running Phase
1's money-qualification backtest a second time with a different probability source, when that source
has already been shown to be worse-calibrated and worse-disagreeing than market, would not be a
meaningful test and was correctly not performed.

## 22. Money-qualified bet count / betting performance

N/A -- no new simulation was run (see point 21). Phase 1's own result (zero, both snapshots) remains
the only backtest evidence and is unchanged by this phase.

## 23. Limitations

(a) The high-probability and disagreement diagnostics are a closer slice of the SAME pooled
out-of-sample evidence Gate 1 already used, not an independent replication -- see `LEAKAGE_AUDIT.md`'s
residual-risk note. (b) No genuinely pristine historical holdout exists for this exact question; the
real one (2026/27) has not yet accumulated enough matches. (c) Gate 1's fundamentals feature set,
while leakage-safe and reasonably rich, is not exhaustive -- xG, rest days, and referee history remain
untested, so this phase's conclusion is "the specific 9 features tested do not help," not "no
conceivable independent feature set could ever help." (d) The draw outcome's calibration weakness in
every non-market architecture was not investigated further (e.g. a dedicated draw-probability
adjustment) -- flagged as a legitimate separate future question, not attempted here.

## 24. Tests passing

940/940 (927 before this phase's changes + 13 new, `tests/unit/test_probability_model_v2_diagnostics.py`).
No existing test was weakened or modified.

## 25. Files changed

New: `src/prediction_markets_lab/research/probability_model_v2_diagnostics.py`,
`tests/unit/test_probability_model_v2_diagnostics.py`,
`scripts/run_probability_model_v2_diagnostics.py`,
`research/probability_model_v2/{DATA_AUDIT.md, EXPERIMENT_PLAN.md, LEAKAGE_AUDIT.md,
PHASE1_INDEPENDENT_VERIFICATION.md, PHASE2_RETURN_CHECKPOINT.md, live_data_feasibility.md,
high_probability_analysis.csv, disagreement_analysis.csv,
per_match_predictions_gate1_reproduction.csv}`. Modified, additively only:
`scripts/run_gate1_1x2_probability_architecture_comparison.py` (a new, off-by-default per-match CSV
export appended after its existing output-writing step; verified byte-level-equivalent behaviour when
the new environment variable is unset, and exact numerical reproduction of its own published figures
when it is set). No production file (`decisions/`, `config/thresholds.yaml`, `config/bankroll.yaml`,
`scripts/run_daily_scan.py`, any GitHub Actions workflow, any paper/real ledger) was touched.

## 26. Commit hash

Recorded once committed -- see the master research directive's own next entry for the exact hash,
following this project's established provenance convention (protocol/audit documents committed before
or alongside results, never edited retroactively to match a result).

## 27. Exact recommended next step

**No change to production.** Two legitimate, separately-justified FUTURE options exist and neither is
recommended for immediate action: (a) a Gate 1b research effort testing the currently-unused-but-
available feature slices (home/away-context windows, last-5 window, conversion rate, goal-diff
volatility) or a genuinely new feature family (xG, rest days, referee history) against market
consensus, under the same pre-registered walk-forward discipline; (b) waiting for the 2026/27 season
to accumulate enough matches to serve as a genuine prospective check of Gate 1's conclusion, rather
than re-partitioning already-seen data. Neither requires any code change today. The live daily
scanner, paper ledger, and money-qualification gate all continue running unattended and unmodified, as
the operator's own instruction requested ("don't stop the live system").

---

## Decision rule applied (Section 24)

**A. Market consensus remains best.** Independent information (the 9 fundamentals features tested)
adds no reliable OOS value -- confirmed by Gate 1's original pooled-metric/bootstrap-CI comparison and
reaffirmed, more granularly, by this phase's high-probability-region and disagreement-band analyses,
which found the market's calibration advantage widens rather than narrows as disagreement grows.

## Final principle (Section 25)

This phase did not respond to Phase 1's null betting result by loosening any threshold, and did not
respond to this phase's own null modelling result by manufacturing a V2 candidate to show progress.
Both null results are recorded as information, not failure, per the operator's own stated principle,
and the live production system was not touched.
