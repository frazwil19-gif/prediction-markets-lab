# Project Objective Alignment + Bet Funnel + CLV Credit Audit (READ-ONLY)

Date: 2026-10-01. Production at master `f4720b4`: nothing modified, no threshold changed, CLV not implemented.

Sources:
* historical: `research/platform_v2/decision_replay/` (commit `9c2c218`), per-row table `reconstructed_candidates.csv.gz`;
* prospective: `paper_betting_v2/{price_snapshots,evaluation_runs,selections,decision_shadow}.csv`,
  `predictions/unified_ledger.csv`, `reports/bet_selection_v2_candidates.csv` (bsv2-4 run 2026-10-01 20:28 UTC);
* code traced: `prediction_platform/stage_a.py`, `bet_selection_v2/evaluate.py`, `paper_card/card.py`,
  `research/v2_8_analyser.py`, `decisions/{grading,money_qualification}.py`, `reports/daily_bet_card.py`,
  `scripts/run_daily_scan.py`.

## 1. Objective, restated
Estimate, for today's available markets, what is most likely to happen and how sure we are (probability,
calibration, uncertainty, context). Rank on that alone. Only then ask whether the offered payout justifies the
risk of the outcome failing. Then ask how much bankroll, if any, it deserves.

Market consensus may be an input, prior or benchmark; beating it is not the goal. CLV is one diagnostic among many.

## 2. Does the architecture match?
**The platform does (Stage A → bsv2-4 → pcard / V2-8). The legacy V1 Daily Bet / Money Card does not** (§13,
§21).

| Stage | Component | Matches? | Evidence |
|---|---|---|---|
| A, prediction | `stage_a.py` (stage-a-2) | **Yes** | Ranks by P only. "Strong" (P ≥ 0.70) is a label. Price status is shown but never suppresses or reorders a row (tested: `test_multi_sport_ranking_is_probability_only_and_nothing_suppressed`). |
| B, financial | `bet_selection_v2/evaluate.py` (bsv2-4) | **Yes, in mathematics** | It asks "does payout justify the failure risk at our P", via EV = P·(odds−1)·(1−c) − (1−P). P floor is 0.50, not 0.70. |
| B, presentation | `paper_card` (pcard-1) | Mostly | Ranks by grade (uncertainty-adjusted value), then **P**, then EV. Grade is a confidence-in-value label; it never overrides a bsv2 decision. |
| C, allocation | bsv2 bankroll block + pcard stakes; V2-8 analyser (research) | Partial | Caps, minimum stakes, ⅛ Kelly and day exposure exist. Cross-bet allocation under correlation is research-only (V2-8). Acceptable while paper-only. |
| Legacy V1 card | `decisions/grading.py`, `reports/daily_bet_card.py`, `money_qualification.py` | **No: value-first** | Grades purely on net EV and probability edge versus the exchange, and ranks by grade then **net EV**. P enters only as a 50% / 60% money floor. This is the "where is the bookmaker wrong by ≥ X" design. It still runs daily for E0/E1/SC0 and is the only component that sets `money_qualified` (currently 0). |

## 3. Can a P < 0.70 selection become a paper bet? **YES.**
Example: P = 0.57, odds 1.90, clean price.

| Gate | Value | Result |
|---|---|---|
| P ≥ 0.50 | 0.57 | pass |
| Odds ≥ 1.33 | 1.90 | pass |
| Net EV ≥ 2% | +8.3% | pass |
| Grade (EV at P−1σ, σ ≈ 0.012) | +6.0% | A |

With fresh price, ≤ 24h and a validated engine it is a **PAPER_BET, grade A**. Nothing in Stage B reads the 0.70
Stage-A label.

This has already happened prospectively:
* Ruse v Tagger, P 0.543 at 1.96 (bsv2-1);
* Sherif v Kudermetova, P 0.631 at 1.62;
* Bai, P 0.599 at 1.73 (bsv2-3, the current valid paper bet).

Historically, 125 of 193 reference qualifiers had P < 0.60. **The 70% threshold does not act as a financial
eligibility threshold. No mismatch here.**

## 4. Historical funnel (favourite side, best UK price; replay rules)
What the replay numbers mean:
* "2 / 2,925" means 2,925 **valid predictions with P ≥ 0.50**, of which 2 had a payout above fair by ≥ 2%.
* It does **not** mean only 2 matches were worth predicting. All 2,925 were predicted; their calibration is in the
  replay §4.

