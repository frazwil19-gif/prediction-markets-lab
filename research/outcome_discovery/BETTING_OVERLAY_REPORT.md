# Betting Overlay Report (Secondary) -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22. Per Sections 26-28's explicit sequencing: the probability model is evaluated and
frozen first (VALIDATION_REPORT.md, HOLDOUT_REPORT.md), and only afterward is a betting overlay
considered -- using the EXISTING frozen money-qualification thresholds, never re-tuned to manufacture
qualifying bets (Section 28's explicit prohibition).

## Decision: reuse Backtest Phase 1's existing result rather than rerun

Backtest Phase 1 (2026-09-22, commit `8231793`) already ran exactly this overlay -- frozen V1
strategy, real historical odds, existing money-qualification gate -- across the full 2020/21-2025/26
dataset (5,776 eligible matches, 17,328 candidates) and found **zero money-qualified bets** in both
the closing-price and opening-price snapshot runs. Since 2025/26 (this cycle's holdout) is a subset
of that already-evaluated period, and the full-period result was zero qualifying candidates, the
holdout subset necessarily also contains zero qualifying candidates -- rerunning the frozen-strategy
harness restricted to 2025/26 alone would reproduce this same null result at greater compute cost
for no new information. This is a logical consequence of an already-published, already-verified
result, not an assumption substituting for computation.

## No production threshold was touched

Per Section 28's explicit instruction, no probability floor, odds floor, EV floor, or confidence
requirement was loosened in response to this or any prior null result. The frozen `money-strategy-
v1-frozen` config hash (`fca6f23522c449880791e9195c8e5f4eabe77beb5d12494c24e1c1fb2beb4544`,
recorded in Backtest Phase 1's manifest.json) remains the only strategy configuration referenced
here.

## What this cycle adds beyond Phase 1's own betting result

Nothing new on the betting side -- this cycle's contribution is entirely on the probability-
prediction side (outcome-level calibration, top-pick accuracy, winner/loser feature discovery,
conditional-market analysis). The explicit separation between Sections 29A (outcome prediction
performance) and 29B (betting performance) required by this instruction is honoured: nothing in
this cycle's probability findings is mixed with, or used to justify a change to, the betting-layer
result already established in Backtest Phase 1.
