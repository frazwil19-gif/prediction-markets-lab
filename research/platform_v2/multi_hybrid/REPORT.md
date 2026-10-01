# Probability-first bet construction + multi + hybrid theory test — REPORT

Date: 2026-10-02. Pre-registration: `PREREGISTRATION.md` (commit `0e2827f`, before any new analysis).
Script: `scripts/multi_hybrid_research.py`. Numbers: `RESULTS.json`, `margin_compounding.csv`.

This was research only. No production change, no paper or multi activation, no threshold change and no purchase.
Labels used below: **CONF** = confirmatory (pre-registered cell); **EXPL** = exploratory; **DATA_REQUIRED**.

## Answer first
* **Calibration:** separate-event multis are well calibrated, including the high-P doubles that V2-7H could not test.
  The independence assumption holds.
* **Margin:** bookmaker margin compounds almost linearly with leg count. At P ≥ 0.80 in tennis, the expected value is:

  | Structure | Expected value |
  |---|---|
  | Single | −3.6% |
  | Double | −7.1% |
  | Treble | −10.5% |
  | 4-fold | −13.7% |
  | 5-fold | −16.4% |

* **Multis do not solve the payout problem.** At equal capital, singles beat or equal every multi structure, in every
  cohort, in the large-sample sport (tennis). Multis add variance and whole-stake losses.
* **The one exception** is football high-P doubles (+9–11 pp over singles, CI just excluding 0 in 2 of 3 books, n = 23
  cards). This is fully explained by a known, *unstable* favourite under-confidence in the football consensus.
  Treat it as a hypothesis, not a finding.
* **Consensus remains the best probability estimator.**
  * Elo is worse in every league.
  * A market + Elo hybrid is better in **0 of 11** leagues on an untouched 2024–26 test, and significantly worse in D1.
  * Recalibrating the market's under-confidence on 2020–22 data did not hold up in 2024–26.

## 1. What previous multi research proved or failed to prove (V2-7H, V2-8, decision replay)
**Proved:**
* separate-event joint probabilities are calibrated (no Holm rejection);
* independence holds to within ±0.4 pp (tennis, NBA) and ±0.9 pp (football);
* margin compounds as (1 + EV)^k;
* with a realistic margin, singles beat cards in 100/100 SYNTH cells and 15/15 CLOSE-DIAG cells;
* card drawdowns are 1.5–3× those of singles;
* whole-stake loss happens on 24–47% of days for doubles and trebles;
* a +EV multi's edge is smaller than our own calibration uncertainty;
* POS_EV multis essentially never exist at football pre-close.

**Not proved:**
* any profitable structure (no CI excluding 0 in both periods);
* calibration of high-P doubles (≥ 0.80) and trebles (≥ 0.65), where n was 10–55.

The present study fills that gap.

## 2. Are separate-event joint probabilities calibrated? **Yes.**
Method: disjoint cards within day and cohort, ordered by an outcome-free hash, so ESS = number of cards. Bias is
shown in percentage points with a day-cluster 95% CI.

| Sport | ≥ 0.80 doubles (**CONF**) | ≥ 0.70 trebles (**CONF**) | ≥ 0.85 doubles | ≥ 0.90 doubles | Top-2 per day | Top-3 per day |
|---|---|---|---|---|---|---|
| ATP | n 936: 76.9 → 76.7 [−3.0, +2.6] ✅ | n 1,187: 53.9 → 52.7 [−3.9, +1.6] ✅ | n 490: 83.3 → 83.9 ✅ | n 236: 88.7 → 90.3 ✅ | 64.8 → 66.6 ✅ | 50.9 → 52.2 ✅ |
| WTA | n 683: 75.5 → 77.5 [−1.3, +5.0] ✅ | n 971: 52.3 → 52.2 ✅ | n 317: 81.7 → 86.1 [+0.3, +8.4] ⚠️ | n 121: 87.2 → 86.0 ✅ | 62.1 → 61.7 ✅ | 48.2 → 47.1 ✅ |
| NBA | n 461: 73.2 → 75.7 [−1.2, +6.2] ✅ | n 700: 50.7 → 52.6 ✅ | n 178: 78.1 → 82.6 ✅ | n 24 (too few) | 61.8 → 63.1 ✅ | 46.4 → 49.0 ✅ |
| Football | n **23**: 68.7 → **87.0** [+3.9, +31.6] ⚠️ | n 52: 45.7 → 36.5 [−21.6, +4.0] ✅ | n 2 | 0 | 41.2 → 45.7 [+1.2, +7.8] ⚠️ | 25.0 → 27.0 ✅ |

