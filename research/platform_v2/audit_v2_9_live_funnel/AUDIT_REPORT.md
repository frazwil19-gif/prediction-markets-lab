# V2-9 — Full System Audit: why the first live V2-7 scans produced zero bet candidates

Status: READ-ONLY diagnostic. No outcomes used. No threshold, engine, V2-7, V2-8, settlement or production change.
Branch: `v2-9-live-funnel-audit` (from master `18f0747`). Not merged.
Reproduce: `python scripts/v2_9_live_funnel_audit.py` → `AUDIT_RESULTS.json` (reads production files via `git show` at the exact scan commits).

| scan | production commit | V2-7 shadow commit | scan time (UTC) | run | intended | delay |
|---|---|---|---|---|---|---|
| morning | `e9cc1a4` | `5c4db9d` | 2026-09-30 12:54 | 36717723414 | 06:30 | 6.4 h |
| afternoon | `7e3ce99` | `18f0747` | 2026-09-30 20:16 | 36771315893 | 15:30 | 4.75 h |

---

## 1. Executive diagnosis

Zero candidates is a **correct outcome of the current rules on this market slate**, not a pipeline failure. Three things explain it:

1. **Prices sit at or just below our probability.** Our P is derived from the Betfair exchange mid, so by design it tracks the market. The median model-minus-bookmaker-consensus gap is +1.1pp (morning) and +1.3pp (afternoon). Only one match disagrees by more than 10pp. Bookmakers carry a ~5.8% median overround. The result is that the best available price is almost always slightly worse than fair.
2. **Every clean positive-EV opportunity was tiny.** The maximum was +1.64% (Medvedev at betvictor 1.29). That is smaller than the 2% bsv2-3 floor and smaller than 1σ of probability uncertainty (1.2–1.5pp). Zero of 5 and zero of 9 positive-EV quotes survive EV at P−1σ.
3. **The spread gate removes 25–30% of matches, but this cost no valid opportunity.** 14 and 16 matches were removed. All of them are WTA China matches 24–48h before start, where the exchange book had not yet formed. No removed match was positive across its whole back/lay range.

**One real defect was found, and it did not cause zero bets.** 10 (morning) and 9 (afternoon) rescheduled matches are silently dropped from the production bsv2-3 universe and the unified board, because the ledger keeps a stale `event_start`. They include Alcaraz, Tiafoe, Tsitsipas, Shapovalov, Rune and others. The same matches were fully evaluated in V2-7, and every one had negative EV at the best price. So the defect hid rows but did not hide a bet.

**One philosophy conflict was confirmed.** The V2-7 HIGH_P cohort, and therefore the V2-8 Stage A board, only includes matches that have a clean (≤3pp) quote. As a result, 8 of 24 (morning) and 9 of 26 (afternoon) P≥0.70 predictions are missing from the probability-first board. DECISION_PHILOSOPHY.md says the board ranks probability *before* price/quality considerations.

## 2. Complete funnel (V2-7 single legs, unique matches)

| stage | morning | afternoon |
|---|---|---|
| Odds API events returned | 56 | 55 |
| engine predictions | 53 | 55 |
| source-validated (EXCHANGE_MID/BACK) | 53 | 55 |
| priced (≥1 book quote) | 53 (808 quotes) | 55 (850 quotes) |
| exchange width ≤ 0.03 | 39 (634) | 39 (644) |
| fresh, not started | 39 | 39 |
| positive central EV (any book) | 3 matches (5 quotes) | 4 matches (9 quotes) |
| EV at P−1σ > 0 (SHADOW_CANDIDATE) | 0 | 0 |
| bsv2-3 net EV ≥ 2% | 0 | 0 |
| **final candidates** | **0** | **0** |

**Production bsv2-3 funnel (separate universe = unified ledger upcoming):**

| | morning | afternoon |
|---|---|---|
| candidate rows | 46 | 49 |
| unique events | 43 | 46 |
| REJECT | 34 | 39 |
| WATCH | 2 | 4 |
| MULTI_RESEARCH_ELIGIBLE | 10 | 6 |

- Reason codes, morning: NET_EV_NOT_POSITIVE 42, PREDICTION_NOT_VALID 7, NET_EV_BELOW_PAPER_GATE 3, ODDS_BELOW_PAYOUT_FLOOR 2.
- Reason codes, afternoon: NET_EV_NOT_POSITIVE 43, EXCHANGE_SPREAD_TOO_WIDE 14, PREDICTION_NOT_VALID 7, NET_EV_BELOW_PAPER_GATE 4, P_BELOW_FLOOR 1.

