# Edge Source Discovery — Cycle 1 — REPORT

Date: 2026-10-02. Plan: `PREREGISTRATION.md` (commit `ef23543`, before any analysis).
Code: `scripts/edge_discovery_c1.py` (main) and `scripts/edge_discovery_c1_supplementary.py` (a disclosed
follow-up).
Outputs: `RESULTS.json`, `ATLAS.csv` (42 behaviours), `HYPOTHESIS_REGISTRY.md`, `SUPPLEMENTARY_OUTPUT.txt`.

**Everything here is DISCOVERY. Production was not touched and nothing was purchased.**

## 1. Executive conclusion
**There is no demonstrated profitable edge in the data we hold.** The data does show *where the money goes*. It also
contains one real, previously overlooked probability flaw and one mechanism worth measuring.
* **Accurate probabilities do not become profit at UK prices.** Return tracks Pinnacle-fair EV almost exactly:
  realised return regressed on EV has slope 1.07 in football and 1.24 in tennis, with intercept ≈ 0. So the price
  *is* the probability. The only ways to win are a better price than fair at decision time, or a better probability
  than the market. Neither shows up historically.
  * Soft UK books priced above Pinnacle-fair: +0.8% then −2.2% (football, n = 1,400); +0.7% then −1.7% (tennis).
    Not stable.
  * Public sporting features (Elo, form, rank) add ΔLL of about −0.0002 beyond the market. That is real in one cell
    but economically zero.
* **The football "high-P under-confidence" seen in three earlier studies is mostly an artefact of how the margin is
  removed.** Proportional de-vig shifts margin onto favourites. With power de-vig:
  * log loss improves in both periods (−0.0006 to −0.0008, CI < 0, 16 leagues);
  * the confirmation-period favourite bias falls from +4.5 pp to +1.6 pp.

  This is a **probability-quality fix (H1), not a betting edge.**
* **The one strong financial regularity is the favourite-longshot bias.** Longshots and draws are the worst bets:
  tennis underdogs below 35% return −15% to −18% at B365 (BH-significant). That supports the existing P ≥ 0.50
  design. It is not a source of profit.
* **The strongest predictor of return was closing-line value (CLV).** An opening price that beats the later sharp
  price returned +0.6% (n 5,090), versus −6.9% otherwise. CLV is only known *after* the decision, so it is a
  measurement tool (H2), not a rule.

## 2. Data inventory
| Dataset | Sport / league / market | Dates | N | Timestamps | Prices / books | Exchange back/lay | Outcomes | Features | P estimates | Leakage / bias notes | Financial replay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| football-data per-book (cycle_001 + 2025/26) | E0/E1/SC0 1X2 | 2020/21–2025/26 | 6,960 matches; 70k book-quotes | collection convention only (pre-close Fri/Tue; close at KO) | B365, WH, BW, PS; BF and 1XB (2024/25); 2025/26 adds BFD, BMGM, BV, CL, LB | no (BF = sportsbook?) | FTR | none | consensus, PS | outlier quotes; untimestamped | **B** pre-close, C close |
| xgabora Matches.csv | 40+ leagues; 16 used | 2000–2026 (used 2020–26) | ~50k matches (16 leagues) | none | B365 + cross-book Max | no | FTR | ClubElo (as-of), Form3/5, post-match stats | B365 de-vig | Max is an aggregate; post-match stats only usable as rolling aggregates | D (B365 vs own de-vig = −margin) |
| Betfair BASIC (interim) | ATP / WTA match winner | 2021–2025 | 12,202 / 10,352 | market start; LTP near T−30 | LTP only | no | yes | rank-P, Elo-P, surface, level, best-of | frozen engine | ~1% early-start contamination | D (P only) |
| tennis-data.co.uk | ATP / WTA | 2021–2025 | ~25k rows, 88–89% linked | none ("latest before play") | B365, PS, BFE (2025), Max/Avg | BFE back only | yes | rank, points, surface | PS de-vig (reference) | corrupt rows (screened) | C (aligned closes) |
| wippa / OddsPortal | NBA ML | 2016-17 → 2025-26 (two seasons absent) | 7,894 games | none | average close only | no | yes | scores | de-vig average | — | D |
| SBR archive | NBA ML/spread/total | 2011–2021 | 12,967 | none | single book closing | no | yes | scores | — | ends 2022 | D |
| Production `tennis_predictions/price_snapshots.csv` | tennis | 2026-09-23 → 10-01 | 5,951 quotes, 20 books, 112 events, 6 scans | **exact scan time + per-book `last_update`** | 17 UK books + Betfair / Matchbook / Smarkets | Betfair back/lay in `exchange_probability_snapshots` | 12 settled | — | engine | tiny outcome N | A-like for prices; no return claims yet |
| `paper_betting_v2/*` (selections, snapshots, decision_shadow, enrichment) | tennis (football / NBA pending) | from 2026-09-29 | 10 selections; 6.7k snapshots; decision shadow from 10-01 | exact | as above | yes | pending | σ, grades | engine | rule versions changed (bsv2-1 → 4) | **A** (prospective) |
| Unified ledger + settlements | tennis | from 2026-09-23 | 155 predictions; 12 settled | exact | — | — | 12 | — | engine | — | probability only so far |
| Daily cards (V1) | E0/E1/SC0 | 2026-09-19 → | ~190 candidates per day | exact | best book per outcome only | — | via V1 ledger | — | consensus | best-price only (dispersion lost) | A-like (best price only) |
| Earlier research (V2-6H, V2-6D, V2-7H, decision replay, multi/hybrid) | all | — | — | — | — | — | — | — | — | — | reused, not re-run |

