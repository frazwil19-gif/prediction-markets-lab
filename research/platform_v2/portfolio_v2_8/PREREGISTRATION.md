# V2-8 Bet Portfolio / Card Allocation Research: Pre-registration

**Written 2026-09-30, before any V2-8 number is computed.** This is research only. It changes nothing in production, bsv2-3, the frozen engines or the V2-7 prospective logger (frozen; first live run PENDING at the time of writing). No data is purchased, and no paper or real-money multis are enabled.

**Status of the evidence.** The V2-7H data have already been examined. Every V2-8 historical result is therefore
**EXPLORATORY on previously examined data**, however pre-registered. Confirmation can only come from untouched or prospective
data. V2-7H is kept unchanged as evidence.

## 1. Question
Given the N strongest predictions available on a day, and the prices available, how should one fixed daily capital be allocated
across instruments? The options are singles, selected multis, 4-fold and 5-fold accumulators, round-robin/system bets, mixed
portfolios, or NO BET. No structure is assumed to be better.

## 2. Candidate sets (deterministic, never uses outcomes)
- Legs are the favourite side of each frozen engine (ATP, WTA, NBA, football), as in V2-7H.
- **HIGH_P set** for a sport-day: the top-N legs by P with P ≥ 0.70, taken in rank order and skipping any repeated participant.
  Ties are broken by event hash. N ∈ {3, 5}. A day enters the N-analysis only if it has at least N such legs.
  - Ranks r = 1 … N run from highest to lowest P.
- **POS_EV set:** the same rule, restricted to legs with net EV > 0 at a single book. This is only possible in the CLOSE-DIAG tennis
  scenario (B365 close vs Pinnacle-fair). N ∈ {2, 3}.
- **The HIGH_P and POS_EV populations are never pooled.**

## 3. Structures (equal total daily capital S, split equally across lines, as system bets are)
For N legs ranked 1..N:

| id | lines |
|---|---|
| SINGLES | N singles |
| ACC_k, k = 2..N | one k-fold on ranks 1..k (a "selected" accumulator; ACC_N = everything combined) |
| DBL12+SINGLES | double (1,2) + singles 3..N |
| 2DBL+SINGLE (N = 5) | (1,2), (3,4) + single 5 |
| TBL123+SINGLES (N = 5) | (1,2,3) + singles 4, 5 |
| RR_DOUBLES | all C(N,2) doubles |
| RR_TREBLES (N = 5) | all C(5,3) = 10 trebles |
| FULL_COVER | every combination of size ≥ 2 (N = 3: Trixie, 4 lines; N = 5: Canadian, 26 lines) |
| FULL_COVER+SINGLES | every combination of size ≥ 1 (N = 3: Patent, 7 lines; N = 5: Lucky 31) |
| NO_BET | nothing |

Line stake = S / n_lines. The multi price is the product of the leg prices (**INDICATIVE**). No bookmaker bonuses or consolations
are modelled.

## 4. Price scenarios (labels are always shown)
- **SYNTH_M0:** O = 1/p. Fair prices.
- **SYNTH_M5:** O = 1/(p·1.05). Realistic retail margin; V2-7H measured −4.6% to −5.8% per favourite leg.
- **SYNTH_EDGE3:** O = 1.03/p. A *hypothetical* world in which every leg carries a genuine +3% EV. This answers the question "if we had
  real +EV legs, which structure would be best?"
- **ASOF-FB:** real pre-closing same-book UK prices for football, with the book chosen as in V2-7H amendment A2. Indicative for multis.
- **CLOSE-DIAG tennis:** B365 close vs Pinnacle-fair P. A diagnostic only.

Synthetic prices describe structure and risk. They are **never** evidence of profit. Realised results under SYNTH scenarios use the
actual outcomes, so they also reflect calibration.

## 5. Two scoreboards (both always reported)
- **A. Prediction scoreboard** (per leg in the candidate sets): event, selection, P, band-SE uncertainty (development-period), outcome,
  Brier, log loss, calibration by rank and band. A 4/5 accumulator counts as 4 correct and 1 incorrect here.