The 53/55 board matches versus the 43/46 production events differ because of the rescheduling defect (§12). Production also includes 3 duplicated event rows (research-only plus validated).

## 3. Unique matches vs card count

| | morning | afternoon |
|---|---|---|
| raw V2-7 cards | 205 | 235 |
| distinct leg sets | 202 | 229 |
| HIGH_P matches | 16 | 17 |
| POS_EV matches (book-quotes) | 3 (5) | 4 (9) |

Card counts are combinatorial: 16 legs give 16 singles, C(16,2)=120 doubles and a 10% hash-sample of 560 trebles (59). So 205 cards represent only **16 + 3 underlying matches**, and ~200 cards give no independent evidence. Afternoon: 17 singles, 136 doubles, 71 trebles, plus 9/2/0 POS_EV. Report matches, not cards, as the unit of opportunity.

## 4. Probability-engine audit

- **Recomputations passed on raw data:** no back/lay inversions; mid and width recomputed exactly; de-vig sums to 1; all 21 POS_EV cards recompute (p_joint, odds, EV) with zero mismatches.
- **Midpoint definition.** The engine averages *decimal odds*, (back+lay)/2, then inverts. Averaging implied probabilities differs by a median of 0.006pp. On clean books (≤3pp) the maximum difference is 0.047pp (morning) and 0.031pp (afternoon). On wide books it reaches 7.35pp and 5.12pp. This is irrelevant where the gate passes and large where it fails. It is a frozen design choice, not a bug.
- **Market agreement:** median model − book consensus is +1.12pp / +1.31pp. The model is systematically slightly *more* confident in favourites than the bookmaker consensus. This is expected, because bookmaker prices embed favourite-longshot margin. Only 1 match has |Δ| > 10pp, a wide-book case.
- **Structural point, not a defect:** P is an exchange-derived probability. The engine is well calibrated on holdout, but by construction it can only find value where a bookmaker is *off the exchange*. It cannot find value where the whole market is wrong. Edges are therefore rare and small, and the probability layer and value layer are nearly collinear.

## 5. Spread-gate audit (EXCHANGE_BOOK_TOO_WIDE / EXCHANGE_SPREAD_TOO_WIDE)

**Provenance.** bsv2-3 was introduced on 2026-09-29 after the wide-spread incident. The rationale was that midpoint error of up to half the width (1.5pp) is comparable to the 2% EV floor. It was fixed before any outcome was seen. It is **not empirically calibrated**: no settled observation has recorded width. Classification: REASONABLE BUT PROVISIONAL (heuristic).

**What it removes:**

| | morning | afternoon |
|---|---|---|
| unique matches removed | 14 | 16 |
| quotes removed | 174 | 206 |
| of which P ≥ 0.70 | 8 | 9 |
| INDETERMINATE (EV sign flips within [back,lay]) | 11 | 8 |
| POOR even at top of exchange range | 3 | 8 |
| positive across the whole range | **0** | **0** |

**New finding: width is a time-to-start effect.** Every removed book is WTA China, 24–48h before start, where the Betfair book had not yet formed.

| window | morning: n / wide / median width | afternoon: n / wide / median width |
|---|---|---|
| 0–12h | 1 / 0 / 0.96pp | 33 / 0 / 0.79pp |
| 12–24h | 37 / 0 / 1.00pp | 4 / 0 / 0.48pp |
| 24–48h | 15 / 14 / 10.5pp | 18 / 16 / 7.6pp |

No match within 24h of start had a width above 3pp. The spread gate is therefore effectively coincident with a "too early" filter. These matches would be re-evaluated on a later scan once liquidity forms, and ATP China and ATP Japan had no wide books.

**Threshold sensitivity (morning; matches passing / with positive central EV):**

| threshold | 1pp | 2pp | 3pp | 4pp | 5pp | none |
|---|---|---|---|---|---|---|
| passing / +EV | 20 / 1 | 38 / 3 | 39 / 3 | 39 / 3 | 39 / 3 | 53 / 9 (NOT VALID) |

