# Historical Decision Replay / Bet-Characteristics Audit — REPORT

Date: 2026-10-01. Pre-registration: `PREREGISTRATION.md` (commit `918966e`, before any result). Script:
`scripts/decision_replay.py`. Numbers: `RESULTS.json`. Tables: `reconstructed_qualifiers.csv`,
`reconstructed_candidates.csv.gz`, `threshold_grid_*.csv`.

This was read-only research. No production file, rule, threshold, engine, state or ledger was changed, and no paper
bet was written. Nothing was purchased. The raw inputs were staged read-only from Fraser's Mac and their SHA-256
hashes verified.

**Bottom line.** The probabilities are well calibrated everywhere. Under the frozen rules, value bets are rare: about
0.1–1 per 100 favourites. Their returns cannot be told apart from zero in any evidence class. Backing favourites
without a value filter reliably loses 3–4.6%. Historical data supports the probability engines. It neither supports
nor refutes the betting rules, and it cannot show a positive edge.

---

## 1. Historical datasets available
| Engine | Source | Seasons | N | Has |
|---|---|---|---|---|
| ATP match winner | Betfair BASIC LTP (frozen engine) + tennis-data.co.uk | 2021–2025 | 12,202 (10,765 linked to tennis-data) | P at T−30; B365 / PS close; BFE close 2025 only |
| WTA match winner | as ATP | 2021–2025 | 10,352 (9,229 linked) | as ATP |
| Football 1X2 E0 / E1 / SC0 | football-data per-book | 2020/21–2025/26 | 6,960 matches | B365 / WH / BW / PS / 1XB / BF at **pre-closing** and **closing** snapshots |
| Football 1X2, 13 other target leagues | xgabora (V2-18 pin) | 2020/21–2025/26 | 1,845–3,356 per league | Bet365 close + cross-book Max |
| NBA moneyline | wippa / OddsPortal | 2016-17 → 2025-26 (two seasons absent) | 7,894 games | one **average** closing price |

## 2. Data-quality and timestamp audit
* **No dataset has exact quote timestamps.**
* **Football:** "pre-closing" is football-data's collection, usually Friday or Tuesday for the next fixtures, so 1–3
  days before kick-off. "Closing" is at kick-off. P and price come from the same snapshot.
* **Tennis:** the frozen engine P is the Betfair LTP at T−30 min. tennis-data odds are "most recent before play", with
  no time. V2-6D proved that pairing these leaks outcomes (spurious +21% ROI), so that pairing is class D.
  * tennis-data needed a validity screen: 81 ATP and 12 WTA corrupt rows were removed, same as V2-6D.
  * Linkage: 0 ambiguous matches, 99.95% winner agreement.
* **NBA:** an average price only, so EV = −overround (−4.3% mean) by construction.
* **Gates not evaluable for any dataset:**
  * ≤ 24h horizon;
  * price age ≤ 240 min;
  * exchange spread ≤ 0.03.

  The replay therefore applies P ≥ 0.50, net EV ≥ 2%, odds ≥ 1.33 and the pcard-1 grade (EV at P−1σ). Tennis σ is
  the calibration SE only, a lower bound on live σ.

## 3. Replayability by sport
| Sport | Class | What it can tell us |
|---|---|---|
| Football E0 / E1 / SC0, pre-closing | **B — SAME-TIME PROXY** (primary) | closest analogue to the live 24–48h scan |
| Football E0 / E1 / SC0, closing | C — CLOSING PROXY | closing efficiency |
| Tennis, BFE close vs B365 close (2025) | C — CLOSING PROXY | exchange-fair vs UK book, aligned; tiny N |
| Tennis, Pinnacle close vs B365 close | C — REFERENCE | the *concept* (sharp fair vs UK book); **not the frozen engine** |
| Tennis, frozen T−30 P vs B365 close | **D — NOT REPLAYABLE** | excluded from finance (19,290 rows) |
| NBA | **D** | probability only |
| Other football leagues (xgabora) | **D** for finance (Max is an aggregate) | probability only |

**No class A (executable-like) evidence exists in any free dataset.**