* **Confirmatory cells:** 7 of 8 contain 0. Football ≥ 0.80 doubles do not (n = 23). With Holm across 8 cells
  (α / 8), a CI that only just excludes 0 does not survive. It is under-confidence, never over-confidence.
* **4- and 5-folds:**
  * calibrated within CI in most cells;
  * ATP ≥ 0.60 4/5-folds are over-predicted by 2.7–3.3 pp (CI excludes 0, EXPL);
  * NBA top-5 is under-predicted by 3.3 pp (EXPL).
* **Joint-P bands** (all cohorts ≥ 0.5, k = 2–5): calibrated in every band with n ≥ 100, in all four sports.
* **Prediction scoreboard:** leg accuracy inside cards equals single-leg accuracy, because legs are the same
  predictions. A lost card with 4 of 5 legs correct counts as 4 correct predictions and 1 lost card, kept separate
  throughout `RESULTS.json`.

## 3. Do high-P doubles improve the payout/risk profile versus their singles?
Evidence class B: same-book product, equal capital (1 unit on the double versus ½ unit on each leg). ROI is shown with
a day-cluster CI.

| Price set | Cohort | Cards | Joint P → hit | Mean double odds | Card EV (model) | Card ROI | Singles ROI | Card − singles |
|---|---|---|---|---|---|---|---|---|
| Tennis B365 close (Pinnacle-fair P) | ≥ 0.80 | 1,288 | 74.8% | 1.25 | −7.1% | −3.4% | −1.6% | **−1.9 [−3.4, −0.3]** |
| | ≥ 0.85 | 621 | 80.8% | 1.17 | −6.2% | −1.1% | −0.6% | −0.4 [−2.2, +1.3] |
| | ≥ 0.90 | 214 | 86.4% | 1.10 | −5.3% | −1.2% | −0.5% | −0.7 [−2.9, +1.4] |
| Football B365 pre-close | ≥ 0.80 (**CONF**) | 23 | 68.7 → 87.0% | 1.32 | −9.8% | +14.7% | +4.8% | **+9.9 [+0.5, +17.1]** |
| Football WH | ≥ 0.80 (**CONF**) | 22 | | 1.31 | −10.5% | +13.3% | +4.0% | +9.3 [−0.9, +16.5] |
| Football BW | ≥ 0.80 (**CONF**) | 22 | | 1.33 | −8.7% | +15.7% | +5.1% | +10.6 [+0.5, +18.1] |
| Football (all books) | ≥ 0.85 (**CONF**) | 2 | — | — | — | — | — | n too small |

**Leakage audit.** The football cell triggered the pre-registered "too good" audit.
* P is the median-of-books consensus from the pre-closing snapshot, and outcomes come from FTR. There is no
  timestamp overlap.
* The football effect is entirely leg under-confidence: legs ≥ 0.80 predicted 83.4% and won 88.7% (n = 203). That
  happened in 6 of 7 seasons and was concentrated in SC0 (103 legs) and E0 (91).
* A double multiplies a leg under-confidence of about +5 pp into about +18 pp at card level.
* The same football pattern was flagged in V2-7H (§3, §9) and V2-18. **No leakage found. The cause is a calibration
  property, not a multi property.**

The tennis result is the general case: doubling high-P legs **lowers** the expected return. At P ≥ 0.85–0.90 the
difference is small because the margin per leg is smaller (2.6–3.2%), but it is never positive.

## 4. Trebles
Card − singles, equal capital:

| Cohort | Card − singles |
|---|---|
| Tennis ≥ 0.70 | −4.7 [−7.4, −2.0] |
| Tennis ≥ 0.80 | −2.2 [−6.1, +1.4] |
| Tennis ≥ 0.85 | −2.3 [−6.7, +1.6] |
| Tennis ≥ 0.90 | −1.8 [−7.7, +4.0] |
| Football ≥ 0.70 | −23 [−40, −5] |

Football ≥ 0.80 trebles: n = 3. **No improvement.**

## 5. 4- and 5-leg structures
Card − singles, tennis:

| Cohort | 4-fold | 5-fold |
|---|---|---|
| ≥ 0.70 | −9.0 [−13.6, −4.2] | −14.8 [−21.1, −8.5] |
| ≥ 0.80 | −4.4 | −4.3 |