The distribution is bimodal: 0–1pp 20, 1–2pp 18, 2–3pp 1, then nothing until 5–6pp 3, 7–8pp 1, 9–10pp 1 and ≥10pp 9. Any threshold between 2pp and 5pp gives an identical result. The "none" column is shown only for completeness. Per the directive, the 6 extra positive-EV matches there use an unreliable midpoint P and are **not** treated as real value (e.g. Samsonova +15.8% at width 21.8pp).

**Does calibration change with width?** **Evidence insufficient.** The engine's calibration holdout pre-dates width logging, and no prospective settled rows with width exist yet. This must be learned from prospective V2-7 logging (legs.csv records width) and not assumed.

## 6. Uncertainty audit

- **σ trace:** σ_leg = √(cal_se² + (width/2)²).
- **cal_se** is the band holdout Wilson half-width / 1.96: 0.0109 (50–65%), 0.0116 (65–80%), 0.0122 (80%+).
- On clean books the width term contributes 0.3–1.5pp, so σ is ≈ 1.2–1.5pp. The joint σ uses the delta method assuming independent leg errors.

**Every positive-central-EV opportunity:**

| scan | selection | book(s) | odds | P | σ (cal / ½w) | break-even P | margin (pp) | central EV | EV at P−1σ |
|---|---|---|---|---|---|---|---|---|---|
| AM | Medvedev | betvictor | 1.29 | 0.7879 | 0.0149 (0.0116 / 0.0094) | 0.7752 | 1.27 | +1.64% | −0.28% |
| AM | Zakharova | betano_uk, betvictor | 1.08 | 0.9310 | 0.0131 (0.0122 / 0.0048) | 0.9259 | 0.51 | +0.55% | −0.87% |
| AM | Siniakova | betano_uk, betvictor | 1.53 | 0.6538 | 0.0130 (0.0116 / 0.0060) | 0.6536 | 0.03 | +0.04% | −1.95% |
| PM | Volynets | paddypower, skybet | 1.83 | 0.5477 | 0.0111 (0.0109 / 0.0020) | 0.5464 | 0.13 | +0.23% | −1.80% |
| PM | Siniakova | betano_uk, betvictor | 1.53 | 0.6546 | 0.0123 (0.0116 / 0.0043) | 0.6536 | 0.10 | +0.16% | −1.73% |
| PM | Eva Lys | betano_uk, betvictor, boylesports, unibet_uk | 1.44 | 0.6953 | 0.0118 (0.0116 / 0.0024) | 0.6944 | 0.09 | +0.13% | −1.57% |
| PM | Halys | betfair_sb_uk | 1.80 | 0.5556 | 0.0113 (0.0109 / 0.0031) | 0.5556 | 0.00 | 0.00% | −2.04% |

That is 5 AM quotes and 9 PM quotes in total. Apart from Medvedev, every one clears break-even by ≤0.51pp. These are prices at fair, not edges.

The best opportunity clears break-even by 1.27pp of probability, which is less than its own 1.49pp σ. No opportunity is close to "statistically strong". The EV_low rule is doing its job. It is not the binding constraint, because even central EV never reached 2%.

## 7. Hard-gate registry