## 4. Probability performance (favourite side; the strong region is P ≥ 0.70)
| Engine | N | Mean P | Win | Brier | Log loss | Slope [95% CI] | Strong ≥ 0.70: pred → actual (n) | Longest failed strong run |
|---|---|---|---|---|---|---|---|---|
| ATP | 12,202 | 0.686 | 0.681 | 0.201 | 0.585 | 1.06 [0.98, 1.13] | per band below | 4 |
| WTA | 10,352 | 0.679 | 0.674 | 0.204 | 0.592 | 1.08 [1.00, 1.16] | per band below | 5 |
| NBA | 7,894 | 0.678 | 0.680 | 0.205 | 0.596 | 1.02 [0.92, 1.12] | per band below | 5 |
| Football E0 / E1 / SC0 (closing consensus) | 6,960 | 0.508 | 0.515 | 0.233 | 0.658 | 1.06 [0.96, 1.17] | 0.774 → 0.800 (676) | 4 |
| N1 | 1,869 | 0.558 | 0.558 | 0.224 | 0.637 | 1.10 [0.93, 1.28] | 0.783 → 0.802 (348) | — |
| D1 | 1,845 | 0.532 | 0.529 | 0.230 | 0.652 | 1.07 [0.88, 1.25] | 0.777 → 0.773 (242) | — |
| F1 | 2,076 | 0.517 | 0.524 | 0.234 | 0.661 | 1.06 [0.86, 1.25] | 0.761 → 0.775 (182) | — |
| SP1 | 2,368 | 0.509 | 0.541 | 0.232 | 0.655 | 1.15 [0.97, 1.33] | 0.761 → 0.791 (210) | — |
| I1 | 2,397 | 0.526 | 0.541 | 0.230 | 0.652 | 1.17 [0.99, 1.35] | 0.750 → 0.780 (250) | — |
| P1 | 1,916 | 0.533 | 0.569 | 0.218 | 0.625 | 1.23 [1.06, 1.41] | **0.774 → 0.866 (365)** | — |
| B1 | 1,889 | 0.508 | 0.518 | 0.235 | 0.663 | 1.17 [0.95, 1.40] | 0.744 → 0.737 (118) | — |

Lower-division leagues (E2, E3, SP2, D2, I2, F2) have only 9–40 strong predictions each. Full tables are in
`RESULTS.json`.

**Bands, predicted vs actual:**

| Band | ATP | WTA | NBA | Football E0 / E1 / SC0 |
|---|---|---|---|---|
| 70–75 | 72.4 → 72.0 | 72.4 → 72.1 | 72.4 → 74.6 | 72.5 → 74.9 |
| 75–80 | 77.4 → 77.5 | 77.3 → 75.6 | 77.5 → 76.6 | 77.3 → 78.9 |
| 80–85 | 82.4 → 82.6 | 82.4 → 83.0 | 82.4 → 81.8 | 82.3 → 86.0 |
| 85–90 | 87.4 → 87.0 | 87.4 → 89.8 | 87.3 → 87.3 | 87.1 → 91.5 |
| 90+ | 93.9 → 95.1 | 93.2 → 94.2 | 91.4 → 94.4 | (n = 3) |

* **Season stability:** tennis Brier was 0.198–0.207 in every year, with no drift.
* **Losing runs:** the longest runs of failed strong predictions were 4–5 in a row. That is normal for P ≈ 0.8.
* **Football:** favourites win slightly *more* often than consensus says, i.e. mild under-confidence. This is most
  marked in Portugal: strong picks at 77% won 87%. That is a hypothesis to watch in shadow, not a finding to act on;
  it is 1 of 13 leagues examined.

## 5–7. Reconstructed current-rule bets, W/L and financial result
| Class | Favourites considered | Qualifiers | Per 100 favourites | Grade A / B | W–L | Mean est. EV | ROI [95% CI] | Max DD (u) | Longest losing run |
|---|---|---|---|---|---|---|---|---|---|
| **B — football pre-closing (primary)** | 2,925 | **2** | 0.07 | 2 / 0 | 1–1 | +8.8% | −2.5% [−100%, +95%] | 1.0 | 1 |
| C — football closing + tennis BFE 2025 | 3,991 | 11 (8 football, 3 tennis) | 0.28 | 10 / 1 | 5–6 | +6.3% | −13.9% [−67%, +43%] | 2.1 | 2 |
| C — tennis Pinnacle-fair vs B365 (reference) | 19,149 | 193 | 1.0 | 190 / 3 | 110–83 | +4.0% | **+2.2% [−9.5%, +14.8%]** | 10.1 | 4 |

