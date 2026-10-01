# V2-7H Historical Betting-Card Backtest (singles / doubles / trebles): Report (2026-09-30)

**Research only.** Production, the V2-7 prospective logger (frozen, independent), bsv2-3, frozen engines and thresholds are all
unchanged. Nothing was purchased. No odds were manufactured: SYNTH prices are labelled synthetic and are used only to describe risk.

Provenance:
- Pre-registration: `PREREGISTRATION.md` (commit `2d81a9b`). Amendments A1 and A2 were made before any result; A3 is
  reporting and disclosure only (`AMENDMENTS.md`).
- Code: `scripts/v2_7h_card_backtest.py`, `src/prediction_markets_lab/research/card_backtest.py`. Tests:
  `tests_research/test_v2_7h_card_backtest.py`.
- Numbers: `RESULTS.json`, `calibration_summary.csv`, `simulation_summary.csv`, `margin_compounding.csv`, `DATA_INVENTORY.json`.

**Evidence labels.**
- **PROB**: probability only.
- **ASOF-FB**: football per-book pre-closing prices, with P from the same snapshot. This is the only decision-time price set we hold.
- **CLOSE-DIAG**: a closing-price diagnostic.
- **SYNTH**: synthetic prices, used for risk description only.
- Every multi price is an **INDICATIVE MULTI PRICE** (a same-book product of leg prices), **not** an executable accumulator price.

## Reproducibility
- **Full run:** `python scripts/v2_7h_card_backtest.py --data <data dir>` (about 11 min), then `python scripts/v2_7h_summaries.py`.
- **Seeds** are fixed (20260930). Re-running the NBA calibration, independence and S1 simulation sections reproduced `RESULTS.json` byte-for-byte.
- **Research tests:** 63 passed. **Production suite:** 1177 passed, 8 skipped (unchanged).

## 1. Data inventory and audit
| source | sport | period | events | P (frozen engine) | prices | timestamp semantics | A prob | B indicative price | C executable |
|---|---|---|---|---|---|---|---|---|---|
| Betfair BASIC (interim datasets) | ATP / WTA | 2021–25 | 12,202 / 10,352 | LTP T−30 multiplicative | LTP only (same source as P) | at/before T−30; ~1% contaminated by early starts | ✅ | ✗ | ✗ |
| tennis-data.co.uk | ATP / WTA | 2021–25 | 13,171 / 12,302 rows; 88–89% linked | — (PS-close de-vig as a *reference* estimator) | B365, PS close; BFE ~5% (2025) | **closing only**, untimestamped; corrupt rows screened | ✅ | CLOSE-DIAG only | ✗ |
| wippa / OddsPortal | NBA | 2016-17 → 2025-26 (19-20, 20-21 absent) | 10,527 | average close, proportional | one average price | closing | ✅ | ✗ | ✗ |
| football-data.co.uk (processed) | E0 / E1 / SC0 1X2 | 2020/21 → 2025/26 | 6,960 matches (2,992 favourites ≥ 0.5) | consensus median of ≥ 3 books, same snapshot | per-book B365 / WH / BW / BF(24/25) / PS … | "opening" = pre-closing collection (Fri/Tue); closing at kick-off; untimestamped | ✅ | ✅ | closest available; multis indicative |

- Live V2-6 / V2-7 files are **excluded**, because they are an independent prospective stream.
- **Every holdout had already been opened by earlier phases.** Holdout results here are "previously exposed", not pristine.
- The V2-6D lesson is enforced: **the frozen tennis T−30 P is never paired with a closing bookmaker price.**
- No blocking integrity issue was found. Known issues are carried as sensitivities:
  - tennis LTP early-start contamination;
  - corrupt tennis-data rows (screened);
  - no WH or BF in football 2025/26.

## 2. Method (pre-registered)
- **Legs:** the favourite side (P ≥ 0.5) from each frozen engine.
- **Calibration universe U1:** disjoint within-day cards, hash-ordered, with distinct events and distinct participants.
- **Overlap universe U2:** all within-day combinations, computed exactly via symmetric polynomials.
- **Independence test:** the within-day pairwise residual product E[(y_i − p_i)(y_j − p_j)]. This is exactly the error that the
  product rule makes for a double.