| Stage | B: football pre-closing | C: football close + tennis BFE | C: tennis Pinnacle-fair reference |
|---|---|---|---|
| Events (snapshots with ≥ 3 books / linked tennis) | 6,960 matches (2,925 with a P ≥ 0.50 side) | 3,991 favourites | 19,078 matches |
| P ≥ 0.50, priced | 2,925 | 3,991 | 19,149 |
| …P ≥ 0.60 / 0.70 / 0.80 | 1,421 / 653 / 203 | 2,142 / 1,081 / 396 | 13,171 / 7,417 / 3,233 |
| Odds ≥ 1.33 | 2,406 (−519, 17.7%) | 3,105 (−886, 22.2%) | 12,867 (−6,282, 32.8%) |
| EV > 0 | **2 (−2,404, 99.9%)** | **30 (−3,075, 99.0%)** | **712 (−12,155, 94.5%)** |
| EV ≥ 2% | 2 (−0) | 11 (−19, 63%) | 193 (−519, 73%) |
| Uncertainty, grade A | 2 (−0) | 10 (−1) | 190 (−3) |
| Horizon / age / spread | not reconstructable | not reconstructable | not reconstructable |
| **Final qualifier** | **2** | **11** | **193** |

**Overlapping reasons among non-qualifiers**, reference class (n = 18,956):

| Reason combination | Count |
|---|---|
| EV ≤ 0 only | 12,155 |
| EV ≤ 0 and odds < 1.33 | 6,196 |
| 0 < EV < 2% only | 519 |
| 0 < EV < 2% and odds < 1.33 | 76 |
| EV ≥ 2% but odds < 1.33 | **10** |

Football B: 2,404 failed on EV ≤ 0 only and 519 on EV ≤ 0 plus odds < 1.33. **No football favourite failed on the
odds floor alone.**

## 5. Prospective funnel (production; tennis only, as football and NBA have no rows yet)
* **All runs:**
  * unified ledger: 155 tennis predictions (124 valid; all P ≥ 0.50);
  * 6,770 price snapshots across 9 bsv2 runs;
  * paper selections: 10 (9 bsv2-1, 1 bsv2-3). Only Bai remains valid under current semantics.
* **Latest bsv2-4 run (20:28 UTC, 48 upcoming valid predictions, all priced):**
  * decisions: REJECT 39, MULTI_RESEARCH_ELIGIBLE 8, WATCH 1, **PAPER_BET 0**;
  * first failure: EV ≤ 0 29 (60%) · exchange spread too wide 15 (31%) · odds < 1.33 3 (6%) · 0 < EV < 2% 1 (2%);
  * all applicable reasons: EV ≤ 0 43 · spread too wide 15 · EV < 2% 4 · odds < 1.33 3 · outside the 24h horizon 3.
* **Engine / league state:** 0. Football leagues are PENDING_FIRST_ROW_PASS, so they will show as
  ENGINE_STATUS_INELIGIBLE until verified.

## 6. Rejection reasons
Covered in §4 and §5. Across every source, **"EV ≤ 0" is the dominant first and only failure: 60–99.9%.** The
odds floor is almost never the sole cause.

## 7. Results by probability band
Historical figures are from the tennis reference class (largest N); football B is in brackets.

| P band | N | Actual win (pred) | Avg best odds | EV > 0 | EV ≥ 2% | Qualified | Mean EV |
|---|---|---|---|---|---|---|---|
| 0.50–0.60 | 5,978 [1,504] | 54.5% (55.2) [55.3 (54.6)] | 1.72 [1.75] | 6.1% [0.13%] | 2.1% [0.13%] | 2.1% [0.13%] | −5.2% [−4.4%] |
| 0.60–0.70 | 5,754 [768] | 65.2 (64.7) [64.7 (64.5)] | 1.48 [1.49] | 4.7% [0] | 0.9% [0] | 0.9% [0] | −4.8% [−4.3%] |
| 0.70–0.80 | 4,184 [450] | 75.1 (74.8) [76.4 (74.4)] | 1.28 [1.29] | 2.7% [0] | 0.5% [0] | 0.4% [0] | −4.3% [−4.3%] |
| 0.80–0.90 | 2,502 [201] | 86.2 (84.4) [89.1 (83.3)] | 1.14 [1.15] | 1.6% [0] | 0.2% [0] | **0** | −3.9% [−4.2%] |
| 0.90+ | 731 [2] | 95.6 (92.8) | 1.05 | 1.0% | 0 | **0** | −2.7% |

