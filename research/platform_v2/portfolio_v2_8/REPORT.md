# V2-8 Bet Portfolio / Card Allocation Research: Report (2026-09-30)

**Research only. EXPLORATORY on previously examined data (V2-7H).** Production, bsv2-3, frozen engines and the V2-7 prospective
logger are unchanged. Nothing was purchased. No paper or real-money multis were enabled.

**Provenance.**
- Pre-registration: `PREREGISTRATION.md` (commit `7a3b9dc`, before any V2-8 number).
- Code: `scripts/v2_8_portfolio_research.py`, `src/prediction_markets_lab/research/portfolio.py`. Tests:
  `tests_research/test_v2_8_portfolio.py`.
- Numbers: `RESULTS.json` plus `portfolio_summary.csv`, `marginal_leg.csv`, `bankroll_realism.csv`, `near_miss.csv`.
- **Reproducibility:** the seed is fixed at 20260930. Re-running one full block reproduced it byte-for-byte. Research tests: 71 passed;
  production suite: 1177 passed / 8 skipped.
- **V2-7 first live verification: PENDING.** No post-activation scheduled board run had written research output to master at the
  time of writing.

**Price labels.**
- **SYNTH_M0** — fair prices.
- **SYNTH_M5** — a 5% margin per leg. This is realistic retail: V2-7H measured −4.6% to −5.8%.
- **SYNTH_EDGE3** — a *hypothetical* genuine +3% EV on every leg.
- **REAL** — Bet365 closing prices vs Pinnacle-fair for tennis (a closing diagnostic), and football pre-closing prices (as-of).

Every multi price is a product of leg prices, so it is **INDICATIVE**. No real accumulator prices exist in any dataset.

## 1. Data and candidate sets
Frozen-engine favourites, as in V2-7H. The set for each sport-day is the top-N legs by P with P ≥ 0.70 and distinct participants.

**HIGH_P sets:**

| sport | days with N = 5 | days with N = 3 |
|---|---|---|
| ATP | 392 | 728 |
| WTA | 320 | 614 |
| NBA | 244 | 780 |
| Football | 3 | 52 |

**Real-price sets:**

| scenario | N = 5 | N = 3 |
|---|---|---|
| Tennis closing diagnostic, HIGH_P (ATP / WTA) | 296 / 237 | 609 / 514 |
| Football pre-closing | 0 | 52 |

**POS_EV sets** (every leg EV > 0 at one book; tennis closing diagnostic only):

| | N = 2 | N = 3 |
|---|---|---|
| ATP | 68 | 12 |
| WTA | 65 | 6 |

## 2. Prediction scoreboard: the legs
Legs are scored individually, whatever instrument they sit in.
- **All legs in the N = 5 sets:**
  - ATP 84.2% predicted → 83.8% realised (n = 1,960)
  - WTA 83.3% → 83.0% (n = 1,600)
  - NBA 81.2% → 81.6% (n = 1,220)
  - Every CI contains 0.
- **By rank** (1 = highest P), every rank is calibrated to within its CI. The one exception is NBA rank 2 at +4.4 pp, CI [+0.1, +8.0];
  it is unadjusted, among 27 rank cells.
- **Football N = 3** (52 sets): −5.1 pp overall, CI [−12.8, +2.3]. This is small and imprecise.

## 3. Legs-correct distribution and near misses
- **The number of correct legs follows the independent-legs Poisson-binomial prediction almost exactly.**
  - ATP N = 5: predicted 0.1 / 1.5 / 12.9 / 58.7 / 146.4 / 172.4 for 0–5 correct; observed 0 / 1 / 14 / 64 / 144 / 169.
  - Simulated χ² p = 0.94 (ATP N = 5), 0.79 (WTA N = 5), 0.94 (NBA N = 5), and 0.38–0.54 for N = 3.
  - Football N = 3: p = 0.088. **No rejection after Holm**, the lowest adjusted p being 0.62.