* Football ≥ 0.5: −22 / −38 to −40.
* Whole-stake loss probability at ≥ 0.80: 43% (4-fold), 50% (5-fold).
* **Strictly worse.**

## 6. How margin compounds (`margin_compounding.csv`)
Mean model EV at the same book: the leg EV, then the card EV for k = 2, 3, 4, 5.

| Price set | k = 1 | k = 2 | k = 3 | k = 4 | k = 5 |
|---|---|---|---|---|---|
| Tennis ≥ 0.80 | −3.6% | −7.1% | −10.5% | −13.7% | −16.4% |
| Tennis ≥ 0.90 | −2.7% | −5.3% | −7.3% | −9.8% | −12.4% |
| Football B365 ≥ 0.70 | −5.3% | −10.2% | −14.4% | −18.2% | — |
| Football ≥ 0.5 | −5.8% | −11.2% | −16.2% | −21.0% | −25.6% |

Offered product odds / fair product odds ≈ (1 − leg margin)^k. A bigger nominal payout is **always** a worse expected
return when the legs carry the margin.

## 7. Do high-P short-odds selections have a legitimate role as multi legs?
**Not on the evidence available.**
* Combining does not remove the margin; it multiplies it.
* A double of two 1.12 favourites (fair 1.15 each) pays 1.25 against a fair 1.33.
* The role would exist only if the legs themselves were underpriced: under-confident P, or a book above fair. That is
  the same condition that makes the *single* worthwhile.
* Football's under-confidence is the only sign of this. It did not survive recalibration out of sample (§18).

## 8. Singles, doubles, trebles and 4/5-folds at equal total capital
Tennis ≥ 0.80, B365, chronological, one card per day (675 days), 1% of bankroll:

| Start | Double final (max DD) | Same legs as singles (max DD) | Treble final (max DD) | Same legs as singles (max DD) |
|---|---|---|---|---|
| £50 | £40.10 (23.4%) | £45.26 (11.8%) | £44.24 (19.9%) | £48.56 (5.8%) |

Every structure loses at a 4% margin; the double loses most and has twice the drawdown.

Football B365 ≥ 0.80 doubles (23 days, 1%): £50 → £51.71 versus singles £50.55. That is n = 23, an artefact of the
under-confidence.

## 9. By P cohort
Card − singles for doubles, tennis:

| Cohort | Card − singles |
|---|---|
| ≥ 0.5 | −4.3 |
| ≥ 0.7 | −2.9 |
| ≥ 0.8 | −1.9 |
| ≥ 0.85 | −0.4 |
| ≥ 0.9 | −0.7 |

The penalty shrinks as P rises, because short prices carry less absolute margin. It never turns positive.

## 10. By actual joint-P band
Tennis, k = 2–3:

| Joint-P band | Cards | Card ROI | Mean model EV |
|---|---|---|---|
| < 0.5 | 11,838 | −10.6% | −11.3% |
| 0.5–0.6 | 1,979 | −5.9% | −8.7% |
| 0.6–0.7 | 812 | −13.1% | −7.9% |
| 0.7–0.8 | 292 | −2.2% | −7.1% |
| 0.8+ | 63 | +6.1% | −5.5% (EXPL, small) |

Football is similar: every band with n ≥ 100 is negative.

## 11. By combined-odds band
Tennis, k = 2–3:

| Combined-odds band | Cards | Card ROI |
|---|---|---|
| < 1.20 | 113 | +5.1% |
| 1.20–1.32 | 289 | −2.7% |
| 1.33–1.49 | 666 | −13.2% |
| 1.50–1.99 | 3,775 | −8.7% |
| 2.00–2.99 | 6,986 | −10.7% |
| 3.00+ | 3,155 | −10.0% |

Model EV gets worse with longer combined odds, from −6.8% to −12.8%.

## 12. By price-evidence class
* **A:** none exist.
* **B:** the tables above.
* **C:** a cross-book best price per leg (football, **not executable**) inflates card economics. For example, ≥ 0.70
  doubles go from −10.2% (same book) to −8.2%. This shows the artefact that a mixed-book "accumulator" would
  create.
* **D:** NBA and 13 xgabora leagues; probability only.

## 13. Drawdown, variance and losing runs
* **Variance per unit at ≥ 0.80** (tennis): single 0.13; equal-capital singles 0.064 (pair) / 0.041 (treble); double
  0.27; treble 0.41; 5-fold 0.73.