**Prospective tennis, all runs, per prediction (any snapshot):**

| P band | n | Ever EV > 0 | Ever EV ≥ 2% | Ever PAPER_BET |
|---|---|---|---|---|
| 0.50–0.60 | 47 | 38% | 11% | 4% |
| 0.60–0.70 | 51 | 29% | 18% | 2% |
| 0.70–0.80 | 31 | 52% | 39% | 25%, almost all under the superseded bsv2-1 |
| 0.80–0.90 | 10 | 70% | 30% | 0 |
| 0.90+ | 16 | 75% | 38% | 0 |

Prospective "ever EV > 0" is inflated by snapshots with wide exchange spreads, where the mid-probability is
unreliable. bsv2-3 removed those; at the latest bsv2-4 run, EV > 0 is 0–33% per band.

**Reading:**
* Calibration holds in every band, so the probability of winning is real.
* Financial attractiveness *falls* as P rises. Mean EV at the best UK price is about −4 to −5% at every P because of
  the bookmaker margin. The payout gets shorter faster than the certainty gets higher.
* Neither "higher P = better bet" nor "higher EV = better prediction" holds. The replay showed EV 6%+ bets did
  *worse*.

## 8. Why P ≥ 0.80 produced zero historical qualifiers

| Class | P ≥ 0.80 rows | Odds < 1.33 | EV ≤ 0 | 0 < EV < 2% | EV ≥ 2% but odds < 1.33 | Median fair / best odds / EV |
|---|---|---|---|---|---|---|
| Football B | 203 | 203 | 203 | 0 | 0 | 1.21 / 1.16 / −4.1% |
| Football + tennis C | 396 | 396 | 393 | 3 | 0 | 1.19 / 1.14 / −3.7% |
| Tennis reference | 3,233 | 3,233 | 3,185 (98.5%) | 43 | **5** | 1.17 / 1.12 / −3.6% |

Answer: **A, payout genuinely below fair**, in 98.5–100% of cases. The best UK price sits about 4% under fair,
which is the bookmaker margin. **B, the odds floor**, is the sole cause in only 5 of 3,233 cases. C (2% EV) affects
0–43, D (uncertainty) 0, and E (data limitations) is not the cause.

There is also an arithmetic fact. With a 1.33 floor, a single at P = 0.80 needs a price 6.4% above fair; at 0.85,
13%; at 0.90, 20%. So the floor is **structurally a probability ceiling of about 0.77 for singles**, even though
in practice EV ≤ 0 would remove those rows anyway.

## 9. Effect of the odds floor
* **Historical:** sole cause for 0 football and 10 tennis-reference rejections. The 10 went 8–2 at average odds
  1.28, ROI +2.5% (n too small).
* **Prospective:** first failure 3 of 48 in the latest run (P 0.8–0.97).
* **Conceptual:** it is a "meaningful payout" rule from `thresholds.yaml payout_policy`. Its side effect is
  excluding P ≳ 0.77 from singles, which is where `MULTI_RESEARCH_ELIGIBLE` (P ≥ 0.80) sends them. **Frozen,
  unproven, small practical effect.**

## 10. Effect of EV > 0
The only gate with a clear historical effect:

| Group | ROI (95% CI) | N |
|---|---|---|
| EV ≤ 0 | −4.6% (−5.6, −3.6) | 18,351 |
| EV > 0 | +2.2% (−3.1, +7.8) | 798 |

The EV > 0 group's CI includes 0. EV > 0 is exactly the condition "payout exceeds what the failure probability
requires".

## 11. Effect of the 2% EV threshold
**Confirmed as a FROZEN PROSPECTIVE POLICY PARAMETER, not a proven optimum.** This is recorded in the pcard-1
pre-registration amendment A1 ("frozen ≠ optimal").

