# V2-6 Staking and Paper Bankroll Framework (pre-registered 2026-09-29)

Paper selections are recorded at **1 unit**. Bankrolls are *simulated afterwards* by replaying settled selections in
event-start order, so one set of selections can be tested under several policies without refitting anything.

## Bankrolls and policies
Bankrolls £20, £30, £50, £100 × policies `flat_1pct`, `flat_2pct`, `kelly_1_8` (⅛ Kelly on the frozen P and the frozen net
odds, capped at 2%), and `min_stake` (always the practical minimum).

## Hard rules (every policy)
- **Practical minimum stake** (verify on the real account before any live use): exchange £1.00, bookmaker £0.10. When a
  policy's stake is below the minimum, the stake is rounded up to the minimum **only if** that still fits the per-bet cap.
  Otherwise the bet is **skipped** and counted (`SKIP_MIN_STAKE`). Example: £30 × 2% = £0.60 < £1 exchange minimum, and £1 is 3.3%
  of £30, which is under the 5% cap, so it is allowed but recorded as `ROUNDED_UP_TO_MIN`. On £20, £1 = 5% is right at the cap.
  This is why "£1–£3 per bet on £30" is **not** presumed safe: £3 is 10% of the bankroll, twice the cap.
- Per-bet cap 5% of current bankroll; daily exposure cap 10%; daily loss lock at −10% of the day's opening bankroll; a
  drawdown stop at −30% from peak ends the simulation and flags a review.
- No martingale, no loss-chasing and no recovery staking. These are not implemented and cannot be configured. Stakes never
  depend on previous outcomes except through the current bankroll size and the locks.
- Exposure is counted per UTC day on the event-start date. Selections on the same event are impossible (one per prediction, and
  one prediction per event and engine).

## Reported per bankroll × policy
Final bankroll, peak, max drawdown (£ and %), bets placed / skipped (by reason), stakes, realised P&L, ROI on turnover,
longest losing streak, and whether any lock or stop fired. With a small sample these numbers are **descriptive only**.
