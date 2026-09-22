# Validation Report -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22. Covers whether relationships mined on DISCOVERY seasons (2020/21-2022/23)
replicate on VALIDATION seasons (2023/24-2024/25), per Section 12's discipline (discovery data may
be explored; validation tests what was discovered).

## Winner/loser feature replication

Every one of the 11 signed engineered features examined (Elo gap, rolling goals/shots/SOT/corners/
cards-for diffs at both 5- and 10-match windows, points-per-game diffs) showed a **remarkably
consistent effect size between discovery and validation** -- full table: FEATURE_STABILITY.csv.
Example: `elo_gap`'s Cohen's d was 0.6321 in discovery and 0.6544 in validation; `diff_shots_for_
last10` was 0.5366 in discovery and 0.5743 in validation. All 11 features are classified **STABLE
(discovery-validation)** -- same sign, both magnitudes above a minimal 0.03 threshold, in both
partitions.

**What this does and does not mean.** This confirms that home/away candidates that go on to win
really do, systematically and reproducibly, have higher pre-match Elo/rolling-form advantages than
the candidates that lose -- a real, stable, replicated pattern. It does **not** by itself mean this
information is useful for beating the market, because the market's own probability is built
substantially from the same underlying strength signal. The critical test is CONDITIONAL_MARKET_
ANALYSIS.csv: within a narrow band of market-estimated probability (50-65%, i.e. candidates the
market already considers roughly evenly matched-to-moderately-favoured), do these same features
still separate winners from losers?

**Answer: no, not usefully.** Within that band, on discovery-season data, every one of the 11
features has |Cohen's d| below 0.12 (versus 0.4-0.65 unconditionally) -- effectively no residual
discriminative power once market probability is held roughly constant. This is the central,
correctly-designed finding of this cycle: the large raw winner/loser differences are almost
entirely explained by exactly what the market is already pricing, not by information the market is
missing.

## Top-pick accuracy replication

Market top-pick accuracy was 52.42% in discovery and 52.89% in validation (MODEL_COMPARISON.csv) --
consistent, no meaningful drift. Every alternative architecture (fundamentals, Elo+Poisson,
market+fundamentals, ensemble) scored lower than pure market in both partitions, replicating Gate
1's original finding via a new metric this cycle introduced (top-pick accuracy was never computed
in Gate 1, which reported only log loss/Brier/calibration).

## Decision rule check (Section 24/25 framing)

Per this cycle's own decision criteria: market consensus remains the strongest predictor by every
metric computed here (top-pick accuracy, and -- per Gate 1's already-published figures -- log loss
and Brier score), and no historical/contextual variable, once conditioned on market probability,
demonstrated validated incremental predictive value. This is Decision Option B (market consensus
alone remains the strongest predictor), not a failed experiment -- exactly the outcome the
instruction's own framing anticipated as acceptable.