- **B. Structure scoreboard** (per instrument and portfolio as it settles): legs, joint P, indicative odds, fair odds, stake, payout,
  P&L, ROI, whole-stake loss, drawdown, bankroll impact. A 4/5 accumulator is a **LOSS** here.

## 6. Analyses
1. **Legs-correct distribution.** For each N-set, the predicted Poisson-binomial distribution of the number of correct legs, compared
   with the realised histogram. Test: χ² goodness of fit, with the p-value from a 10,000-draw parametric simulation under the model
   (seed 20260930). Per sport × N, with Holm correction across sports.
2. **Near misses** (diagnostic). Among failed ACC_N:
   - share failing by exactly one leg, predicted vs realised;
   - which rank was the single loser, per-rank observed vs expected, with a binomial test per rank and Holm across ranks;
   - share where the lowest-P leg was a loser, observed vs expected.
   - **A near miss is never counted as a financial success.**
3. **Marginal leg.** For ACC_k, k = 1 → N (adding rank k), per scenario, averaged over days: Δ joint P, fair odds, indicative odds,
   EV, σ_joint (delta method with development band SE), expected log growth at s = 1% and at the Kelly-optimal fraction,
   whole-card loss probability, and implied margin. "The leg improves the bet" only if the Kelly-optimal growth rises. Computational
   caps (N ≤ 5) are not betting rules.
4. **Card size (1–5).** Joint P, calibration, P(full win), legs-correct distribution, indicative payout, EV where legitimate, variance,
   drawdown, streaks, error sensitivity.
5. **Portfolios** (all structures in §3, per scenario). Exact daily P&L distribution by enumerating all 2^N leg outcomes:
   - expected profit, variance, maximum loss, P(lose the full daily stake), P(positive day), P(negative day);
   - expected log growth at the daily fraction f;
   - exposure per selection (capital riding on each leg across lines);
   - number of instruments.
   - **Realised:** chronological compounding at f ∈ {1%, 2%, 5%} of the current bankroll, per day. Reports ROI, mean daily log return
     with a day-bootstrap CI, maximum drawdown, longest losing run, and P(bankroll < 50%) from bootstrap re-orderings.
   - **Comparison:** each structure versus SINGLES, as the mean daily log-return difference with a paired day-bootstrap CI. A
     verdict needs ≥ 30 days.
6. **Probability-error sensitivity.** For every structure and scenario, true p = p − δ on every leg, δ ∈ {±0.5, 1, 1.5, 2, 3, 5} pp:
   - expected profit and expected log growth;
   - δ* at which expected profit reaches 0;
   - δ at which the structure's growth advantage over SINGLES disappears.
   - A deterministic grid, plus empirical development band SE, labelled separately.
7. **Small-bankroll realism.** Bankroll £20 / £30 / £50 / £100, daily capital f ∈ {2%, 5%}:
   - each line is rounded down to £0.10;
   - minimum line stake £0.10 (config, bookmaker), with a sensitivity at £1.00;
   - a structure whose lines fall below the minimum is **not bet** that day (counted), never scaled up;
   - ruin = bankroll below £1;
   - no martingale, no chasing, no forced bets.
8. **Overlap.** Capital per selection, the maximum share of daily capital riding on one leg, and lines per leg.

## 7. Periods and multiple testing
- Periods are development and holdout as in V2-7H, both **previously exposed**.
- Only tests 6.1 and 6.2 use formal p-values (Holm within each family). Everything else is descriptive or exploratory with CIs.
- The results will not be used to tune any structure, N or stake until something looks profitable.

## 8. Outputs
- Code: `scripts/v2_8_portfolio_research.py`, `src/prediction_markets_lab/research/portfolio.py`.
- Tests: `tests_research/test_v2_8_portfolio.py`.
- Numbers: `RESULTS.json` and CSVs.
- Report: `REPORT.md`, including the decision matrix (§19 of the directive), the answers to the 12 questions, the bounded V2-8
  prospective-extension design (**design only**) and the Daily Bet Card portfolio concept.