| layer | gate | value | classification | binding on 30 Sep? |
|---|---|---|---|---|
| engine | exchange freshness | 6h | OPERATIONAL SAFETY | no |
| engine | VALID_SOURCES | EXCHANGE_MID, EXCHANGE_BACK (validated); BOOKMAKER_CONSENSUS research-only | EMPIRICALLY SUPPORTED (holdout-validated sources only) | 7 NOT_VALID rows each scan |
| ingest | Odds API key coverage / max 6 keys / credit guard | 3 active, 0 over cap, credits 394→385 | OPERATIONAL SAFETY | no |
| ingest | ledger `event_start` used as the "upcoming" filter | first-seen start time | **DEFECT** (§12) | hid 10 / 9 matches |
| bsv2-3 | PREDICTION_NOT_VALID | — | EMPIRICALLY SUPPORTED | 7 / 7 |
| bsv2-3 | EVENT_STARTED, PRICE_AT_OR_AFTER_START | — | OPERATIONAL SAFETY | no |
| bsv2-3 | NO_EXECUTABLE_PRICE, COMMISSION_UNKNOWN (matchbook null) | — | OPERATIONAL SAFETY | no |
| bsv2-3 | PROBABILITY_NOT_SAME_SNAPSHOT | — | OPERATIONAL SAFETY (leakage) | no |
| bsv2-3 | EXCHANGE_SPREAD_TOO_WIDE / UNKNOWN | 0.03 | REASONABLE BUT PROVISIONAL (heuristic, pre-outcome) | 14 PM; none within 24h |
| bsv2-3 | PRICE_STALE | 240 min | OPERATIONAL SAFETY | no (max age 11 min) |
| bsv2-3 | NET_EV_NOT_POSITIVE (HARD) | 0 | REASONABLE BUT PROVISIONAL (sound decision logic; never bet −EV) | **42 / 43, primary** |
| bsv2-3 | P_BELOW_FLOOR | 0.50 | REASONABLE BUT PROVISIONAL | 0 / 1 |
| bsv2-3 | NET_EV paper gate | 2% | ARBITRARY/HEURISTIC (chosen vs midpoint error, not vs outcome data) | 3 / 4 |
| bsv2-3 | ODDS_BELOW_PAYOUT_FLOOR | 1.33 | ARBITRARY/HEURISTIC | 2 / 0 |
| bsv2-3 | horizon | ≤24h | OPERATIONAL SAFETY | — |
| bsv2-3 | commission | betfair 5%, smarkets 2% | EMPIRICALLY SUPPORTED (published rates) | — |
| V2-7 | leg quality codes (TOO_WIDE, STALE, STARTED, INVALID_ODDS) | mirrors bsv2-3 | as above | — |
| V2-7 | HIGH_P requires ≥1 clean quote | — | **CONFLICTS with DECISION_PHILOSOPHY** (§8) | removes 8 / 9 P≥0.70 |
| V2-7 | HIGH_P P ≥ 0.70, max 24 events, treble 10% sample | — | ARBITRARY/HEURISTIC (logging budget) | no |
| V2-7 | SHADOW_CANDIDATE EV at P−1σ > 0 | 1σ | ARBITRARY/HEURISTIC (σ model itself provisional, no covariance) | 5 / 9 quotes |
| V2-7 | lateness | 90 min | OPERATIONAL SAFETY | no |
| V2-8 | structure screen, min stakes | config | REASONABLE BUT PROVISIONAL (offline) | n/a |
| engine | model probabilities, calibration bands | frozen | DO NOT CHANGE — FROZEN | — |

## 8. Value-first legacy audit

- **Production tennis Prediction Board:** shows all P≥0.70 predictions (24 / 26). ✔
- **Unified board (`prediction_platform/board.py`):** filters `event_start > now`, so the rescheduled-match defect also removes those rows here (see §12). ✘
- **V2-7 HIGH_P cohort:** requires ≥1 clean book quote and width ≤0.03, which gives 24→16 and 26→17. ✘ The V2-8 Stage A board reads V2-7 HIGH_P legs, so it inherits this. DECISION_PHILOSOPHY.md separates *prediction quality* from *bet quality* and ranks by probability first. A high-P prediction with a wide book is still a prediction; only its *betability* is in doubt. The fix is to show those predictions with a quality label instead of dropping them (a RESEARCH NEXT design change on V2-7/V2-8, not done now).
- **bsv2-3 labels:** NET_EV_NOT_POSITIVE is HARD, so a P=0.93 favourite is shown as REJECT (or MULTI_RESEARCH_ELIGIBLE). This is correct for staking, but it is value-first language on a probability-first board. Consider a separate "HIGH_P / NO VALUE" display label (presentation only).

## 9. Exact explanation of zero candidates — final attrition

| cause | morning (matches) | afternoon (matches) |
|---|---|---|
| start | 53 | 55 |
| − spread gate (all 24–48h WTA China; 0 positive across range) | −14 | −16 |
| − no book priced above fair (central EV ≤ 0) | −36 | −35 |
| = positive central EV | 3 | 4 |
| − EV at P−1σ ≤ 0 (all; max central EV 1.64%) | −3 | −4 |
| − (bsv2-3 alternative) EV < 2% | (−3) | (−4) |
| **= candidates** | **0** | **0** |

The quantified primary cause is **price, not gating**. 36/39 and 35/39 clean matches have no book above fair value, because bookmaker margin (~5.8%) exceeds the typical model-vs-book disagreement (~1.2pp). The only other contributor is uncertainty, and it only affects 3–4 matches with EV of +0.0–1.6%.

## 10. HIGH_P / no-bet analysis (top 15 each scan)

