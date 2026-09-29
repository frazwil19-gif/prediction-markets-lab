# Phase V2-6H — Historical Data Audit and Bet-Selection Backtest Feasibility: Return Checkpoint (2026-09-29)

**Label:** retrospective research simulation. No paper bets were written. The frozen engines, sealed holdouts, thresholds,
ledgers and workflows are unchanged. Pre-registered in `PREREGISTRATION.md` (commit `b4a56a4`) before any betting number was
computed. Code: `scripts/v2_6h_historical_backtest.py`. Numbers: `V2_6H_RESULTS.json`. Rules: `bsv2-1` exactly. There was no
threshold search; sensitivities are descriptive only.

## 1. Inventory
| engine | source | period | n | price type in data | timestamps | per-book executable prices | licence |
|---|---|---|---|---|---|---|---|
| ATP match winner | Betfair historical BASIC (Fraser download) + TML results | 2021–2025 | 12,202 | exchange **last-traded price** (LTP), both runners | market start; LTP near the frozen snapshot | **no** (no back/lay, no bookmakers) | Betfair personal-use terms |
| WTA match winner | Betfair BASIC + TennisCourtLog | 2021–2025 | 10,352 | LTP | as ATP | **no** | as ATP; CC BY-NC-SA results |
| NBA moneyline | wippa (OddsPortal) | 2016-17 → 2025-26 (19-20, 20-21 not on disk) | 10,527 on disk (12,825 in the audit) | one **average closing** price per side | none | **no** | MIT |
| Football 1X2 | football-data.co.uk, E0/E1/SC0 | 2020/21 → 2025/26 | 6,960 | **per-book** odds at 2 snapshots: pre-closing (Fri/Tue collection) and closing (kick-off) | collection convention only, no exact time | **yes**: B365, WH, BW, BF (2024/25), plus PS, 1XB; 2025/26 adds Betfred, BetMGM, BetVictor, Coral, Ladbrokes | free, non-commercial |
| Football O/U 2.5 | football-data.co.uk | 2020/21 → 2024/25 | 5,800 | B365, Pinnacle, Betfair Exchange (2024/25 only) | as 1X2 | B365 (+BFE 2024/25) | as above |
| Football Double Chance | derived from the 1X2 panel | 2020/21 → 2025/26 | 5,897 | **no DC prices at all**, only synthetic dutching of 1X2 | — | **no** as a single price | — |

## 2. Existing backtests reproduced (no holdout reopened for tuning; all were already opened once)
| engine | reproduced here | committed claim | match |
|---|---|---|---|
| ATP holdout 2024–25 | n 5,066; slope 0.986; ≥80% 87.6% → 87.4% | n 5,066; slope 0.986; 87.6 → 87.4 | ✅ exact |
| WTA holdout 2024–25 | n 4,339; slope 0.979; ≥80% 86.9% → 87.0% | n 4,339; slope 0.979 (CI 0.90–1.06); 86.9 → 87.0 | ✅ exact |
| NBA holdout 2024–26 | n 2,629; ≥80% 85.5% → 87.5% | n 2,629; 85.5 → 87.5 | ✅ exact |
| Football 1X2 consensus (closing) | favourites ≥70%: dev 77.5% → 80.5% · 2024/25 77.6 → 78.0 · 2025/26 76.3 → 80.6 | "slope 1.06–1.09, slightly flat" | ✅ consistent (mild under-confidence) |
**Probability quality is confirmed for every engine.** The favourite-side bands are calibrated to within about 1 pp (tennis, NBA),
and football favourites win slightly *more* often than consensus implies.

## 3. Price audit: which data can test a *bet*, not just a *prediction*?
- **Tennis:** the only prices are Betfair LTP, the same prices that produce P. LTP is not an executable back price, there are
  no bookmaker odds, and there is no back/lay spread. Against its own source, with 5% commission: mean net EV −1.7% (ATP) / −1.8% (WTA);
  level-stake ROI backing every favourite −2.6% / −2.7%. The 2.3–2.6% of rows with "positive EV" come from LTP pairs whose book sum
  is below 1, a data artefact, not value. **A V2-6 betting backtest is not possible.**
- **NBA:** one OddsPortal average closing price. Not executable; EV = −margin (−3.6%) by construction. **Not possible.**
- **Double Chance:** no DC prices exist in any dataset. Dutching two 1X2 selections is executable in principle, but it is not a
  `bsv2-1` rule. **Not possible under frozen rules.**
- **Football 1X2:** the only genuine as-of, per-book historical prices we hold. **Possible, with limits:** there are no exact
  timestamps; the closing snapshot is taken *at* kick-off (optimistic executability); football-data's "BF" column in 2024/25 may be
  the Betfair sportsbook rather than the exchange (5% commission applied anyway, conservatively); and we can't verify that a quote
  was available at stake size.
- **Football O/U 2.5:** at most 3 books, and only 2024/25 meets the frozen ≥ 3-book rule.

## 4. V2-6 historical simulation (football, the only market where it is legitimate)
**Funnel, 1X2, 6 seasons, 6,960 matches (20,880 match-selections):**
| | A: closing (primary) | B: pre-closing (horizon gate not evaluable) |
|---|---|---|
| P ≥ 0.50 (favourites) | 2,985 | 2,928 |
| …with a positive-EV UK price | **15** | **2** |
| PAPER_BET-equivalent (P ≥ 0.5, EV ≥ 2%, odds ≥ 1.33) | **8** (0.27%) | **2** |
| selections per match day | 0.007 (8 in 863 match days) | 0.002 |
| est. net EV of those | +7.8% | +8.7% |
| realised | −0.44 u, ROI −5.5% (95% CI −72% to +66%) | −0.05 u |
| periods with any selection | 2021/22 (6), 2022/23 (1), 2023/24 (1); **0 in 2020/21, 2024/25, 2025/26** | 2020/21 (2) |