## 3. Replayability map
* **A:** prospective production only (tennis now; football from about 8 Oct; NBA from 20 Oct).
  * Can support decision-time EV, dispersion and staleness.
  * Cannot yet support return claims (N is tiny).
* **B:** football pre-close per-book. Can support same-snapshot EV and return by book, side and P.
  * Cannot support exact horizon, staleness or executability at size.
* **C:** football close; tennis-data aligned closes. Can support closing efficiency and soft-vs-sharp at close.
  * Cannot support decision-time execution.
* **D:** tennis frozen-T−30 vs B365 close (proven leakage), NBA, xgabora Max. Probability and calibration only.

## 4. Raw-data behaviour (key distributions)
* **Margins:**
  * UK books 5.2–6.9% (football), 5.4–8.0% (tennis live);
  * Pinnacle 3.0–3.3%;
  * 1XB 3.7–4.3%;
  * live Matchbook 3.6% and Betfair 4.8% back-back, both before commission.
* **Dispersion (football):** the best UK price sits **2.5–2.7% above the median** and 5.1–5.6% above the worst. That is
  about half a margin, so line shopping recovers about half the vig and never all of it.
* **Pinnacle-fair movement opening → close:** mean |Δ| 1.7 pp.
  * Opening best-UK CLV versus closing Pinnacle-fair: median −3.7%, 10th percentile −13%, 90th percentile +4.6%.
* **Return vs EV:** the linear slope is 1.07 (football) and 1.24 (tennis). EV is realised on average.
  * Positive-EV quotes are mostly **longshots**: football EV > 0 average odds are 6.3. Their variance makes them
    statistically invisible.

## 5. Behaviour Atlas
`ATLAS.csv`, 42 rows. 30 rows carry a p-value; Benjamini–Hochberg is applied at q = 0.10. BH-significant and
sign-stable (status CANDIDATE):
* **FB-SIDE-D-P<0.35:** draws at the best UK price, −10.2% / −3.1%;
* **TN-SIDE-underdog P<0.35:** −17.7% / −14.7%.

Both are **negative** behaviours. No positive-return behaviour passes BH.

## 6. Price dispersion
* **Historical, football, 4–6 books:** dispersion is too small to beat the margin. The best UK price above
  Pinnacle-fair gave no stable return (+0.8% → −2.2%, CIs ±15%).
* **By book:** no book's EV > 0 quotes returned reliably. WH 0–1% EV quotes returned −34%, CI below 0. That looks
  like stale or outlier quotes.
* **Live, 20 books:** the panel is wider than any historical dataset. Best-quote EV versus the exchange de-vig has a
  median of −0.8% and a 90th percentile of +2.7%. 4–8% of quotes are EV > 0 at skybet, virginbet, grosvenor and
  paddypower (before any check). That is the **only** place dispersion can still be tested (H3, H7).

## 7. Bookmaker vs exchange
* **Pinnacle** is the cheapest and sharpest source historically. Betting *at* Pinnacle returned about −3% everywhere.
  As a probability source it was **not** better than the multi-book consensus (SUP-PS-VS-CONSENSUS).
* **Live exchanges** have the lowest margins. Matchbook shows the "best price" in 53% of quotes, but only before
  commission; its rate is unverified, so production already rejects it. That is correct; **no defect**.