| EV band | N | ROI |
|---|---|---|
| < 0 | 18,315 | −4.7% |
| 0–1% | 426 | +3.1% |
| 1–2% | 205 | +0.9% |
| 2–4% | 140 | +3.1% |
| 4–6% | 42 | +6.5% |
| 6–10% | 18 | −10.6% |
| 10%+ | 3 | −20.7% |

The 0–2% bands are not worse than 2–4%. Every positive band's CI includes 0. Prospectively, the
`decision_shadow.csv` analytical ledger (live since 2026-10-01 20:28) records every band with real timestamps.
Nothing is changed.

## 12. Effect of uncertainty (grade A, EV at P−1σ)
* **Historical:** removed 3 of 196, 1 of 11 and 0 of 2. The current σ (about 1.2–2.2 pp) is small relative to
  prices, so grade B is rare.
* It is a ranking/label, not a gate.
* Tennis σ historically lacked the exchange-width term, so it is a lower bound.

## 13. Gates serving the wrong conceptual purpose?
1. **1.33 odds floor:** stated as a payout floor, it also acts as an implicit P ceiling of about 0.77 for singles.
   Not harmful in data, since EV ≤ 0 dominates. It conceptually contradicts "predict first" only at high P.
   **Flag for your decision; no change.**
2. **The legacy V1 grading** (`grading.py`: net-EV / probability-edge grades, ranked by net EV) **is a value-first
   engine** and is the only real-money-capable path. It predates the probability-first objective. **This is the
   genuine drift (see §21).**
3. **bsv2 P ≥ 0.50 floor:** excludes underdogs entirely. That is consistent with "most likely to occur", but it is a
   design choice, not evidence.
4. Everything else serves its stated purpose.

## 14. Are Stages A / B / C separated?
**A: yes.** Payout never alters P or rank. **B: yes**, as a separate module that reads P and never writes it.
**C: partly.** Allocation is policy caps plus hypothetical stakes, with V2-8 research. The legacy V1 card merges B
and C into a value-ranked list.

**The deeper reason the system behaves "value-like":** every validated engine's P *is* a market-consensus estimate
(Betfair mid, median of UK books, de-vigged average). These won the probability research; independent models did not
beat them. So for a typical bet, P ≈ the market's fair price. EV > 0 can then only come from **one book pricing above
the consensus**, which is price dispersion. That is a property of the probability source, not of Stage B. A
probability-first engine whose probabilities equal the market's will mostly find "no bet". Strong predictions at
fair-or-worse prices are correctly *not* bets. Changing gates cannot create value that the probabilities do not
contain. Only an estimator with information beyond consensus, or line-shopping across many books, could.

## 15. Role of CLV
One diagnostic. It answers: "is the price we took at decision time better than the later, more efficient price?"
It is **not** prediction quality, not the objective, and does not override calibration.

Monitor it alongside:
* accuracy, calibration, Brier and log loss;
* expected vs actual wins;
* paper W/L and ROI;
* drawdown, average odds and payout;
* breakdowns by P, odds and EV band, and by grade, model and sport.

Its practical value is speed: CLV has far lower variance than ROI.

## 16. CLV API-credit mechanics (The Odds API v4 docs, checked 2026-10-01)

| Call | Cost |
|---|---|
| `/v4/sports/{sport}/odds` | markets × regions. h2h + uk = **1 credit**, however many events are returned. |
| `eventIds=` filter on the same endpoint | Same cost (1 credit for h2h/uk), returns only the named events. |
| `/v4/sports/{sport}/events/{id}/odds` | unique markets *returned* × regions; h2h/uk = 1 credit, possibly 2 if `h2h_lay` counts as a returned market (unverified). |
| `/events` | **free** |
| Any call returning no events | **free** |

* **Exchange data:** Betfair lay odds come **automatically** with h2h as market `h2h_lay`, so exchange back/lay and
  UK books arrive in one call.
* **Cheapest call:** sport-level odds with an `eventIds` filter, h2h, uk = **1 credit** and includes the exchange
  back/lay. One call covers every paper bet in that sport key at that moment. Football 15:00 Saturday kick-offs share
  a call.

## 17. CLV monthly cost (paper-selection triggered, one closing capture per bet, worst case one call per bet)