* **Longest losing run:** the same in days, but each card loss is a whole-stake loss.
* **Stress test, flat £5 on £30–£50** (not a policy):
  * football ≥ 0.70 doubles: **ruined** (−93% to −98%);
  * the equivalent singles survived on £50 (−48%);
  * tennis: everything at £5 flat on £30–£50 was ruined or nearly so.
  * £3 to £5 on £30 is 10–17% of bankroll per day, which is inappropriate for singles and multis alike.

## 14. The 1.33 singles floor
Floor-rejected legs (odds < 1.33), as singles:

| Price set | Cohort | N | P → win | Avg odds | ROI [CI] |
|---|---|---|---|---|---|
| Tennis B365 | ≥ 0.75 | 5,164 | 83.0 → 83.8 | 1.16 | −2.0% [−3.2, −0.9] |
| | ≥ 0.80 | 3,233 | 86.3 → 86.4 | 1.12 | −1.4% [−2.6, −0.1] |
| | ≥ 0.85 | 1,741 | 89.7 | 1.08 | −0.6% [−2.0, +0.7] |
| | ≥ 0.90 | 731 | 92.8 | 1.05 | +0.3% [−1.2, +1.7] |
| Football B365 / WH / BW | ≥ 0.80 | 184–203 | 83.4 → 88.7 | 1.13–1.15 | +0.9% / +1.4% / +3.3% |
| | ≥ 0.85 | 55–57 | 86.6 | 1.09–1.11 | +4.0% / +3.1% / **+6.7% [+0.5, +10.8]** (EXPL) |

Paired into doubles:
* tennis ≥ 0.80: −3.4%, worse than the singles;
* football ≥ 0.80: +13–16% (n = 22–23, the under-confidence).

**Reading of the directive's options A–E:**
* **A (retain the hard floor):** consistent with tennis. Floor-rejected singles lose in exactly the proportion the
  margin predicts, about 1.4–2% (CI excludes 0 at ≥ 0.75–0.80).
* **B (probability-aware payout rule) / C (allow very-high-P singles):** tennis gives no support. Expected value is
  still the margin, so the only thing that changes is the stake turnover needed to make a few pence.
* **D (use high-P outcomes as multi legs):** refuted for tennis; margin compounding is worse.
* **Football's floor-rejected favourites:** the only cohort with positive point estimates; small and EXPL. If you
  ever revisit the floor, the question is "is football consensus under-confident at high P prospectively?". It is
  not a multi question.
* **No production answer is selected.**

## 15. Should bet construction happen before single-bet financial rejection?
**Conceptually, yes, as the order of reasoning: predict, construct, evaluate. The evidence shows it changes nothing
today.**
* A multi's EV is the product of its legs' (1 + EV) minus 1.
* If no leg has EV > 0, no multi of those legs can have EV > 0 (same book).
* If legs are under-priced, the singles are already financially assessable.
* So "construct, then evaluate" is mathematically equivalent to the current single gates for same-book, independent
  legs, except when a positive-EV leg is paired with a slightly negative one. That case is rare and only adds risk.

The architecture can safely remain singles-first. A future construction layer is justified only when legs carry
positive EV, which the V2-7 POS_EV logger already records prospectively.

## 16. Non-market sporting data we already have
| Sport | Data (all pre-match unless noted) |
|---|---|
| Tennis | Betfair LTP; Elo-global and ranking P (`p_a_elo_global`, `p_a_ranking`); TML match data; tennis-data rankings and points |
| NBA | Scores, home/away, dates; Elo built in-house; a "data_logit" model (NBA research) |
| Football E0/E1/SC0 | Cycle-1 / Gate-1 fundamentals: 9 leakage-safe features, Elo+Poisson |
| Football, 13 leagues | xgabora: ClubElo (as-of snapshots); Form3/Form5 points; post-match shots, corners and cards (usable only as rolling pre-match aggregates, not built here) |

## 17. Is a bounded independent-model test possible now?
**Yes, and it was run** for 11 football leagues (market vs ClubElo vs a market + Elo hybrid). E2 and E3 lack Elo
coverage. Tennis, NBA and football E0/E1/SC0 were already tested in earlier phases; those results are reused.

## 18. Market vs independent vs hybrid: probability quality
Untouched 2024/25–2025/26 test; fitted on 2020/21–2022/23.

**Leakage check passed:** Elo AUC < market AUC in every league.