- **Uncertainty:** 2,000-resample day-cluster bootstrap. Holm correction across the 12 P1 tests and the 4 P2 tests.
- **Daily engine simulation:** selection functions receive outcome-free frames (a test checks that permuting outcomes cannot
  change a selection). One card per strategy per k per sport-day. Equal total stake s ∈ {0.5, 1, 2, 3, 5}% of the current bankroll:
  k singles at s/k each versus the k-fold at s. Bankroll compounds daily.
- **Strategies:**
  - HIGH_P population: S1 top-P ≥ 0.70; S2 development-supported bands (**empty**, A3); S5 lowest σ/p.
  - POS_EV population: S3 top-EV; S4 top-Kelly; S6 top-P among EV > 0, same book.
  - The two populations are never pooled.

## 3. Probability calibration: P1, holdout, Holm across 12 tests
Bias is realised − predicted, in percentage points, with a day-cluster 95% CI.

| sport | singles | doubles | trebles |
|---|---|---|---|
| ATP | −0.05 [−1.2, +1.1] ✅ | −0.6 [−2.5, +1.3] ✅ (half-width 1.9) | −1.3 [−3.5, +0.9] ✅ |
| WTA | −1.0 [−2.3, +0.3] ✅ | −1.7 [−3.7, +0.4] ⚠️ imprecise (half-width 2.03 vs the 2.0 limit) | **−2.6 [−5.1, −0.2]**: Holm p = 0.43, passes the rule (half-width 2.4); see note |
| NBA | −0.1 [−1.9, +1.5] ✅ | +0.3 [−2.6, +3.0] ⚠️ imprecise | +1.0 [−2.1, +4.2] ⚠️ imprecise |
| Football | −1.0 [−4.1, +1.9] ⚠️ | −1.0 [−5.7, +3.3] ⚠️ | −4.8 [−9.3, +0.1] ⚠️ |

- **No cell is miscalibrated after Holm.**
- The WTA treble cell is the one unadjusted rejection. Excluding linked matches whose T−30 P disagrees with the Pinnacle close by
  more than 10 pp moves it to **+0.05 [−2.7, +2.8]**, which points to early-start contamination.
- In development, ATP doubles were −1.9 [−3.5, −0.3] (unadjusted). Tennis multis lean slightly *over*-predicted (−0.5 to −2 pp),
  inside precision.
- Recalibration slopes cluster around 0.9–1.2 where n ≥ 200.
- Brier skill: singles 0.05–0.08, doubles 0.04–0.07, trebles 0.01–0.07.

**Probability bands** (full tables in `calibration_summary.csv`):
- Singles are calibrated in every band and leg threshold in tennis and NBA, to within about 2 pp. For example, ATP holdout legs
  ≥ 0.90: n = 333, 94.0% predicted → 93.4% realised.
- **Football favourites are under-confident at high P**: legs ≥ 0.70 run +3.0 pp in development.
- Random U1 multis rarely reach high P. For the high-P region, the top-P strategy S1 (P_joint ≈ 0.60–0.72) gives:
  - doubles: ATP +3.7 / −0.6, WTA −1.1 / +1.7, NBA +1.0 / +3.5, football +10.5 / +5.8 (development / holdout);
  - trebles: ATP +4.0 / +0.1, WTA −2.3 / +1.9, NBA −0.1 / **+6.9**.
  - CI half-widths are 3.5–6 pp. **The engines are not over-confident at the top**, but precision is weak.
- **Trebles ≥ 0.65 and doubles ≥ 0.80 remain effectively untested:**
  - U1 counts: trebles 4–25, doubles 10–55 per cell.
  - This matches the earlier finding and is **not** resolved by the data we own.