- **Baseline, accuracy without value:** backing all 2,985 favourites at the best primary UK price gives a win rate of 63.6%
  (matching the mean P of 62.3%) and ROI **−2.6%** (CI −5.4% to +0.1%) at closing. At pre-closing it's **−3.1%** (CI −5.9% to −0.2%).
  The predictions are accurate and the bets lose, because the bookmaker margin is larger than the favourite bias.
- **The 8 "value" bets are mostly single-book outliers.** For example, WH 2.25 while B365/BW/PS quoted 1.55–1.63. These quotes at
  kick-off are the least trustworthy: stale, void-able as a palpable error, or limited in size.
- **O/U 2.5:** 0 qualifying bets at either snapshot (2024/25; 9 and 1 positive-EV favourites).
- **Descriptive sensitivities** (not used to choose anything):
  - EV floor 0% → 14 bets (−8.7%)
  - EV floor 5% → 3 bets
  - leave-one-out consensus → 10 bets (+10.7%, CI −48% to +64%)
  - adding Pinnacle, 1xBet and the 2025/26 UK books → 16 bets (−28.8%)
  
  None is distinguishable from zero.
- Bankroll simulation: **not meaningful** with n = 8. There is no drawdown or survival claim.
- CLV (pre-closing selections against closing fair odds): n = 2, both positive. Uninformative.

## 5. Per-engine answers
| engine | historical samples | calibration | real executable odds | backtest feasible | historical bet frequency | net ROI (CI) | key limitation | most valuable next dataset |
|---|---|---|---|---|---|---|---|---|
| ATP | 12,202 (2021–25) | ✅ holdout slope 0.986 | ✗ LTP only | ✗ | — | self-source −2.6% | no bookmaker/back prices | as-of UK bookmaker + Betfair back/lay snapshots (Odds API historical) |
| WTA | 10,352 (2021–25) | ✅ 0.979 | ✗ | ✗ | — | self-source −2.7% | as ATP | as ATP |
| NBA | 10,527 on disk | ✅ 85.5 → 87.5 | ✗ average close | ✗ | — | −3.6% by construction | no per-book prices | Odds API historical (per-book h2h) |
| Football 1X2 | 6,960 (2020/21–2025/26) | ✅ mild under-confidence | ✅ per-book, 2 snapshots | ✅ with limits | **8 in 6 seasons** (0.007/match day) | −5.5% (CI −72% to +66%); favourites −2.6% | no exact times; outlier quotes | exact-timestamp snapshots (Odds API historical, 5–10 min) |
| Football O/U | 5,800 | ✅ (registry) | B365 (+BFE) | 1 season only | 0 | — | too few books | Odds API historical totals |
| Double Chance | 5,897 | provisional (sealed 2026/27) | ✗ none | ✗ | — | — | no DC market prices | DC prices at a screened subset (live) |

## 6. Data gaps and acquisition options (nothing purchased; researched, not verified by purchase)
1. **The Odds API historical endpoint.** It holds the same data and source as production (`betfair_ex_uk` back/lay plus UK books)
   as as-of snapshots: every 10 min from 6 Jun 2020, every 5 min from Sep 2022. It costs **10 credits per region per market per
   snapshot**, and each snapshot returns a whole sport key. It needs a **paid plan**; published third-party pricing is 20K credits
   for about $30/month. A rough budget: one pre-match snapshot per active tennis key per day for 2024–2026 is about 1,000–1,500
   key-days × 10 ≈ 10–15K credits, so a single month of the 20K plan could plausibly cover the tennis V2-6 question with the *exact
   production estimator and price hierarchy*. Estimate only, to be confirmed on one paid test call. **This is the single most
   valuable dataset: the first that can answer V2-6's central question outside live collection.**
2. **tennis-data.co.uk:** free per-match Bet365/Pinnacle/Max/Avg tennis odds. Blocked from here (403 / TLS). Fraser can download it
   manually from a browser. Its collection timing is not documented in anything we've verified; treat it as near-closing. It is
   useful for dispersion between bookmakers and the Betfair LTP, but weaker than (1).
3. **Betfair historical data:** BASIC (free, what we hold) has LTP only. Richer tiers with ladder depth are paid; price not verified.
   That would give real back prices, but no bookmakers.

## 7. Does this change the prospective evidence requirements?
**No gate is loosened. One expectation is updated.**
- The historical record predicts that, under `bsv2-1`, a PAPER_BET will be **rare**: football gave about 1 per 100 match days. The
  live gate's "≥ 300 settled PAPER_BET singles" could therefore take **years** unless tennis bookmaker dispersion turns out
  materially larger. That is now measurable live, at 0 credits.
- If prospective tennis collection repeats the football pattern (EV ≤ 0 almost everywhere), the correct outcome is a recorded
  **negative result: "accurate probabilities, no purchasable value at UK retail prices."** It is not a reason to lower the 2% floor,
  which historical data shows would only add noise (the 0% floor lost −8.7%).

## 8. Recommendation
- **Can be tested now (done):** probability quality for all engines (confirmed); a V2-6 football backtest (done, near-zero
  frequency, no evidence of value).
- **Must await data:** tennis and NBA betting economics. Either (a) wait for prospective V2-6 price snapshots (free, slow, starts
  today), or (b) buy **one month of The Odds API 20K plan (~$30)** for a pre-registered historical replay with the exact production
  pipeline. That is Fraser's decision. I'd first make one paid test call to confirm the snapshot format and the credit cost before
  committing the month.
- Keep production collection unchanged. No engine promoted; no real money.
