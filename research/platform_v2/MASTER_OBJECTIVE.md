# Platform V2 — Master Objective (locked 2026-09-23)

Source: Fraser/ChatGPT "MASTER DIRECTIVE — PREDICTION MARKETS PLATFORM V2". This file restates it as the project's
permanent objective. It supersedes any wording that treats "beating the market" as the primary research goal
(master directive §1 was already marked superseded by §14/§16; nothing is deleted).

## Objective
A **multi-sport statistical outcome-prediction and bet-selection platform**.

1. Primary question: *across today's events and markets, which outcomes have the strongest statistically
   defensible probability of occurring?*
2. Secondary question: *of those, which available bets pay enough relative to probability, uncertainty and risk?*

## Locked hierarchy
Outcome prediction → estimated probability → statistical support → uncertainty → current context → available odds →
payout/value → risk → stake → BET / NO BET.

## Three layers
- **A. Probability Engine.** What is P(outcome)? Returns P, fair odds, uncertainty, support, calibration evidence,
  model/version. `PROBABILITY_ENGINE_SPEC.md`.
- **B. Bet-Selection Engine.** Is this price worth the risk? Returns BET / WATCH / PAPER_ONLY / REJECT.
  `BET_SELECTION_SPEC.md`.
- **C. Portfolio / Multi Engine.** How should valid selections be staked or combined? Singles by default, multis
  optional and gated. `MULTI_ENGINE_SPEC.md`.

## Principles carried forward
- The best validated probability estimator wins. Market consensus, historical data, or a combination are all
  acceptable. Not beating the market is not a failure.
- Probability quality is judged on unseen data (log loss, Brier, calibration, band reliability, stability), never on ROI.
- Anti-leakage, discovery → validation → freeze → sealed holdout, and null results are preserved.
- A strong prediction can still be a poor bet. That doesn't invalidate the prediction.
- Multis are a packaging tool for independently valid legs. They are never a way to rescue weak ones.
- Scale through breadth (more validated sports/markets), never through lower standards. No daily quota.

## One economic fact every layer must respect (recorded so it is never lost)
A multi does not create value. Its expected return is the **product** of the legs' (P × odds) ratios. If the
probability engine is market consensus, a typical leg has P × odds ≈ 1 − margin, so every extra leg compounds the
margin. For example, three legs at 0.97 each give 0.97³ = 0.913, an expected loss of 8.7%. The worked example in
the directive (85%@1.18, 82%@1.22, 80%@1.25) has leg ratios of 1.003, 1.000 and 1.000, so the multi's expected return is ≈ +0.3%:
larger payout, same near-zero edge, and much higher variance. **Multis only make sense when every leg already
clears value against an independent reference (see the Phase 5 consensus/price note).** The Multi Engine spec
enforces this.