## 8. Timing
* Historical data has two snapshots only. Prices move 1.7 pp on average from pre-close to close.
* A price that turns out to beat the close returns about 7 pp more than one that doesn't (FB-CLV-SIGN).
* Live: staleness (scan time − last_update) is a median of 0.6 min in every EV band. **Positive-EV live quotes are
  not stale** by this measure.
* Whether price movement is *predictable* at decision time is **DATA_REQUIRED**. It needs multi-snapshot timestamped
  prices.

## 9. Probability-region (calibration) findings
* **Favourite-longshot structure in football single-book de-vig:** 31 of 32 league-periods have a logit slope > 1.
  * Heavy favourites (P ≥ 0.70): +1.9 / +4.5 pp.
  * Longshots (< 0.20): −1.3 / −1.8 pp.
  * **This is largely the de-vig method (H1).**
  * The high-P effect sits in E0 / SC0 in per-book data (fav ≥ 0.7 +2.1 / +3.1 pp). With power de-vig it becomes
    −1.8 / +1.3 pp. It is not large enough to beat a 5% margin.
* **Tennis:** calibrated in every stratum: surface, level, best-of and tour (|bias| ≤ 2 pp where n > 500).
* **NBA:** calibrated, home and away (±1.5 pp).

## 10. Sport / league / market
| Market | Calibration | Return at UK books |
|---|---|---|
| Tennis | calibrated | −4% to −7% in the 20–80% band; least negative at 80%+ (−1.4% to −2.6%) |
| Football E0 / E1 / SC0 | calibrated | best-UK favourites −1% to −3%; SC0 least negative |
| NBA | calibrated | not replayable |

There is no market where return at UK prices is positive and stable.

## 11. Favourites, underdogs, draws
* Football all three sides at the best UK price:
  * home: −1% to −8%;
  * away underdogs < 0.35: −1.4% then −9%;
  * draws: −10% then −3%.
* Tennis underdogs < 0.35: −15% to −18%.
* **Excluding P < 0.50 is not hiding opportunities. It avoids the worst-priced region (favourite-longshot bias).**
* Showing all three 1X2 outcomes in Stage A is still worthwhile for probability monitoring. Production already
  ledgers all three.

## 12. EV continuum
* Realised return rises with EV (slope ≈ 1) **on average**.
* In the EV > 0 tail the relationship disappears. Every positive bucket's CI spans zero, and the 10%+ buckets are
  dominated by longshots and outliers.
* Nothing observable happens at 2%. **The 2% floor corresponds to nothing in the data**: it neither helps nor hurts.
  No change made.

## 13. Disagreement states
* **Model disagreement** (Elo or hybrid versus market): when they disagree, the market is right (multi/hybrid §19).
* **Pinnacle versus consensus:** outcomes follow Pinnacle by 1–3 pp, but there is no gain in log loss overall and
  the return at UK prices is ≈ 0.
* **Book versus consensus (dispersion):** a book above consensus does not win more. These are the stale or outlier
  quotes.

## 14. Sporting-feature residual information
Conditional on the market:
* ClubElo, Form5 and both together add **ΔLL −0.0001 to −0.0002** (football, 15.6k test matches; one cell CI
  just < 0);
* tennis rank-P and Elo-P add −0.0003 to −0.0005 (CI includes 0).

**Public features are already priced.** Any residual edge would need **non-public or faster** information, such as
lineups at announcement, injuries or in-play. That is DATA_REQUIRED.

## 15–17. Mechanisms and hypotheses
See `HYPOTHESIS_REGISTRY.md`:
* H1 is a CANDIDATE (probability quality);
* H2 is DATA_REQUIRED (CLV measurement);
* H3 was rejected historically and continues prospectively;
* H4 is rejected;
* H5 is validated as do-not-bet;
* H6 is rejected;
* H7 is a hypothesis;
* H8 is superseded by H1.

## 16. Important null results
1. Line shopping against a sharp fair price, historically.
2. Pinnacle as a better probability source.
3. Public sporting features beyond the market.
4. Underdogs and draws.
5. Any EV threshold effect.
6. Staleness of live positive-EV quotes.
7. Football high-P as an edge (now explained).
8. Multis and hybrids (previous cycle).

