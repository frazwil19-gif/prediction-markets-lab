# V2-18 — Existing-sport expansion study: pre-registration (fixed 2026-10-01, BEFORE any outcome analysis)

Nothing here changes a frozen engine, a threshold or production. The study is historical and exposed-data only; there is no fitting, so "validation" means stability across periods.

## 1. Football data

| Item | Value |
|---|---|
| **Source** | `github.com/xgabora/Club-Football-Match-Data-2000-2025`, file `data/Matches.csv` (MIT) |
| Commit | `25882a58a736daf7ece3781940eac17ae1117a66` |
| sha256 | `ef224cf2c252f07a842b3bcfd4ba5c718c25cedd8937ffa174a74b86b5ba4221` |
| Coverage | 238,858 matches, 2000 → 3 Sep 2026; derived from football-data.co.uk |
| Columns used | Bet365 1X2 (`OddHome/OddDraw/OddAway`); Bet365 O/U 2.5; Bet365 Asian handicap (line + odds); max-over-books 1X2; results |

**Why this source:** football-data.co.uk is blocked from this sandbox (proxy 403), and the repo's processed panels are not on disk. The raw file is **not committed** (45 MB). The analysis script records its URL, commit and sha256, and fails if the hash differs.

**Estimator used here:**
- per-match **Bet365 single-book** multiplicative de-vig (no fitting);
- a proxy for the live estimator (median of about 20 UK books, 24–48h before kickoff);
- the B365 pre-match odds in football-data are taken days before kickoff, not at the close, which is temporally *closer* to the live snapshot than the closing panels used previously.

**Proxy check (pre-declared):** E0/E1/SC0 results here are compared with the repo's prior results (Gate 1 log loss by league; V2-1 bands). A material discrepancy is reported, and makes the proxy unusable for any league verdict.

## 2. Leagues

| Role | Leagues |
|---|---|
| **Reference** | E0, E1, SC0 |
| **Candidates** (required) | E2 (League One), E3 (League Two), SP1, D1, I1, F1 |
| **Candidates** (also supported by football-data, the Odds API and settlement) | SP2, D2, I2, F2, N1, P1, B1, T1, G1, SC1 |

**Seasons** (season boundary 1 July):

| Period | Seasons | Notes |
|---|---|---|
| Development | 2017/18–2021/22 | 2019/20 and 2020/21 flagged COVID; reported, not excluded |
| Validation | 2022/23–2024/25 | |
| Confirmation | 2025/26 | |

**Rows used:** a match is used if FT result and all three B365 1X2 odds are > 1.0. Missingness is reported.

## 3. Metrics (per league × period)

- matches, odds coverage;
- multiclass log loss and Brier;
- pooled H/D/A one-vs-rest calibration intercept/slope, with a **match-clustered bootstrap** 95% CI (1,000 resamples, seed 20261001);
- per-outcome (H/D/A) slope;
- 5pp band table with Wilson 99.5% intervals;
- top-pick ≥0.60/0.70/0.80 predicted vs actual;
- DC best-pick ≥0.80;
- per-season slope;
- **volume:** matches/week, top 1X2 ≥0.70/0.80 per week, DC best ≥0.80 per week.

## 4. Pre-registered grade (identical to the V2-4 DC / V2-1 gate logic)

| Criterion | Definition |
|---|---|
| C1 | Calibration slope 95% CI includes 1 in **both** validation and confirmation |
| C2 | Every 5pp band with n ≥ 200 (all H/D/A events) has its mean predicted inside the 99.5% Wilson interval, in both periods |

- **Grade A** = C1 and C2.
- **Grade B** = exactly one.
- **Grade C** = neither.
- A confirmation season with fewer than 200 matches is reported as LOW_N, and C1/C2 then use validation only, flagged.

## 5. Classification

| Status | Rule |
|---|---|
| **EXPAND NOW** | Grade A **and** an Odds API sport key exists **and** a football-data current-season settlement file exists, **ranked** by strong predictions/week per incremental credit, and selected only while the projected monthly total stays ≤ the 425-credit target (Plan A accounting). Live UK coverage (≥ 3 books per fixture, as the existing consensus requires) is verified on the first gated scan; failing leagues are auto-reported, not used. |
| **PROSPECTIVE SHADOW** | Grade A beyond the credit budget, or grade B. Collected only if credits allow; never paper-bet before review. |
| **NEEDS MORE RESEARCH** | Grade C, or odds coverage < 95% in validation + confirmation, or fewer than 900 matches across them. |
| **REJECT** | Grade C with the slope CI excluding 1 in **both** periods **and** band failures; or no live key / settlement. |

**Incremental credits:** h2h + totals (2 credits) × paying days. The Plan A gate pays only on days with a fixture within 48h. Paying days per month are estimated from the historical fixture-date distribution (days with ≥ 1 match in the following 48h) over 2023/24–2025/26.

## 6. Football markets (pooled reference + candidate leagues; same periods and grade)

| Market | Probability definition |
|---|---|
| 1X2 / DC | As above |
| O/U 2.5 | B365 over/under de-vig → P(over) |
| BTTS | Market-implied independent Poisson. λ_home, λ_away are solved so that the Poisson model reproduces the de-vigged 1X2 home/away probabilities and P(over 2.5) in least squares. P(BTTS) = (1 − e^−λh)(1 − e^−λa). No BTTS odds exist historically, so Stage B is historically blocked. |
| DNB | P(home \| not draw) = P_H / (P_H + P_A), evaluated on non-draw matches (void on draw) |
| AH | B365 line; **half-ball lines only** (binary outcome), de-vigged home/away cover probability. Whole and quarter lines are reported as excluded counts. |

The same grade applies. **Strong-prediction frequency is reported, never used to pass a market.**

## 7. NBA spread/total and tennis secondary markets

- **NBA spread/total.** The audit checks for historical closing spreads, totals and scores (repo sources, then GitHub-hosted free sources). It reports the distribution of market-implied cover/over probabilities (vigorous two-way lines imply ~0.5) and whether any **strong** prediction region exists. A sports-derived model must be calibrated, and its probabilities must extend materially beyond 0.5, to matter for the probability-first board.
- **Tennis.** The audit checks data availability (scores with set/game detail, historical odds for those markets, live UK availability via the Odds API). No model is fitted in this sprint.

## 8. Outputs

- `research/platform_v2/v2_18_expansion/RESULTS.json`, plus tables;
- `REPORT.md` (the sprint report).

Negative results are kept.