Every qualifier is in `reconstructed_qualifiers.csv`. Under the frozen rules the historical system would have
placed **about 2 football bets in 6 seasons** at pre-closing prices. Even the most permissive aligned reference
(tennis Pinnacle-fair) gives about 1 bet per 100 favourites, roughly 39 a year.

## 8–10. Performance by band (reference class, n = 193 qualifiers; "all favourites" in brackets)
* **P band** (qualifiers): <60: 125 bets, +8.1% · 60–65: 36, −8.4% · 65–70: 16, −4.6% · 70–75: 11, −22.9% ·
  75–80: 5, +9%.
  * Qualifiers are mostly *coin-flip favourites*. At P ≥ 0.80 there were **zero** qualifiers in any class, because
    UK books never priced strong favourites above fair by 2%.
  * The 80%+ region produces no singles; this is the "strong prediction ≠ valid bet" finding in historical form.
* **Odds band** (qualifiers):

  | Odds band | Bets | ROI |
  |---|---|---|
  | 1.33–1.49 | 14 | −0.5% |
  | 1.50–1.74 | 65 | −7.2% |
  | 1.75–1.99 | 60 | −6.9% |
  | 2.00+ | 54 | +24.4% |

  The 2.00+ group are "favourites" by the reference that B365 priced as underdogs; this is small, noisy and
  outlier-prone. All favourites lose in every odds band from <1.20 to 1.75–1.99, from −1.7% to −6.9%. The exception is 2.00+ (136 bets, +14.1%), the same price-disagreement outliers.
* **EV band** (qualifiers):

  | EV band | Bets | ROI |
  |---|---|---|
  | 2–4% | 130 | +3.2% |
  | 4–6% | 42 | +6.5% |
  | 6–10% | 18 | −10.6% |
  | 10%+ | 3 | −20.7% |

  For all favourites: EV < 0 gave −4.7% (18,315 bets) and EV 0–2% gave +2.4% (631). **High apparent EV does not
  predict higher return.** Large computed edges are mostly price errors or stale quotes, as V2-6H found.

## 11. Sport / league breakdown
* **Tennis reference:** ATP 99 bets, +5.0%; WTA 94 bets, −0.6%.
* **Football closing qualifiers:**

  | League | Bets | ROI |
  |---|---|---|
  | E0 | 3 | −42% |
  | E1 | 3 | +43% |
  | SC0 | 2 | −24% |

* **Football all-favourites:**

  | League | Pre-closing ROI | Closing ROI |
  |---|---|---|
  | E0 | −3.1% | −2.4% |
  | E1 | −5.4% | −5.0% |
  | SC0 | +1.5% | +0.2% |

  SC0 is the only league near break-even, consistent with its under-confidence.
* NBA and the other leagues are not financially replayable.

## 12. Season stability
* **Football pre-closing, all favourites, by season:**

  | Season | ROI |
  |---|---|
  | 2020/21 | −3.9% |
  | 2021/22 | −3.1% |
  | 2022/23 | −0.6% |
  | 2023/24 | +3.4% |
  | 2024/25 | −5.9% |
  | 2025/26 | −7.7% |

  One positive season in six.
* **Tennis reference qualifiers, by year:**

  | Year | Bets | ROI |
  |---|---|---|
  | 2021 | 51 | −5.0% |
  | 2022 | 46 | −1.0% |
  | 2023 | 39 | −1.8% |
  | 2024 | 21 | +0.1% |
  | 2025 | 36 | +22.3% |

  The whole positive total comes from 2025. There is no stable sign.

## 13. Gate / reject analysis
Tennis reference class; this is where N allows a reading.