## 4. Independence of distinct events: P2
**Mean pairwise residual product, holdout** (= the product rule's error for a double):
- ATP −0.0016 [−0.0035, +0.0004]
- WTA −0.0021 [−0.0044, +0.0004]
- NBA +0.0001 [−0.0037, +0.0039]
- Football +0.0009 [−0.0067, +0.0093]

**Development:** +0.0005, −0.0014, +0.0020, 0.0000.

- **No sport rejects independence after Holm, and the signs are inconsistent across periods.**
- The error of P_joint = p_i·p_j is bounded at about ±0.4 pp (tennis, NBA) and ±0.9 pp (football).
- Same-tournament and cross-tournament pairs do not differ.
- Daily-loss dispersion index is 0.90–1.07, and every CI contains 1.
- **Cross-sport doubles** (exploratory): 5 of 6 pairs are calibrated. ATP + football is +2.6 [+0.1, +4.9], an unadjusted exploratory
  cell consistent with football under-confidence.

## 5. Overlap and effective sample size (K)
- Exhaustive within-day universes are huge: ATP holdout gives 29,892 doubles and 143,335 trebles from **5,018 events**. Each event
  appears in about 12 doubles and about 89 trebles.
- Model-implied Kish n_eff / raw, on 60 sampled days: **doubles 0.12–0.23, trebles 0.035–0.09.**
- Raw combination counts overstate evidence by 4–30×. Every confirmatory result above uses disjoint cards (U1) and day clustering.

## 6. Margin compounding (J)
Mean net EV of **all** favourite same-book cards:

| | leg | double | treble |
|---|---|---|---|
| Football pre-close, B365 / WH / BW | −5.8 / −5.5 / −4.8% | −11.2 / −10.7 / −9.4% | −16.3 / −15.6 / −13.8% |
| Tennis B365 close vs Pinnacle-fair (ATP / WTA) | −4.6 / −4.6% | −9.1 / −9.0% | −13.3 / −13.1% |

The bookmaker margin compounds almost multiplicatively, (1 + EV)^k.

## 7. Probability-error stress (E)
**Deterministic.** For a card priced at model EV +2%, the uniform per-leg overestimate that erases all EV is:

| leg P | single | double | treble |
|---|---|---|---|
| 0.6 | 1.18 pp | 0.59 pp | 0.40 pp |
| 0.9 | 1.77 pp | 0.89 pp | 0.59 pp |

The tolerance shrinks roughly as 1/k. At a +5% model EV, P = 0.8 doubles tolerate 1.9 pp and P = 0.7 trebles 1.1 pp.

**Empirical** (CLOSE-DIAG tennis POS_EV cards, ATP / WTA):
- Median tolerance: singles 0.72 / 0.66 pp, doubles 0.84 / 0.75 pp, trebles 1.19 / 0.64 pp.
- Share still EV > 0 after a **1 pp** uniform error: singles 38 / 35%, doubles 44 / 33%, trebles 73 / 13%.
- After **2 pp**: 10 / 13%, 8 / 12%, 7 / 0%.
- The card's 1%-stake growth advantage over its singles vanishes at a median error of 0.3–0.7 pp.

**Observed precision** (§3): singles 1.2–2 pp; high-P multis 3.5–6 pp. **The apparent edge of a typical +EV multi is smaller than
our own calibration uncertainty.**

## 8. Chronological daily engine, equal capital, bankroll (F, G, H)
Verdict counts for card vs singles (mean daily log-return difference with a day-bootstrap CI; 5 stakes × period × k × strategy):

| price scenario | CARD better | SINGLES better | no difference | < 30 days |
|---|---|---|---|---|
| SYNTH fair (m = 0) | 13 | 6 | most | 10 |
| **SYNTH 5% margin** | **0** | **100** | rest | 10 |
| CLOSE-DIAG real closes, HIGH_P | 0 | 15 | rest | — |
| POS_EV, any priced scenario | 0 | 0 | all | most |

- **Fair prices.** The 13 CARD cells come from 3 sport × k × period combinations: ATP doubles in development, NBA trebles in
  holdout, and football doubles in development. **None replicates in the other period.** The 6 SINGLES cells are at 3–5% stakes.
  With zero margin, structure mostly trades variance for nothing.
- **Realistic margin.** Singles dominate at every stake. Card bankrolls fall well below singles.
  - Example, WTA S1 doubles, development, 1%: final bankroll 0.59 vs 0.79.
  - At a 2% stake, P(bankroll < 50%) for a card vs singles: ATP doubles holdout 0.84 vs 0.02; NBA trebles development 0.99 vs 0.22.
- **Risk profile at a 2% stake (HIGH_P S1).**
  - Whole-stake loss: 24–33% of days for doubles and 36–47% for trebles (tennis, NBA), versus 2–4% and < 1% for the singles.
  - Maximum drawdown is typically 1.5–3× that of the singles.
  - Model P(losing run ≥ 8 over the period) for trebles is 0.12–0.53 (tennis, NBA), versus about 0 for the singles' whole-stake losses.
- **At 5% stakes**, card impairment becomes likely even at fair prices: ATP doubles holdout P(bankroll < 50%) is 0.53 for the card
  vs 0.08 for singles.

## 9. Odds and profitability (I): only ASOF-FB is legitimate
- **HIGH_P S1 at real pre-closing UK prices**, per unit (with 95% CI):
  - singles: +1.3% [−4.4, +6.2] (306 days) / +0.5% [−7.2, +8.5] (125 days);
  - doubles: +6.0% [−6.4, +18.3] (114) / +4.8% [−16.9, +27.5] (44);
  - trebles: −23.6% [−51.5, +1.3] (42) / −42% (10).
  - **No CI excludes 0 in either period, so there is no profitability evidence.**
  - The positive doubles point estimates come from football favourite under-confidence: +9.6 pp in development (significant),
    +8.2 pp in holdout (not significant). This is a **hypothesis only**.
- **POS_EV at ASOF-FB:** only **2 days in 6 seasons** had any UK-book EV > 0 favourite, and **zero** all-legs-+EV multis. The
  paper-eligibility rule (every leg +EV) essentially never triggers historically at football pre-close UK prices.
- **CLOSE-DIAG tennis** (Pinnacle-close P vs B365 close; *diagnostic, not a decision*):
  - POS_EV singles on about 22–24% of days: +5.6% / +8.7% (ATP), +1.0% / −0.5% (WTA).
  - POS_EV doubles on about 5% of days (ATP 51/17, WTA 43/22 days, development / holdout).
  - Every CI includes 0.
  - HIGH_P at the real B365 close loses (−1 to −8%), with doubles worse than singles.

## 10. Sport by sport (L)
- **Tennis:** singles, doubles and < 0.50 trebles are precisely calibrated. Independence is supported to ±0.4 pp. There are no
  decision-time prices.
- **NBA:** calibrated. Multis are imprecise in holdout (2.6 seasons). There are no per-book prices.
- **Football:** under-confident at high P, imprecise (small n). It has the only decision-time prices; value there is almost nonexistent.
- Nothing is assumed to transfer between sports. Cross-sport cards are exploratory only.

## 11. Null and negative findings (recorded)
- S2 is empty (A3).
- No POS_EV football multis exist at pre-close.
- No strategy shows a CI-excluding-0 profit in both periods.
- Fair-price CARD wins did not replicate.
- No P1 or P2 rejection after Holm.

## 12. Limitations
- All holdouts were previously exposed.
- Tennis P comes from per-match T−30 snapshots, so a "morning card" uses slightly later information for later legs (market
  information, not outcomes).
- Football snapshots are untimestamped, and single-book outlier quotes are possible.
- There are no accumulator prices, rules or limits anywhere.
- CLOSE-DIAG uses a reference estimator, not the frozen engine.
- SYNTH shows structure, not markets.
- Favourite legs only.
- Strategies, stakes and scenarios are many; only P1–P3 are confirmatory.

## 13. What the historical evidence establishes
1. The product rule for distinct events is sound. Its error is ≤ about 0.4 pp for tennis and NBA doubles, and independence is not
   rejected anywhere.
2. Tennis singles, doubles and low-P trebles are calibrated to 1–2.5 pp.
3. Bookmaker margin compounds (1 + EV)^k: about −10% for doubles and −15% for trebles at UK retail.
4. At realistic margins, singles on the same legs dominate multis in growth, drawdown and impairment at every tested stake. At fair
   prices there is no consistent winner.
5. A multi's apparent edge is erased by a per-leg probability error of about 0.4–1 pp. That is smaller than our demonstrated
   calibration precision.

## 14. What it does not establish
- Any real profitability for any structure.
- Executable accumulator pricing.
- Calibration of trebles ≥ 0.65 or doubles ≥ 0.80.
- Decision-time value in tennis or NBA.
- Whether the football high-P under-confidence is exploitable after margin (ROI CIs include 0).

## 15. Decision classification (N)
| | probability evidence | profitability evidence |
|---|---|---|
| **Joint probability model** (distinct events) | **VALIDATED** for independence (all 4 sports) and for tennis doubles and < 0.50 trebles; **PROMISING** for NBA and football multis (imprecise); **INCONCLUSIVE** for trebles ≥ 0.65 and doubles ≥ 0.80 | — |
| **Singles** | **VALIDATED** (tennis, NBA); football **PROMISING**, slightly under-confident at high P | **NONE**: ASOF-FB CIs include 0; no valid tennis or NBA prices; CLOSE-DIAG inconclusive |
| **Doubles** | **VALIDATED** (ATP); **PROMISING** (WTA: 2.03 pp vs the 2.0 limit; NBA; football) | **NONE / NEGATIVE** at realistic margins; zero POS_EV historical sample at ASOF-FB |
| **Trebles** | **PROMISING** below 0.50; **INCONCLUSIVE** at or above 0.50 and untested at or above 0.65 | **NEGATIVE**: −13 to −16% compounded margin; highest whole-stake loss and impairment |

**Answers.**
- **Best calibrated:** tennis singles and doubles.
- **Bands with enough evidence:** singles in all bands (tennis, NBA); doubles below 0.65; trebles below 0.50.
- **Surviving realistic probability-error stress:** only cards with a model EV cushion of at least 1–2 pp per leg. Typical +EV
  multis do not survive.
- **When each structure dominates, at equal capital:**
  - With every leg genuinely +EV and a small stake (below about 2–5%, depending on P and odds), the card grows faster.
  - Once the legs are not all genuinely +EV, P is off by about 1 pp, or the stake is larger, singles dominate. Historically, that is
    almost always.
- **Legitimate profitability findings:** none.
- **Indicative only:** every multi price, CLOSE-DIAG, and SYNTH.

## 16. Remaining data gap (exact)
1. Decision-time (T−X) same-book prices for tennis and NBA, which would allow POS_EV frequency and value at decision time.
2. Real accumulator prices and terms. **No dataset we own or could buy via The Odds API contains them.**
3. More high-P multi outcomes (trebles ≥ 0.65 need n_eff ≥ 300). These accrue slowly by nature, and the prospective V2-7 logger
   already collects them at 0 cost.

## 17. Historical Odds API recommendation (O): do not buy for card research
- For card research specifically, the purchase adds little:
  - It returns only per-selection prices, so multis would remain indicative.
  - The card question that decision-time prices could answer (how often all legs are +EV at one book) is already being measured
    prospectively by V2-7, twice a day, at 0 cost.
- Where it still has value is the **singles** decision-time question (V2-6D). If Fraser wants to accelerate that, the already-specified
  pilot remains correct, and a card hypothesis can ride along at no extra credit cost:
  - **Scope:** Wimbledon and US Open 2024, ATP and WTA, one snapshot per active key-day at about T−3 h.
  - **Request:** h2h, region uk (bookmakers plus `betfair_ex_uk`), about 56 key-days × 10 = 560 credits, plus about 60 event calls,
    **≈ 620 credits** in total.
  - **H1:** the rate of favourites with same-book net EV ≥ 2% against the exchange-mid P at that snapshot.
  - **H2:** the rate of days with at least one same-book all-legs-EV > 0 double.
  - **Success:** H1 of at least 1 per 100 favourite matches, with calibration of the selected legs inside ±3 pp.
  - **Failure:** H1 below 0.5 per 100. That would stop further purchase and lead to a negative result being recorded.
- **Not purchased.**

## 18. Next recommended action
1. Leave V2-7 prospective logging running untouched.
2. Keep **singles as the default**. Nothing historical justifies promoting multis, and the prospective POS_EV multi stream is the
   right place for any future evidence.
3. Record the football high-P under-confidence as a **pre-registered hypothesis for a future out-of-sample test** (2026/27 season),
   **not** as a rule change.
4. The Odds API pilot is Fraser's call, justified by the singles question, not by the multi question.
5. When convenient and without placing a bet, Fraser could check one bookmaker's accumulator bet-slip price against the product of
   its leg prices. That is the only way to test execution-verified multi pricing. It is outside this task.