| League | Market log loss | Elo only Δ | Hybrid Δ [95% CI] | Market recalibrated Δ |
|---|---|---|---|---|
| D1 | 0.970 | +0.024 | **+0.014 [+0.005, +0.022]** (worse) | +0.013 |
| N1 | 0.963 | +0.015 | −0.001 [−0.008, +0.007] | −0.002 |
| F1 | 0.966 | +0.024 | +0.003 [−0.003, +0.010] | +0.003 |
| SP1 | 0.958 | +0.019 | +0.004 [−0.004, +0.012] | +0.003 |
| I1 | 0.967 | +0.020 | +0.001 [−0.007, +0.010] | −0.003 |
| P1 | 0.922 | +0.009 | +0.002 [−0.010, +0.016] | +0.001 |
| B1 | 1.008 | +0.024 | +0.007 [−0.002, +0.015] | +0.007 |
| D2 / I2 / SP2 / F2 | 1.023–1.045 | +0.016 to +0.023 | −0.002 to +0.007 (all CIs include 0) | — |

Prior results reused:

| Sport | Market log loss | Hybrid / stack log loss | Elo log loss |
|---|---|---|---|
| Tennis ATP (holdout) | 0.5883 | 0.5877 | 0.622 |
| WTA | 0.5967 | similar | — |
| NBA | 0.5809 | 0.5810 | 0.608 |
| Football E0/E1/SC0 (Gate 1) | — | every alternative worse, CI excluding 0 | — |

## 19. Does a hybrid improve calibration or discrimination? **No.**
* Hybrid better in 0 of 11 leagues; worse in D1.
* Home-win AUC is unchanged (±0.003).
* **Disagreement analysis** (hybrid versus market on the market favourite, test set):
  * where the hybrid is more than 5 pp *above* the market, the market was right. P1: market 66.5%, hybrid 75.0%,
    actual 67.9%. SP1: market 54.8%, hybrid 62.4%, actual 54.6%.
  * Elo disagreement adds noise, not information.
* **Market recalibration** (fixing the historical under-confidence) did not transfer. P1 favourites ≥ 0.70 in test:
  market 77.8% predicted versus 85.4% actual, but the recalibrated model predicted 83% for a different set that won
  78%.
* **Consensus remains the best estimator.**

## 20. Does hybrid information change multi economics?
**Moot.** No hybrid improved probability, so there are no legitimately "moved" legs. Any multi built on hybrid
disagreement would be built on noise (§19).

## 21. DATA_REQUIRED
1. Executable accumulator prices and rules (evidence class A).
2. Decision-time timestamped prices for tennis and NBA.
3. Rolling pre-match football features (xG, rest, lineups), which would need building or sourcing. Lineups at
   decision time are not available historically.
4. Prospective football high-P calibration to test the under-confidence hypothesis. This is collected automatically
   from now on.
5. More football ≥ 0.80 doubles: 23 in 6 seasons; prospectively, about 4 a season across the six Tier-1 leagues.

## 22. Evidence for each structure
* **Singles:** the only structure with no compounded margin. It is the best or equal-best at equal capital in every
  large-sample cell. It remains the default.
* **Doubles:** calibrated, but worse than singles at UK margins in tennis (CI excluding 0 at ≥ 0.70–0.80). Football
  high-P is the single positive exception, a hypothesis only.
* **Trebles:** worse, with 2–5× the variance.
* **4/5-folds:** clearly worse: −4 to −40 pp versus singles, and 43–50%+ whole-stake loss even at P ≥ 0.80.
* **Systems / round robins:** not tested. A round robin is a bundle of doubles and trebles; with no positive structure
  inside it, it cannot do better than its parts. DATA_REQUIRED only if positive-EV legs exist.
* **No bet:** strongly supported whenever leg EV ≤ 0. That is the normal state at UK prices for consensus-priced
  favourites.

## 23. Should production remain unchanged while prospective evidence accumulates? **Yes.**
Nothing here justifies:
* activating multis;
* changing the floor or the 2% rule;
* promoting a hybrid.

The paper system, decision shadow and V2-7 POS_EV logger already collect the evidence that would matter.

## 24. Next smallest evidence-driven step
**Do nothing new in production.** At the protocol's interim review, add one pre-registered prospective check:
* football high-P (≥ 0.80) favourite calibration across the six Tier-1 leagues, from the unified ledger, at 0 credits;
* plus the V2-7 POS_EV multi log.

If football under-confidence persists prospectively, the right next question is about the *probability estimate*
(a calibration adjustment for football consensus), tested on probability quality first. It is not a multi rule.