| Group | N | Win / expected | ROI [95% CI] |
|---|---|---|---|
| Accepted, grade A | 190 | 57.4% / 58.7% | +2.8% [−9.9, +15.9] |
| Accepted, grade B (fails P−1σ) | 3 | — | −33% |
| Rejected **only** by odds < 1.33 | **10** | 80% / 80% | +2.5% [−36, +29] |
| Rejected **only** by EV < 2% (but EV > 0) | 519 | 62.2% / 60.9% | +2.3% [−4.2, +9.3] |
| No value (EV ≤ 0) | 18,351 | 68.2% / 67.8% | **−4.6% [−5.6, −3.6]** |

* **The EV > 0 filter is the only gate with a clear historical effect.** It separates a group losing a reliable 4.6%
  from groups that cannot be told apart from zero.
* **The 1.33 odds floor removed almost nothing.** Only 10 short-priced favourites ever showed ≥ 2% value against
  B365. The floor is neither shown harmful nor shown useful.
* **The 2% EV floor removed 519 bets** that performed the same as the accepted ones (+2.3% vs +2.8%). It mainly cut
  sample size.
* **The P−1σ grade** split off only 3 bets, which is uninformative.

Football gives the same pattern with tiny N. No gate is changed from this.

## 14. Threshold sensitivity — diagnostic only
* The grid had 840 cells per class. Of the 167 reference-class cells with n ≥ 30, **none** has a 95% CI excluding
  zero, in either direction. That is what one expects when there is no detectable signal; with 840 cells some would
  look significant by chance anyway.
* The structure is the opposite of "more selective is better". At P ≥ 0.60, ROI *falls* as the EV floor rises: 0% →
  +3.7%, 2% → −7.2%, 5% → −29.8% at odds ≥ 1.20, with the same pattern at every odds floor. Raising the odds floor
  changes little.
* The frozen cell (odds 1.33, EV 2%, 1σ) at P ≥ 0.60 had 68 bets, ROI −8.6% [−28%, +10%], positive in 1 of 5
  seasons.
* There is no broad, stable, monotonic region that would justify any threshold. **Nothing is recommended or changed.**

## 15. Drawdown and losing streaks
* **Strong predictions:** the worst runs were 4–5 consecutive failures in tennis, NBA and football.
* **Reference qualifiers (193 bets at avg odds 1.80):** max drawdown 10.1 units; longest losing run 4.
* **All favourites at the best price:** losing streaks up to 8–10, and drawdowns of 90–860 units over the full
  samples, because the expectation is negative.

## 16. Bankroll simulations
Reference class only; class B (2 bets) and class C (11 bets) barely move a bankroll. The bsv2 replay runs in
chronological order with a 5% per-bet cap, a 10% daily cap and minimum stakes, over 193 bets in 5 years.

| Start | 0.5% | 1% | 2% | ⅛ Kelly (2% cap) | 1% max DD | 2% max DD |
|---|---|---|---|---|---|---|
| £30 | £30.63 | £31.07 | £31.63 | £29.61 | 10% | 20% |
| £50 | £50.98 | £51.78 | £52.79 | £49.17 | 10% | 20% |
| £100 | £101.96 | £103.61 | £105.65 | £98.53 | 10% | 20% |

* **Resampling, 10,000 paths at £50 / 1%:**
  * bootstrap of realised results: median £51.64; 5–95% range £42.3–£63.5; P(finish below start) 40%;
    P(drawdown ≥ 20%) 8%; ruin 0%;
  * model-P paths (which assume the edge is real): median £53.55, P(loss) 29%.
* **At 2%:** P(drawdown ≥ 20%) is 51–61%.
* **Stress test, not a policy:**

  | Bankroll | Flat stake | % of bankroll | Max drawdown | Outcome |
  |---|---|---|---|---|
  | £30 | £5 | 16.7% | 95% | ruined |
  | £50 | £5 | 10% | 81% | survived |
  | £30 | £3 | 10% | 81% | survived |

  The same bets that are harmless at 1% wipe out a small bankroll at £5 flat.
* **Scale:** the best-case reference class turned £50 into about £51.8 over **five years** at 1%.

## 17. Limitations
1. No class A data; every financial row is a proxy.
2. Horizon, price-age and spread gates could not be applied.
3. Closing-at-kick-off quotes over-state executability. Outlier book quotes may be stale, voidable or size-limited.
4. The tennis reference uses Pinnacle, not our engine. Tennis σ is a lower bound.
5. Football pre-closing (the best analogue) produced only 2 qualifiers, so its financial result is uninformative.
6. NBA, the other 13 leagues and DC are financially unreplayable with free data.
7. Survivorship / linkage: 11–12% of tennis matches were unlinked, with no evidence of bias (winner agreement
   99.95%).