The pattern is overwhelmingly **HIGH_P + POOR PAYOUT**. Favourites at P 0.79–0.97 are priced 1.02–1.29, with best EV of −4% to +0.5%. Examples:
- Zverev 0.887 @1.10 (−2.5%)
- Alcaraz 0.827 @1.18 (−2.4%)
- Storm Hunter 0.926 @1.06 (−1.9%)

Some rows were excluded only because of data quality (wide book, P unreliable): Samsonova, Muchova, Andreeva, Noskova, Osaka and Sabalenka. The apparent +EVs for some of these (Samsonova +15.8%, Noskova +4.0%, Muchova +3.6%) come from an unreliable midpoint P.

Only Zakharova (AM) and Medvedev (AM) had positive EV at the best clean price, and both failed on uncertainty. Identical P/σ/width values across two different matches (e.g. 0.9198) come from identical Betfair ladder prices (1.08/1.09), not a join error. The raw rows were checked.

## 11. One-gate-at-a-time counterfactuals (no outcomes; matches with ≥1 candidate)

| relaxation (others unchanged) | morning | afternoon |
|---|---|---|
| baseline (EV_low at 1σ > 0) | 0 | 0 |
| central EV > 0 only | 3 | 4 |
| EV at P−0.5σ > 0 | 1 | 0 |
| EV at P−1.645σ > 0 | 0 | 0 |
| σ = calibration SE only (drop width term) | 1 | 0 |
| bsv2-3 EV ≥ 2% | 0 | 0 |
| no spread gate (NOT VALID — midpoint P unreliable) | 9 central / 1 EV_low | 9 / 0 |

No single reasonable relaxation produces more than one weak candidate, at EV +1.6%. Loosening would not reveal hidden strong bets. It would only admit near-zero-edge bets. Per the directive, no looser threshold is recommended on these grounds.

## 12. Bug audit

| check | result |
|---|---|
| back/lay inversion, odds ≤1, NaN | none |
| mid/width/de-vig recompute | exact |
| V2-7 card p_joint / odds / EV recompute (21 POS_EV cards) | 0 mismatches |
| POS_EV duplication / self-pairing | none; 3 duplicate leg-sets from treble sampling (205→202, 235→229) — cosmetic |
| production write only to prospective/ | yes (verified in first-live check) |
| **rescheduled matches dropped (stale `event_start`)** | **VERIFIED DEFECT** |
| duplicate research-only + validated rows for same event (3 per scan, e.g. Siniakova, Parks/Zhu, Tararudee/Osorio) | cosmetic; the valid twin is evaluated |
| 4 NOT_VALID events with no valid twin (Starodubtseva, Ito/Birrell, Kenin/Krueger, Badosa/Kasatkina) | expected: BOOKMAKER_CONSENSUS-only, no exchange price |
| midpoint in odds space | frozen design choice; negligible on clean books (≤0.05pp) |
| σ ignores correlated calibration error (joint σ assumes independence) | methodological limitation → RESEARCH |
| settlement disabled | confirmed |

**Rescheduled-start defect (details).**
- The tennis prediction row, and therefore `predictions/unified_ledger.csv` via `append_unique` on `prediction_id`, keeps the `commence_time` from the first scan. The Odds API had placeholder start times (e.g. 2026-09-30T02:00). These later moved to 2026-10-01 02:00–08:00.
- `scripts/run_bet_selection_v2.py:78` (`upcoming = … event_start > now`) and `prediction_platform/board.py:32` both use the stale value. So the matches are treated as already started and are silently excluded. No reason code is logged.
- Morning: 10 of 53 board matches; afternoon: 9 of 55. Affected: Nakashima/Humbert, Darderi/Ruud, Nishikori/Tiafoe, Rune/Jacquet, Etcheverry/Tsitsipas, Shapovalov/Shimabukuro, Davidovich Fokina/Berrettini, Alcaraz/Michelsen, Gao, …
- **Impact on 30 Sep:** none on the decision. All affected matches were evaluated in V2-7 and had EV < 0 at the best price.
- **Latent risks:**
  - silent loss of real opportunities on any rescheduled day;
  - any consumer that times off `event_start` (settlement delay, lateness, "started" checks) will be wrong for these rows.
- Tennis settlement is disabled, and `settle.py` is football-only, so there is no current mis-settlement.
- The defect is reproduced deterministically by `v2_9_live_funnel_audit.py → defect_rescheduled_matches_dropped_from_production`. No test was added; the reproduction from committed data is the demonstration.

## 13. Data-coverage and scheduling audit