| Paper bets / week | 1 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|
| CLV credits / month | ≤ 5 | ≤ 13 | ≤ 22 | ≤ 44 | ≤ 87 |
| NORMAL total (≈ 390 base) | 395 | 403 | 412 | 434 | 477 |
| BUSY total (≈ 469 base) | 474 | 482 | 491 | 513 | 556 |
| STRESS: core at caps, shadow fully throttled (455) | 460 | 468 | 477 | 499 | 542 |

Doubling to two captures (e.g. T−60 and T−10) doubles the CLV line.

Current bet rate is about 1 per week under bsv2-4. With football and NBA it might reach 2–5 per week, a reasonable
expectation rather than a forecast.

## 18. Does it fit in 500?
**Yes at ≤ 5 bets per week in every scenario. Yes at 10 per week in NORMAL.** In BUSY or STRESS at 10–20 per week
it fits **only** if CLV sits in the priority order **below Tier 1 and above Tier 2/3 shadow**. The existing dynamic
throttle then shrinks shadow collection to pay for it. Tier 1 is never sacrificed. No purchase is needed.

## 19. Cheapest CLV architecture (recommendation; not implemented)
1. On PAPER_BET, register `(selection_id, sport_key, event_id, commence_time)` in an append-only queue. This costs 0
   credits, and the decision is never modified.
2. A capture job looks for registered bets starting within the next window and makes **one** filtered sport-odds call
   per sport key (1 credit) when it finds one.
   * It records UK prices, the exchange back/lay mid, the capture time and the minutes before start.
   * It then computes CLV against the exchange mid (de-vigged) and against the best UK price.
3. **The scheduling constraint is a real blocker.** GitHub cron runs here have started **2–7 hours late**
   (`SCHEDULE_RELIABILITY_AUDIT.md`; today 13:45 / 14:19 / 20:28 versus configured times). A true T−10 capture is
   not achievable on GitHub schedules. Options:
   * **(a)** an hourly or more frequent capture job, recording the actual minutes before start (CLV labelled by
     timing quality);
   * **(b)** a scheduled task on the Claude side or on your Mac. Precise timing; needs your setup decision.
   * **(c) Zero-credit fallback, available today:** compare each paper bet's decision price with the **last
     already-paid pre-start snapshot** from existing scans (tennis 06:30 / 15:30). This gives partial coverage and
     "pre-close" rather than closing value. **Football gets none**, because its one daily scan is the decision scan.
4. If you approve, start with (c) plus a pre-registered definition, then (a) or (b).

## 20. Should a multidimensional financial decision be researched?
**Conceptually yes, as a question for later; not yet as a build.**
* The binary EV ≥ 2% rule is *consistent* with the objective. EV is exactly "probability × payout versus probability
  of failure". Uncertainty enters through the grade, and risk enters through staking.
* It is cruder than the objective in three ways:
  1. a hard 2% cliff where evidence shows no discontinuity;
  2. uncertainty and historical support do not move the gate;
  3. bankroll growth (Kelly-type) already weighs P, payout and variance jointly, which is arguably the principled
     "multidimensional" form.
* Prerequisites before considering any alternative (no weights or score now):
  1. prospective calibration of the *qualified* set by P band;
  2. realised returns by EV band from `decision_shadow.csv` with real timestamps, with enough N per band (Evidence &
     Promotion Protocol interim precision);
  3. CLV by EV band;
  4. stability across sports and time.

  Then compare frozen-binary versus continuous-EV/Kelly sizing **prospectively, pre-registered**. That is not
  historical optimisation.

## 21. Architecture discrepancies needing your approval before any modification
1. **Legacy V1 Daily Bet / Money Card** (value-first grading, ranked by net EV, the only `money_qualified` path).
   Options: (a) mark it SUPERSEDED / legacy-research-only and keep it running as a comparison; (b) retire its
   money-qualification output; (c) leave as is. **Recommendation: (a).** Real money stays off either way.
2. **The 1.33 odds floor as an implicit P ≈ 0.77 ceiling for singles.** Decide whether it is an intended payout rule
   (keep) or should become a probability-aware payout rule. Not for this cohort; it is frozen.
3. **CLV collection:** approve the design and its scheduling (§19), with CLV priority below Tier 1.

Nothing else. Stage A, bsv2-4 and pcard-1 match the stated objective. The P < 0.70 question is answered **yes**.
