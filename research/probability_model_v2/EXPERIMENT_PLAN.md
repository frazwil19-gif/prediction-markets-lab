# Phase 2 Experiment Plan (Sections 5-11) -- Reusing, Not Re-Running, Gate 1

**Written 2026-09-22.** Documents how this phase's model-family, target, and chronological-design
requirements map onto work already done, and exactly what new work this phase adds on top of it.

## Model families (Section 5) -- already built and separated, not blurred

| Instruction's family | What already exists | Where |
|---|---|---|
| Model A -- market only | De-vigged multi-bookmaker closing consensus, explicitly labelled `market_consensus_baseline_probability` in production | `probability/market_pipeline.py`, `probability/consensus.py`; Gate 1's "Model 0" |
| Model B -- fundamentals only, no bookmaker odds as predictors | 9-feature multinomial logistic regression (Elo gap + 5 rolling stat differentials + points-per-game differential + 2 competition dummies), fitted per fold on training seasons only, zero market inputs | `models/multinomial_logistic_regression.py`; Gate 1's "Model 2" |
| Model C -- market + fundamentals | Model B's 9 features plus two market-derived logit features, same regression class | Gate 1's "Model 3"; a separate calibrated linear blend of Model A and Model B also exists as Gate 1's "Model 4" |
| Model D -- existing Elo/Poisson benchmark | The production-frozen Elo+Poisson blend, reproducible via a continuous leakage-safe replay | `models/football_elo.py`, `models/football_poisson.py`, `models/football_blended.py`; Gate 1's "Model 1" |

These four families were never blurred in Gate 1's own construction (each is evaluated separately,
per fold, on an identical eligible sample) and remain unblurred here.

## Target (Section 6)

Confirmed: every model above is trained and evaluated against the actual match outcome (home/draw/
away), via `full_time_result`, never against bookmaker odds, EV, or historical bet profitability.
Log loss and Brier score (the metrics Section 11 asks for) are themselves defined against the
realised outcome, not against money. No target-leakage risk was found or introduced.

## Chronological design and the sealed-holdout question (Section 7)

Gate 1 used 5 **expanding-window walk-forward folds** (train on all seasons up to and including
season *i*, evaluate on season *i+1*), covering 2020/21 through 2025/26. This is a legitimate
chronological-OOS design and is NOT a random split. However, it is **not** the
development -> validation -> sealed-holdout structure Section 7 explicitly asks for, and Gate 1's own
checkpoint says so plainly (point 2): every one of the six seasons used had already been "exposed" to
some earlier stage of this project's research (Stage 3B's development folds, Stage 3B's own 2024/25
holdout, or H-FB2-002's 2025/26 sealed-OOS test) before Gate 1 ran. **No period in the historical
record used here is a genuine, never-before-inspected holdout for THIS SPECIFIC question** (can
fundamentals features improve on market consensus for 1X2).

Manufacturing an artificial "sealed holdout" by carving out one of Gate 1's already-evaluated seasons
and re-presenting it as pristine would misrepresent the actual epistemic status of that data -- exactly
the kind of dishonesty the project's scientific-method discipline (master directive §7) exists to
prevent ("chronological validation only," "final holdout stays untouched during development"). The
honest position, already stated by Gate 1 itself and reaffirmed here: **the only genuine, never-yet-
inspected holdout for this question is the current, still-in-progress 2026/27 season**, which has not
been acquired, downloaded, or looked at by any script in this repository. Once it has accumulated
enough matches to be meaningful, it is the correct place to prospectively validate whatever
architecture conclusion this phase reaches -- not a re-partition of already-seen 2020/21-2025/26 data.

This phase therefore does NOT construct a new dev/validation/sealed-holdout split over historical
data. It instead (a) treats Gate 1's walk-forward result as already-adequate chronological evidence
for the historical comparison, and (b) explicitly names 2026/27 as the pending genuine holdout for a
future prospective check -- consistent with Gate 1's own stated position, not a new invention.

## What Sections 8-11 (leakage, model research, market+fundamentals, metrics) already have answers

Every leakage check (Section 8), the actual models fitted (Section 9), the market+fundamentals
combination test (Section 10), and the metrics comparison with uncertainty (Section 11) were already
executed in Gate 1 with a full pre-registered protocol, bootstrap CIs on every delta vs market, and a
result that **excludes zero in every single comparison** -- not a marginal or ambiguous case that
would benefit from a second, differently-parameterised attempt. Re-running the identical comparison
with the identical features and calling it "Phase 2" would be exactly the "repeated retesting until
something passes" pattern the project's own method explicitly forbids, so it was not done. Instead,
`scripts/run_gate1_1x2_probability_architecture_comparison.py` was extended (additively, off by
default) to also export its already-computed per-match, per-model out-of-sample predictions, and that
export is what powers the two genuinely new analyses in this phase -- see
`PHASE2_RETURN_CHECKPOINT.md` Sections 13 and 15.

## What this phase adds that Gate 1 did not

1. Section 2's independent verification of the Phase 1 backtest result, with one documentation
   correction (`PHASE1_INDEPENDENT_VERIFICATION.md`).
2. Section 4's feature inventory, itemising exactly what is available-but-unused vs genuinely absent
   (`DATA_AUDIT.md`).
3. Section 13's high-probability-region reliability breakdown and Section 15's disagreement-band
   analysis, computed from Gate 1's exact frozen models' per-match predictions (new module
   `research/probability_model_v2_diagnostics.py`, new script
   `scripts/run_probability_model_v2_diagnostics.py`, outputs `high_probability_analysis.csv` /
   `disagreement_analysis.csv`).
4. Section 18's live-data feasibility note for the fundamentals feature set specifically
   (`live_data_feasibility.md`).
5. The explicit decision-rule application (Section 24) and the full 25-point return checkpoint
   (`PHASE2_RETURN_CHECKPOINT.md`).

Sections 17 (nominate a V2 candidate) and 19 (optional betting simulation after model freeze) are
explicitly NOT actioned, because their own trigger condition -- a model that beats or usefully
complements market consensus -- was not met. See `PHASE2_RETURN_CHECKPOINT.md` point 19.