**Coverage:**
- 3 active keys (ATP China, ATP Japan, WTA China); 0 over cap; 0 skipped for credit; credits 394 → 385.
- 20 distinct books; per match min 10–11, median 16, max 17.
- Median bookmaker overround 5.8%.
- Quote age: median 0.5 min, max 3.1 / 11.1 min.
- Coverage is not a constraint.

**Self-source concentration:** 26 of 46 / 49 production "best prices" are betfair_ex_uk, the same exchange our P comes from. After 5% commission these can never be +EV against a Betfair-derived P. In practice, the executable value universe is the ~15 bookmakers.

**Scheduling delay (GitHub cron):**
- Runs started 6.4h and 4.75h late.
- 8 matches started inside the morning delay window (06:30–12:54) and so lost their intended pre-match scan. They were last seen ~20h earlier at the previous afternoon scan.
- 0 matches were lost in the afternoon window.
- The 24–48h width finding (§5) shows why this matters: books tighten close to start. A scan cadence that misses the final ≤12h before a match loses the only window where the book is clean and priced.
- This is an opportunity-coverage issue, not a correctness issue.

## 14. Decision matrix

| item | category | evidence |
|---|---|---|
| Use the latest scan `commence_time` (not the first-seen ledger `event_start`) for the bsv2-3 upcoming filter and unified board; log a reason code when a row is excluded | **FIX NOW** (after approval; append-only: do not rewrite ledger rows — add a latest-start lookup) | §12: 10 / 9 matches silently dropped |
| Show all P≥0.70 predictions in the V2-7 HIGH_P / V2-8 Stage A board, with a DATA_QUALITY label, instead of requiring a clean quote | **RESEARCH NEXT** (design change to V2-7/V2-8; pre-register) | §8: 8 / 9 predictions hidden; conflicts with DECISION_PHILOSOPHY |
| Scan cadence / delay: add a pre-match scan (e.g. hourly-to-start or later slots) to catch the ≤12h clean-book window | **RESEARCH NEXT** (cost/credit analysis) | §13: 8 matches lost; §5: books clean only <24h |
| Spread threshold 3pp | **KEEP** (provisional); **MONITOR** calibration vs width prospectively | §5: 2–5pp identical; no evidence on calibration vs width |
| σ model (independence, band-level cal_se) | **RESEARCH NEXT** | §6/§12: no covariance term; not event-specific |
| EV at P−1σ rule; 2% paper gate; 1.33 odds floor | **KEEP / MONITOR** — do not loosen | §11: no relaxation gives strong bets |
| Value sources beyond Betfair-derived P (independent model features) for markets where books diverge | **RESEARCH NEXT** (long-term) | §4: P≈market by construction |
| Exclude self-source (betfair_ex_uk) from "best price" display | **MONITOR** (cosmetic) | §13 |
| Duplicate research-only + validated rows | **MONITOR** (cosmetic) | §12 |
| "HIGH_P / NO VALUE" presentation label instead of REJECT on the board | **RESEARCH NEXT** (presentation only) | §8 |
| Tennis engine, calibration bands, midpoint definition, holdouts, historical ledgers | **DO NOT CHANGE — FROZEN** | §4 |
| V2-7 shadow logging (keep running; accumulates width + σ + price data needed for §5/§6) | **KEEP** | first-live PASS |

## 15. Recommended next actions (priority order)

1. **Approve and implement the rescheduled-start fix.** Use a latest-seen `commence_time` lookup, keep ledger rows append-only, add an explicit exclusion reason code, and add a regression test. This is the only verified defect.
2. **Keep V2-7 logging unchanged** for ≥2–4 weeks, so that prospective rows with width, σ, best price and (later) outcome accumulate. This is the only valid way to test the spread gate and the σ model.
3. **Pre-register a V2-7/V2-8 board change:** show every P≥0.70 prediction, labelled by data quality and betability, and keep staking eligibility unchanged.
4. **Scan-timing study:** quantify how width and the best price evolve 48h→0h, using existing snapshots across scans, and cost a later pre-match scan against Odds API credits.
5. **Research σ:** estimate calibration error correlation across legs and scans, and event-specific uncertainty, before any multi/structure staking.
6. **Longer-term research:** probability sources that are not exchange-derived, which are the only route to a materially larger edge than bookmaker margin.
7. Do **not** loosen the spread, EV or σ thresholds to generate bets. Treat zero-bet days as valid outputs.