- **Near misses are exactly as frequent as calibrated probabilities predict.** Share of failed 5-folds that failed by exactly one leg:

  | | observed | expected |
  |---|---|---|
  | ATP | 64.6% | 67.4% |
  | WTA | 65.3% | 65.0% |
  | NBA | 62.5% | 63.0% |
  | 3-folds, tennis and NBA | 77–84% | 80–82% |

- **Rank responsibility.** No rank is disproportionately the single loser: every Holm-adjusted p is ≥ 0.14. The lowest-P leg loses in
  39–42% of failed 5-folds, against 38–39% expected. Adding the 4th or 5th leg does not "break" cards beyond what its own P implies.
- **Interpretation.** A 4/5 accumulator is **4 correct predictions and a financial loss.** The losses on multis come from the
  all-or-nothing instrument, **not** from worse predictions.

## 4. Card size and marginal legs
Representative example: ATP, N = 5, ranks added in order. Averages over 392 days.

| k | P_joint | fair odds | M5 odds | M5 EV | implied margin | real-close EV | EDGE3 Kelly growth | P(full loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.914 | 1.10 | 1.05 | −4.8% | 5.0% | −3.0% | 54.7 bp | 0.09 |
| 2 | 0.802 | 1.27 | 1.15 | −9.3% | 10.3% | −6.4% | 80.4 bp | 0.20 |
| 3 | 0.677 | 1.54 | 1.33 | −13.6% | 15.8% | −10.0% | 90.9 bp | 0.32 |
| 4 | 0.554 | 1.94 | 1.60 | −17.7% | 21.6% | −13.5% | 94.0 bp | 0.45 |
| 5 | 0.440 | 2.55 | 2.00 | −21.7% | 27.6% | −16.9% | 91.0 bp | 0.56 |

Realised full-win rates for 1–5 legs match P_joint:
- ATP ACC_5: 44.0% predicted → 43.1% realised;
- WTA: 41.1% → 39.7%;
- NBA: 35.7% → 37.7%.

**Does adding a leg improve the bet?**
- **With negative-EV legs** (M5 and real closes), adding a leg lowered the fixed-stake growth on 97–100% of days and never raised
  Kelly growth.
- **With a genuine +EV leg** (EDGE3), the card's EV compounds, so growth at a fixed 1% stake rises with every leg. Kelly-optimal growth,
  however, **peaks at about 3–4 legs**: the 5th leg improves it on only 28% of ATP days and 25% of NBA days, because whole-card
  losses reach 56–64%.
- The natural stopping point therefore depends on the staking rule, **and on whether each added leg is genuinely +EV.**

## 5. Portfolios at equal total capital
Model expectation over exact 2^N outcome distributions, ATP N = 5. Per unit of daily capital.

| structure | lines | max share on one leg | P(lose all capital) | E[return] M0 / M5 / EDGE3 | real-close E[return] | realised, real close |
|---|---|---|---|---|---|---|
| SINGLES | 5 | 0.20 | 0.000 | 0 / −4.8% / +3.0% | −3.6% | −3.8% [−6.0, −1.7] |
| DBL12+SINGLES | 4 | 0.25 | 0.002 | 0 / −5.9% / +3.8% | −4.5% | −4.7% |
| 2DBL+SINGLE | 3 | 0.33 | 0.018 | 0 / −7.8% / +5.1% | −6.0% | −6.8% |
| TBL123+SINGLES | 3 | 0.33 | 0.018 | 0 / −7.7% / +5.1% | −5.9% | −6.2% |
| RR_DOUBLES (10) | 10 | 0.40 | 0.004 | 0 / −9.3% / +6.1% | −7.1% | −7.8% |
| RR_TREBLES (10) | 10 | 0.60 | 0.037 | 0 / −13.6% / +9.3% | −10.5% | −11.7% |
| Canadian (26) | 26 | 0.58 | 0.004 | 0 / −13.1% / +8.9% | −10.1% | −11.2% |
| Lucky 31 | 31 | 0.52 | 0.000 | 0 / −11.7% / +8.0% | −9.1% | −10.0% |
| ACC_2 | 1 | 1.00 | 0.198 | 0 / −9.3% / +6.1% | −6.4% | −4.6% |
| ACC_5 | 1 | 1.00 | 0.560 | 0 / −21.7% / +15.9% | −16.9% | −19.2% [−30.2, −6.4] |

**Law this makes visible.** Every portfolio's expected return is the average over its lines of (1 + e)^(legs in line) − 1. **A structure
is a lever on the per-leg edge.** It cannot create value; it amplifies whatever edge the legs have:
- positive edge → larger multis and systems amplify gains;
- negative edge → they amplify losses.

System bets lower the chance of losing everything (0–4% versus 56% for the 5-fold), but they carry the **compounded margin of every line**.

**Growth versus SINGLES** (mean daily log-return difference, paired day-bootstrap CI, at 2% of bankroll per day). Counts of structure
comparisons across all sets and periods:

| scenario | structure better | singles better | no difference | < 30 days |
|---|---|---|---|---|
| SYNTH_M0 (fair) | 0 | 0 | 57 | 0 |
| **SYNTH_M5 (retail margin)** | **0** | **43** | 14 | 0 |
| REAL (tennis close, football pre-close) | 0 | 24 | 26 | 12 |
| SYNTH_EDGE3 (every leg +3%) | **31** | 0 | 26 | 0 |

In the EDGE3 scenario, structures beat singles in development (18) and in holdout (18), and never lose.

**Mixed portfolios** such as DBL12+SINGLES and 2DBL+SINGLE sit between singles and accumulators on every metric. They add no risk
adjustment beyond what their line mix implies.

## 6. Probability-error sensitivity
- **REAL and M5:** δ* = 0. These structures are already negative-EV, so no error margin exists.
- **EDGE3**, with each leg carrying +3%:
  - Portfolio EV reaches zero at a uniform per-leg overestimate of **2.4–2.6 pp for every structure**, because each leg's EV goes to
    zero at the same point.
  - The growth advantage over singles disappears at about **2–2.5 pp**. At +3 pp every structure is *worse* than singles, and the
    larger multis are worst: ACC_5 −9 to −11 bp/day, against −1 to −2 bp for doubles.
- **Empirical development band SE** (1.0–2.5 pp per leg) keeps EDGE3 portfolios positive. This holds only under the hypothetical
  +3% edge; historically we observed no such edge.
- **A large central EV from a 4- or 5-fold is the most error-sensitive number in the study**: its advantage swings by 43 bp/day between
  −1 pp and +3 pp of error.

## 7. Bankroll and drawdown realism (£20–£100, stakes rounded down to £0.10 per line)
**Stake granularity dominates at £20–£30.**

| daily risk | at £20 | effect |
|---|---|---|
| 2% (£0.40) | 5 singles need £0.08 each | **cannot be placed** (below the £0.10 minimum) |
| 5% (£1.00) | 5 singles at £0.20 | feasible |
| any | systems of 10–31 lines | infeasible |

- **With a £1 minimum line**, only a single-line structure (one single or one accumulator) is feasible, and only at 5% risk.
- **At a realistic margin** (M5, ATP, 392 days, £20, 5%/day), every structure lost:
  - singles → £9.88 (maximum drawdown 51%);
  - ACC_2 → £5.90 (75%);
  - ACC_3 → £1.96 (91%);
  - ACC_5 → £1.93 (91%).
- **At real tennis closing prices** (296 days, £20, 5%): singles → £14.14 (drawdown 32%); ACC_2 → £9.48; ACC_5 → £1.98 (drawdown 91%).
- **The EDGE3 hypothetical** (£20, 5%): singles → £28.87 (drawdown 12%); ACC_2 → £108 (24%); ACC_5 → £175 (74%). This is a picture of
  what a *genuine* edge would do. It is not evidence.

## 8. Overlap and exposure
Capital riding on a single leg:
- 20% for 5 singles;
- 25–33% for mixed portfolios;
- 40% for round-robin doubles;
- 52–60% for full-cover systems and round-robin trebles;
- 100% for any accumulator.

Systems place a leg in up to 16 of 31 lines (Lucky 31), so **one losing leg reprices most of the portfolio**.

## 9. Answers to the 12 questions
1. **Scoring legs separately changes the interpretation of losing multis materially.** A failed 5-fold is typically 4/5 correct (65%
   of failures). The predictions behave as calibrated; the all-or-nothing instrument is what loses the money.
2. **Near misses occur exactly as often as calibrated probabilities predict.** Every goodness-of-fit and near-miss test passes after
   Holm correction.
3. **No leg rank disproportionately causes failure.** The lowest-P leg fails at its own rate (39–42% of failed 5-folds, against
   38–39% expected).
4. **Each added leg multiplies P_joint by p_i, the price by o_i, and (1 + EV) by (1 + EV_i).**
   - Whole-card loss goes 9% → 20% → 32% → 45% → 56%.
   - Implied margin goes 5% → 10% → 16% → 22% → 28% at retail.
5. **Margin overwhelms the payout improvement from the very first added leg, whenever the leg is not genuinely +EV.** A bigger payout
   never compensates, because card EV = ∏(1 + EV_i) − 1 does not depend on payout size.
6. **A multi can beat singles on the same capital only when every leg carries a genuine edge** that exceeds the model's error by
   about 2 pp or more, and stakes stay small. In that hypothetical (EDGE3), structures beat singles in 31/57 cells and never lose.
   Historically, no such legs were demonstrated.
7. **Selected doubles and trebles lose far less than blindly combining everything** at retail margins (−9% and −14%, against −22% for
   ACC_5). With a genuine edge, selected 2–4 leg cards reach the highest Kelly growth. Selection reduces damage; it does not create
   value.
8. **Mixed portfolios interpolate between singles and accumulators.** They add no free risk-adjusted improvement.
9. **Round-robin and system structures remove the all-or-nothing risk, but compound margin on every line.** At retail they are 2–3×
   worse than singles (−9% to −14% against −4.8%), and they cannot be placed at £20–£30 with £0.10–£1 minimums.
10. **Sensitivity to probability error scales with leg count.** An edge advantage vanishes at about 2–2.5 pp of per-leg overestimate
    (for a +3% edge). The largest multis flip hardest.
11. **For a £20–£30 bankroll**, at most 1–2 instruments a day, or NO BET. Five singles at a 2% daily risk are not placeable.
    Systems are out.
12. **Paper eligibility for any structure would require all of the following:**
    - every leg individually POS_EV with its EV lower bound > 0 (the existing rule);
    - leg calibration verified prospectively in its band to about ±1.5 pp;
    - accumulator price and rules verified at the book, from the bet slip;
    - the structure beating the same legs as singles at equal capital prospectively, with a CI excluding 0 over at least about 100
      independent settled days;
    - feasibility within stake minimums;
    - Fraser's approval.

## 10. Decision matrix (no overall winner forced)
| structure | probability evidence | price evidence | risk evidence | profitability evidence | paper readiness |
|---|---|---|---|---|---|
| Singles | STRONG | INDICATIVE (tennis, NBA); EXECUTABLE-like (football pre-close) | ACCEPTABLE | NEGATIVE at retail HIGH_P; INCONCLUSIVE POS_EV | NEEDS MORE EVIDENCE (the existing bsv2-3 path) |
| Doubles | STRONG (tennis) / PROMISING | INDICATIVE | UNCERTAIN (20–30% full loss) | NEGATIVE at retail; INCONCLUSIVE POS_EV (n = 65–68) | RESEARCH ONLY |
| Trebles | PROMISING (< 0.65) | INDICATIVE | HIGH | NEGATIVE | RESEARCH ONLY |
| 4-leg | PROMISING (legs-count fit exact; P_joint 0.47–0.55 calibrated) | INDICATIVE | HIGH | NEGATIVE | RESEARCH ONLY |
| 5-leg | PROMISING (same) | INDICATIVE | HIGH (56–64% full loss) | NEGATIVE | RESEARCH ONLY |
| Round robin / system | STRONG (built from legs) | INDICATIVE | UNCERTAIN (low full loss, margin on every line, infeasible stakes) | NEGATIVE | RESEARCH ONLY |
| Mixed portfolio | STRONG (from legs) | INDICATIVE | UNCERTAIN | NEGATIVE at retail | RESEARCH ONLY |
| NO BET | — | — | ACCEPTABLE | — | always available |

## 11. Limitations caused by indicative multi prices
- Real accumulator prices can differ from the product of leg prices: related-contingency rules, maximum payouts, acca boosts or
  insurance, stake limits. None of these is modelled or verified.
- The EDGE3 scenario is a counterfactual.
- REAL tennis prices are closing, not decision-time.
- Football has almost no days with at least 5 favourites at P ≥ 0.70 (3 days), so 4- and 5-fold football results are absent.
- All results are exploratory on previously examined data.

## 12. Proposed bounded V2-8 prospective extension (DESIGN ONLY; not deployed)
See `PROSPECTIVE_EXTENSION_DESIGN.md`. In short: **no new live logging is needed.** V2-7 already freezes everything V2-8 needs:
- event-level HIGH_P legs (up to 24 per scan);
- per-book POS_EV legs;
- production per-book `price_snapshots.csv`, with its sha recorded.

An offline, deterministic V2-8 analyser can rebuild every portfolio in §3 of the pre-registration per scan, with:
- N ≤ 5 and at most 16 structures × 2 populations;
- 0 credits;
- under 1 s per scan;
- about 10 KB per scan if summaries are stored.

It requires no change to V2-7.

## 13. Daily Bet Card: portfolio concept (design only; no grades invented)
```
DAILY OPPORTUNITIES (prediction scoreboard view)
  A  P 0.86 ±σ | band evidence | book odds 1.15 | fair 1.16 | leg EV −0.9% | fresh 12 min
  B  ...
ALLOCATION OPTIONS (same daily capital; structure scoreboard view)
  1 Singles A–E      E[r] −4.1%  P(lose all) 0.0%  worst −100%  feasible at £20? no (5 × £0.08)
  2 Double A+B       E[r] −8.2%  P(lose all) 27%   ...
  3 Mixed / system   ...
  0 NO BET           0
RECOMMENDED PORTFOLIO: the option with the best probability → evidence → price → uncertainty → payout → risk → bankroll fit;
NO BET whenever no option has positive EV after error sensitivity. Grades A+ to REJECT: thresholds deliberately NOT set yet.
```

## 14. Recommended next action
1. Keep V2-7 collecting. Verify its first live run when it lands; the status is PENDING.
2. Keep **singles as the default instrument and NO BET as the default outcome**. The allocation question only becomes real once
   individual legs show a **genuine, prospectively verified edge**, because structure only amplifies the sign of that edge.
3. On approval, build the offline V2-8 analyser over the V2-7 prospective data. It requires no change to V2-7.
4. Fraser could verify one bookmaker's accumulator bet-slip price against the product of its leg prices, without placing a bet. This
   is the only way to move multi prices from INDICATIVE toward EXECUTABLE.

## Erratum E1 (2026-09-30, found while building the offline analyser)
In the REAL-price scenarios, the historical HIGH_P set selection took each book's own top-N and then chose the book with the
highest price product. That could, in principle, have selected weaker legs at a book lacking a stronger one. The code now fixes the
N strongest predictions **first**, then uses the book that prices all N. In the POS_EV population, the book with the highest joint P
is now used. After a full re-run, **every result block is byte-identical**: every priced set had already been the global top-N,
since tennis has one book and the football books priced the same legs. The only change is the `days_no_single_book` counter, which
had been counting days without enough legs. Prior numbers stand.