## 18. Validation designs for surviving hypotheses
* **H1:** shadow-compute power de-vig alongside the frozen football estimator on every prospective row (0 credits).
  * The confirmatory test, pre-registered, runs at the protocol interim (about 300 settled football favourites):
    ΔLL < 0 with CI, plus high-P calibration.
  * Holdout: 2026/27 and later.
  * Only then consider a production estimator change, which needs approval.
* **H2:** CLV logging per paper selection and decision-shadow row (≈ 1 credit per bet; design in the objective
  audit §19). Test mean CLV > 0 at 30–50 bets.
* **H3 / H7:** the decision shadow already records every quote decision. Add net-of-commission venue comparison at
  the interim review. 0 credits.

## 19–20. Data gaps and acquisition options (no purchase)

| Rank | Dataset | Value | Cost | Free alternative |
|---|---|---|---|---|
| 1 | **Prospective CLV + full-panel prices** (our own scans) | Highest. The only class-A source; tests H2, H3, H7 | ≤ 22 credits/month at ≤ 5 bets/week; 0 for the decision shadow | — |
| 2 | **The Odds API historical, 1 month (20k credits)** | Class-A replay of tennis and football at decision time across 20 books, so H3/H7 can be answered in weeks instead of months | ~$30 (third-party published; unverified) | none |
| 3 | Betfair historical PRO (ladders, volumes) | Exchange spread and liquidity, timing | paid, price unverified | BASIC (held; LTP only) |
| 4 | Lineup / injury feeds with timestamps | Tests the "non-public / faster information" route | varies; often paid | partial scraping, licence risk |
| 5 | Richer xG / shot data (free sites) | Low, given the H6 null | free | — |

## 21. Recommendation (A–H)
* **A. Most promising evidence-backed path:** execution quality at decision time. Measure CLV and full-panel
  (20-book plus exchange) dispersion on real decisions.
  * It is the only mechanism with a positive regularity (CLV predicts return).
  * It is the only place where our data is *wider* than history (20 live books versus 4–6 historical).
  * It costs almost nothing.
* **B. Second:** fix the probability estimator's known flaw (H1, power de-vig) in shadow. It will not make money by
  itself, but it removes a systematic calibration error from Stage A. It also stops us mistaking a de-vig artefact
  for an edge, as nearly happened.
* **C. Stop:**
  * multis;
  * Elo / form / rank or other public-feature models;
  * threshold tuning;
  * underdog or draw strategies at UK books;
  * football high-P as an edge;
  * NBA spreads and totals;
  * more league or market expansion.
* **D. Overlooked:**
  1. **The de-vig artefact.**
  2. **Economics:** even a genuine +2% edge on £30–£50 at 1% stakes is pennies a month. And soft-book line-shoppers
     who win get **restricted**, which caps the very mechanism most likely to work. Exchanges avoid restrictions but
     charge commission.
  3. **Wider live panel:** historical dispersion nulls were measured on 4–6 books. The live panel is 20 books, so
     the prospective test is not redundant.
* **E. If this were my platform:**
  * run the frozen system for about 8–12 weeks purely as a measurement instrument: CLV, dispersion, H1 shadow;
  * spend the one optional ~$30 on a pre-registered historical decision-time replay (option 2), after a 1-call
    format check;
  * make the go / no-go on money only from CLV plus qualified-set calibration.
* **F. Is the probability-first architecture right?** Yes for prediction. But be clear-eyed: because P ≈ market, the
  *betting* layer is unavoidably a price-comparison problem. That is a property of the probabilities, not a drift.
* **G. Is consensus still the right baseline?** Yes, with H1's de-vig method as the candidate refinement.
* **H. Where next cycle's effort should go:** decision-time price data (prospective CLV / dispersion; optional paid
  replay) and the H1 shadow. Nothing else.

## 22. Do not research further
* Multis and round robins.
* Public-feature hybrids.
* Threshold sweeps.
* Underdogs and draws at UK books.
* Pinnacle as the probability source.
* NBA spreads and totals.
* Tennis secondary markets.
* League expansion.

## 23. Strong enough for a prospective shadow test?
**Yes, two, both zero or near-zero cost and neither a betting rule:**
* H1, the de-vig shadow;
* H2, CLV measurement (needs your approval as a production addition, about 1 credit per bet).

Nothing justifies a new paper or money rule.

## 24. The single smallest next step
Pre-register H1 and add a **research-only shadow column**: the power-de-vig football P, computed from the raw book
prices already stored, written to a separate research file and never to the ledger. That costs 0 credits. Then
evaluate it at the protocol interim. It needs your approval because it touches a production workflow; the code
itself is trivial.