8. Multiple testing across 840 cells × 3 classes plus every breakdown in this report.

## 18. Evidence for and against a positive edge
* **For:**
  * aligned sharp-fair vs UK-book value in tennis gave +2.2–2.8%, in the right direction;
  * EV > 0 groups did better than EV ≤ 0 groups (−4.6%), so the value filter does sort out losing bets;
  * calibration is excellent, so P is trustworthy.
* **Against:**
  * every CI includes zero, with one stable result only in the negative direction (no-value favourites);
  * the primary class B produced 2 bets;
  * higher computed EV did *worse* (price errors);
  * the reference result is carried by one year (2025);
  * football closing qualifiers were −14% (n = 11).
* **Verdict:** **no evidence of a negative-expectation problem *after* the value filter, and no evidence of a positive
  edge.** What the data does show clearly: betting accurate favourites without value loses about 3–5% per bet.

## 19. Small-stakes live-readiness assessment (questions A–I)
* **A. Does historical probability evidence support the system?** **Yes, strongly**, for ATP, WTA, NBA and football
  (all leagues; grade B leagues are slightly under-confident).
* **B. Does legitimate historical financial evidence support the betting rules?** **No.** It neither supports nor
  refutes them. The frozen rules generate too few historical bets: 2 in class B.
* **C. Strongest evidence:** tennis ATP/WTA (probability) and the tennis reference concept (finance, weakly
  positive, not significant).
* **D. Insufficient evidence:** football betting economics (N = 2 / 8), NBA and all non-E0/E1/SC0 leagues
  (unreplayable financially).
* **E. Major limitations:** no executable-like timestamped prices (§17).
* **F. An obvious negative-expectation problem?** Not inside the qualified set. Yes for unfiltered favourite-backing,
  which the rules already exclude.
* **G. Evidence consistent with a positive edge?** Consistent with a small one, but equally consistent with zero.
* **H. What prospective evidence would materially change confidence?** Real decision-time prices showing two things:
  1. paper qualifiers whose price **beats the closing fair price** (CLV) — the fastest, lowest-variance signal of real
     value, informative after tens of bets rather than hundreds;
  2. prospective calibration of the qualified bets in line with P.
* **I. Is a £30–£50 experimental live bankroll scientifically defensible yet?** **Not yet. This does not justify a
  SMALL-STAKES MONEY-ELIGIBILITY REVIEW CANDIDATE.** Calibration is ready. What is missing is any decision-time
  evidence that qualified prices hold value (CLV) and that execution matches paper. The downside of a £30–£50 trial
  at 0.5–1% stakes is very small: the 5–95% range is about ±£8 over hundreds of bets. So the real constraint is the
  *evidence*, not the risk.

## 20. Exact recommendation: what to collect next
All of this is within the frozen system.
1. **Closing-line value for every paper selection** (and decision-shadow row).
   * Record the best UK price and the exchange mid at about T−10 min for each paper selection.
   * This needs one extra Odds API snapshot per day per active league/tour, so it would need approval as a production
     change.
   * It is the single most informative missing measurement.
2. **Accumulate prospective paper qualifiers**, expected at about 1–3 a week, and report calibration of the qualified
   set separately from all predictions.
3. **Use `decision_shadow.csv`** to repeat this audit prospectively, with real timestamps, at the protocol's interim
   trigger.
4. **Re-assess money eligibility when either:**
   * about 30–50 paper qualifiers show mean CLV > 0 with a CI excluding 0; or
   * calibration of the qualified set reaches the protocol's interim precision.

   Whichever comes first. A small-stakes trial would then be 0.5–1% stakes, £30–£50, with the bsv2 caps, and a
   **predefined stop** at a 20% drawdown.
5. **Optional, Fraser's decision; nothing purchased.** One month of The Odds API historical plan (about $30) would
   allow a class-A replay of tennis at decision time. That would answer B and G months sooner.

Return to normal operation; production is unchanged.
