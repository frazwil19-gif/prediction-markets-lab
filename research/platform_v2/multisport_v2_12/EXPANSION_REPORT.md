# V2-12 — Multi-Sport Expansion Report (audit + design; nothing deployed)

Date: 2026-10-01. Branch `v2-12-multisport-roadmap` (docs only).
Method: repository artefacts were read directly (the football and NBA inventories were cross-checked by spot re-computation), and free NHL sources were checked on the web with URLs cited. No outcomes were used to tune anything, no data was bought, and nothing was activated.

**Status legend:** READY FOR PROSPECTIVE SHADOW · NEEDS SMALL FIX · NEEDS RESEARCH · DATA BLOCKED · REJECT FOR NOW.

## Summary verdicts

| Sport / market | Stage A (probability) | Stage B (financial) | One-line reason |
|---|---|---|---|
| Tennis Match Winner (ATP/WTA, Betfair mid) | **LIVE** (prospective since 23 Sep) | **NEEDS SMALL FIX** (bsv2-4 pending merge) | Validated holdouts; V2-10 merged; bsv2-4 closes the last known gate bypass |
| Football 1X2 (market consensus) | **NEEDS SMALL FIX** | **NEEDS SMALL FIX** | Validated on exposed seasons and wired since V2-5, but 0 prospective rows yet; live estimator ≠ validated estimator; 2 settlement aliases missing; no σ |
| Football Double Chance (derived 1X2) | **READY FOR PROSPECTIVE SHADOW** (with a holdout no-peek rule) | **DATA BLOCKED** | Strong exposed-data calibration; sealed 2026/27 holdout pending; no historical DC odds; live DC quotes not fetched; ≥80% picks sit below the 1.33 payout floor |
| Football O/U 2.5 | REJECT FOR NOW (as a strong-prediction source) | DATA BLOCKED | Almost never ≥80%; historical Stage B blocked (<3 books) |
| NBA Moneyline (market consensus) | **NEEDS SMALL FIX** (activation 20 Oct already configured) | **NEEDS SMALL FIX** | Holdout verified; but snapshot timing, duplicate-on-flip, no freshness check, no σ, and an unparseable price source |
| NHL Moneyline | **NEEDS RESEARCH** | **NEEDS RESEARCH** | Free data is sufficient for a feasibility/discovery study; key blockers are pre-game goalie data, a 2023–26 odds gap, and UK 3-way/2-way market ambiguity |

**The binding constraint is not models, it is Odds API credits** (§17–18). On the free 500-credit plan, Tennis + Football + NBA already uses about 410–425 credits a month at current scan rates. Tennis's own 120-credit cap will stop the tennis board around **20 October** at the current burn of about 6 credits a day.

---

## 1. Tennis / V2-10 / bsv2-4 status

**V2-10 status.** Merged to master as `2ba3cac` on 2026-10-01 at 00:41 BST.
- Production suite: 1206 passed. Research suite: 54 passed.
- Frozen paths and the V2-7 fingerprint `9e52b67df08691d0` are unchanged.

**First scheduled run after the merge.** This was run 36800820871 (commit `de7ba21`, 01:22 UTC), the 22:30 settlement-only cron.
- The board step was skipped (no scan); the unified board build and bsv2 settlement ran.
- The est-1 resolution is present: ELIGIBLE 72, EXCLUDED 53 (all with reason EVENT_STARTED), 53 eligible-rescheduled.
- The Stage A board was built with 56 rows / 26 strong, all PRICE_QUALITY_FAIL. That is correct, because every quote was older than 240 minutes.
- `bet_selection_v2_start_time_resolution.csv` is written only by `evaluate`, which the settlement run does not execute.
- **Scan-run verification: PENDING** until the next 06:30 or 15:30 UTC board run commits.

**bsv2-4.** Branch `v2-11-spread-gate-ledger-path`, now at `30860b4`.
- **EXCHANGE_BACK audit:**
  - Back-only Betfair P has an unmeasurable book width.
  - It has never been validated separately and has never been observed (0/172 snapshots).
  - **Revised:** it now fails closed for financial use. The reconstruction is byte-identical and the test was replaced.
- **Bai carry-forward audit:**
  - The carry-forward was mechanically re-derived on the decision-time inputs (betway 1.73, P 0.5986, width 0.0097, EV +3.55%), with no outcome read. **KEEP.**
  - Caveat: the label `VALID_SAME_SNAPSHOT` is overloaded; analyses must split by origin rule version.
- **Recommendation: MERGE after the scan-run checkpoint PASSES.** Details are in that branch's REPORT.md, Addendum A1.

## 2. Football asset inventory

The single registry is `research/platform_v2/PROBABILITY_ENGINE_REGISTRY.json`.

| Engine | Market | Version | Status | Hist. n | Holdout | Money-eligible | Probability source |
|---|---|---|---|---|---|---|---|
| `football_1x2.market_consensus` | 1X2 | v1 | VALIDATED_HISTORICAL | 5,776 | DONE (2024/25, opened once) | true | Live: per-book proportional de-vig, **median** of about 20 UK Odds API books, snapshot ≤48h. Validated: closing B365/BW/PS **mean** (V2-1) / median of ≥4 books (Gate 1) |
| `football_double_chance.derived_1x2` | DC 1X/X2/12 | v1 (frozen; no fitting) | PROVISIONAL_PROSPECTIVE | 5,897 | SEALED 2026/27 Aug–Dec, opens ≥ 2027-01-03 | false | Pairwise sums of renormalised 1X2 |
| `football_ou25.market` | O/U 2.5 | v1 | VALIDATED_HISTORICAL | 4,640 | DONE | true | Thin market panel (2–3 books) |
| `football_btts.market_implied_poisson` | BTTS | v1 | RESEARCH_VALIDATED | 4,595 | DONE | false | Not wired |

**Key evidence for 1X2** (all seasons now exposed):

- **Stage 3B sealed 2024/25 holdout** (`CYCLE_001/results/STAGE_3B_FINAL_REPORT.md`):
  - n = 1,160; market log loss 0.9937, Brier 0.5931.
  - Elo + Poisson was worse (+0.0169 log loss); blends put 100% weight on the market.
  - Verdict: **"market dominates / null"**.
- **Gate 1 walk-forward 2021/22–2025/26** (`CYCLE_003_FOOTBALL/GATE1_CHECKPOINT.md`):
  - n = 5,631 out-of-sample; market log loss 0.987, Brier 0.589.
  - Slopes: home 1.053, draw 1.005, away 1.045. AUC: home 0.70, draw 0.56, away 0.70.
  - Log loss by league: E0 0.955, E1 1.034, SC0 0.931.
  - **2025/26 is the worst season at 1.015.**
- **High-probability bands** (V2-1, multiplicative de-vig):
  - top pick ≥70%: dev 77.6 → 79.8 (n 331); val 77.6 → 81.5 (n 232);
  - top pick ≥80%: dev 83.6 → 86.3 (n 117); val 84.2 → 94.2 (n 69);
  - 2025/26 had only 5 matches at ≥80%.
- **Leakage:** none found for the market engine (closing odds are pre-match by construction).
- **Prices:** historical closing and opening odds come from football-data.co.uk. Live prices come from the Odds API (`regions=uk`, `h2h` + `totals`, 3 leagues).
- **Negative results kept on record:**
  - Stage 3B null; Gate 1 and Gate 1b fundamentals all worse than market;
  - H-FB2-001 REJECTED; H-FB2-002 sealed OOS FAIL (terminal);
  - V2-6H: 8 qualifying 1X2 value bets in 6 seasons, ROI indistinguishable from 0.

**Live state.**
- **0 football rows** have ever reached `predictions/unified_ledger.csv`. Every daily card since 22 Sep holds the same 38 fixtures, which kick off from 9 October; the reason is the OUTSIDE_48H_WINDOW skip during the international break.
- **First football Stage A rows are expected automatically from about 7–8 October**, through the existing approved V2-5 wiring. No new activation is needed. This is flagged so it is a conscious decision.

## 3. Football 1X2 readiness — **NEEDS SMALL FIX**

The probability quality is historically well supported, and the market is the best estimator the project has found. However:

1. **Estimator mismatch (most important).** The live estimator is the median of about 20 UK books taken 24–48h before kickoff; the validated estimator is a closing mean or median over a fixed panel.
   - The DC study's "stored median consensus" variant suggests the mean/median choice is immaterial (≥80%: 86.39 → 86.40).
   - **Snapshot timing (early vs closing) has never been validated.**
   - Fix: label the live estimator `football_1x2.market_consensus@1-live` in provenance and let prospective data test it. Do not claim the historical calibration applies unchanged.
2. **The 1X2 triplet is not renormalised** in ledger rows (sums 0.992–1.006). DC renormalises; 1X2 does not.
   - Decide and pre-register one rule (renormalise for Stage A display; keep the raw values for provenance).
3. **Settlement aliases are missing** for "Bolton" and "Lincoln" (`status/settlement_shadow.json` → `fd_unresolved_names`). Two fixtures on the current card would land UNRESOLVED_NAME.
   - The settlement migration shadow gate also shows `passed: false` (0/100 comparisons). It needs re-checking once October results exist.
4. **No σ on Stage A** (σ is tennis-only). A per-band Wilson SE from the Gate 1 / V2-1 bands is needed (pre-register the source).
5. **Champions League is configured but not covered** (no sport key, no settlement mapping). It must stay out until covered.

**Shortest safe path.**
- **Stage A:** let the existing wiring populate from about 8 Oct, after fixes 2–5. Display P with basis `P_FIRST_SNAPSHOT`.
- **Stage B:** bsv2 already prices 1X2 from the latest card (`prices.football_from_card`). Under the existing gates (24h horizon, odds ≥ 1.33, EV ≥ 2%), the realistic outcome is very few or no qualifiers. This is consistent with V2-6H and acceptable.

## 4. Football Double Chance readiness — Stage A **READY FOR PROSPECTIVE SHADOW**; Stage B **DATA BLOCKED**

**Formula verification.**
- `prediction_platform/adapters.py:110-126` computes 1X = q_H + q_D, X2 = q_D + q_A, 12 = q_H + q_A on the renormalised triplet q. This matches the required identities.
- The research path `research/double_chance.py` is identical and enforces Σ = 1 within 1e-6.
- Tests: `tests/unit/test_double_chance.py`, `test_prediction_platform.py:72-83`.

**Evidence** (`research/platform_v2/double_chance/DC_REPORT.md`, pre-registered before results). It covers 5,897 matches across E0/E1/SC0, 2020/21–2025/26, and **all of it is exposed**.

| Period | Slope | Best-pick ≥80%: predicted → won (n) |
|---|---|---|
| Development | 1.062 | — |
| Validation | 1.088 | 86.5 → 88.0 (631) |
| 2025/26 confirmation | 0.949 | 85.2 → 89.1 (129) |

- Overall, ≥80% best-pick is 86.3 → 87.1 (n 1,855, 31.5% of matches).
- The engine is under-confident at the top (≥90%: 92.8 → 95.0).
- Weakest cell: E1 2021/22 ≥80%, 84.2 → 79.2 (n 130).
- The 12 selection is never the best ≥80% pick; 1X dominates (1,353 of 1,855).

**Financial side.**
- There are **no historical DC odds** anywhere.
- Live DC quotes exist only on the Odds API per-event endpoint, at 1 credit per event per region; the probe found 4 UK books at about a 5% margin. They are not fetched.
- The current "price" is a synthetic dutch of the best 1X2 prices across books, which is **not executable**.
- At P ≥ 0.80, fair odds are ≤ 1.25, below the 1.33 payout floor, so **a DC single can never qualify under the current policy**. DC's role is probability board and future multi legs.

**Required before relying on DC Stage A:**
- (a) Fix the registry text inconsistency ("prospective: DESIGNED, not active" vs `COLLECTING`), and record your explicit approval for DC collection; I found no approval record.
- (b) **Holdout protection.** Prospective DC rows for Oct–Dec 2026 are on the same matches as the sealed DC holdout (2026/27 Aug–Dec, opens ≥ 2027-01-03). Two steps:
  - add a **no-peek rule**: DC performance is not reported before the holdout is opened, or the prospective ledger is declared to be the holdout's estimator test;
  - write a guarded one-shot holdout opener script; none exists yet, unlike tennis and NBA.

## 5. Recommended initial football universe

**Start with E0 + E1 + SC0 only** (the leagues with historical evidence, fixture keys and settlement mapping).

| League | Historical depth | 1X2 log loss (Gate 1) | DC ≥80% share | Settlement | Live keys |
|---|---|---|---|---|---|
| Premier League (E0) | 2020/21–2025/26 | 0.955 (n 1,888) | about 40–45% | E0 | `soccer_epl` |
| Championship (E1) | same | 1.034 (n 2,640) — weakest | about 16–26% | E1 | `soccer_efl_champ` |
| Scottish Premiership (SC0) | same | 0.931 (n 1,103) | about 36–44% | SC0 | `soccer_spl` |

The Odds API keys are marked "not yet independently confirmed" in config, but cards with E0/E1/SC0 fixtures do exist (38 fixtures: 19 / 12 / 6 by event, plus 1).

**Do not add leagues blindly.** Candidates for a later research gate are leagues with football-data.co.uk history, an Odds API key and enough UK books (e.g. L1/L2, La Liga, Serie A, Bundesliga). Each needs its own calibration check and settlement mapping, and adds 2 credits a day per league.

**Expected volume** (from the historical panel, about 1,160 matches per season over about 40 weeks ≈ 29 fixtures a week):

| Market | Per week |
|---|---|
| 1X2 predictions | about 87 (29 × 3 rows) |
| 1X2 top pick ≥0.70 | about 3 |
| 1X2 top pick ≥0.80 | about 1 |
| DC rows | about 87 |
| DC best pick ≥0.70 | about 27 |
| DC best pick ≥0.80 | about 9 |

Week 41 (the card in hand): 27 fixtures; 1X2 ≥0.80 = 1; DC best ≥0.80 = 6.

## 6. Exact football gaps before prospective deployment

1. Aliases: Bolton, Lincoln; re-run the settlement migration shadow once October results exist.
2. Pre-register 1X2 renormalisation for display, and the live-estimator provenance label.
3. A football σ source for Stage A (band Wilson SE), pre-registered.
4. DC registry text fix and a recorded approval.
5. A DC holdout no-peek rule, plus a guarded opener script.
6. Fix or remove Champions League from `competitions.yaml`.
7. Decide whether to spend credits on live DC quotes (per-event, 1 credit each). **Recommendation: no**, until DC multis are a live research question.

None of these change thresholds or frozen engines.

## 7. NHL free-data inventory (web-verified 2026-10-01; URLs in `NHL_DATA_INVENTORY.md`)

| Source | Data | Years | Access / terms | Leakage notes | Cost |
|---|---|---|---|---|---|
| NHL web API `api-web.nhle.com/v1` | Schedule, scores, `gameType`, `gameOutcome.lastPeriodType` REG/OT/SO, boxscores, PBP, goalie `starter` | Many seasons | Unofficial, no key, no published terms or rate limit; **blocked by this sandbox's proxy** (GitHub runners untested) | `starter` is post-game only, never a feature | Free |
| NHL stats REST `api.nhle.com/stats/rest` | Team/player summaries (W, L, OTL, SO wins) | Many | As above | Season totals leak in-season | Free |
| MoneyPuck downloads | Game-level team xG, shots; shot-level 2007/08–2026/27 | 2008/09+ | Free for non-commercial use with credit; no scraping | Lag xG; model refits could leak retroactively | Free |
| SBRO NHL odds archive | Open/close moneyline, puck line, totals | **2007/08–2022/23 only (frozen)** | Free download; terms unverified | Closing line is a benchmark only | Free |
| Kaggle (CC0) ESPN-derived | Favourite moneyline, spread, totals | 2004–Dec 2025 | CC0 | Odds timing unknown | Free |
| DailyFaceoff | Projected / confirmed starting goalies, timestamped | Archive shows final state | Terms unverified; treat as no scraping | **Historical archive is not as-of** — must be snapshotted live | Free |
| Odds API `icehockey_nhl` | Live h2h/spreads/totals, UK books | Live; historical from 2020 | Historical is paid-plan only, 10× cost | — | Credits |
| Natural Stat Trick, Hockey-Reference | Rich stats | Decades | **Scraping prohibited** without permission | — | Not used |
| Evolving-Hockey | RAPM/GAR | — | Paid | — | **Not used** |

## 8. NHL Moneyline feasibility — **NEEDS RESEARCH**

The free data is sufficient for a leakage-safe feasibility and discovery study, but not yet for a model.

**Target definition (verified).** UK "Money Line" includes overtime and shootout:
- William Hill, Sky Bet, Betfair Sportsbook and bet365 all state this;
- the Betfair Exchange "Moneyline" includes OT and SO;
- "Match Result / 3-Way / 60-minute / Regular Time" markets exclude them.

**The Odds API warns that EU/UK books may return regulation 3-way odds under `h2h`.** The pipeline must check each bookmaker for a Draw outcome and never mix 3-way and 2-way. The project target is the 2-way winner after OT/SO, labelled from the final score, with `lastPeriodType` recorded.

**Blockers:**
1. The starting goalie (likely the most informative pre-game variable) has no free, timestamped historical record.
2. Free odds stop at 2022/23 (SBRO). Later seasons need Kaggle favourite-only lines of unknown timing or paid-credit historical snapshots.
3. The sandbox proxy blocks `nhle.com`, so data collection must run where access is allowed.
4. 20.7% (2024/25) and 24.8% (2025/26) of games were decided in OT/SO, so discrimination will be lower than football or NBA. The high-probability share is likely small, and must be measured, not assumed.

**Schedule.** The 2026/27 season opened on 29 Sep 2026.
- 84 games per team (Wikipedia only) gives 1,344 games, about 49 a week.
- Live forward collection could start any time (1 credit per scan).

## 9. NHL leakage-safe research plan (proposed; to be pre-registered before any modelling)

1. **Data audit.**
   - Pull NHL API results for 2010/11–2025/26 (regular season and playoffs flagged; REG/OT/SO), MoneyPuck team game-level data, and SBRO odds 2010/11–2022/23.
   - Reconcile team names and game ids and report missingness.
   - Run where `nhle.com` is reachable.
2. **Target.** The 2-way winner after OT/SO (the UK moneyline). A separate 3-way regulation target is research-only.
3. **Leakage-safe dataset.** Every feature is computed as-of the game date from strictly prior games. No season totals, no post-game `starter`, and lagged xG only. Unit tests assert future-invariance, as in the NBA study.
4. **Split** (chronological):
   - development 2010/11–2019/20 (COVID 2019/20 and 2020/21 flagged);
   - validation 2020/21–2022/23 (the SBRO overlap allows a market benchmark);
   - sealed holdout 2023/24–2025/26, with a hashed spec and one-shot opener.
   - Market benchmarking on the holdout requires a decision on Kaggle lines or paid credits (your call).
5. **Discovery (data-first).** Rank candidate feature families by out-of-sample information gain, without pre-selection:
   - team strength (Elo, goal differential), shots and xG, goalie season form (the *announced* starter is not available historically, so use a team-goalie-pool proxy and record it as a limitation), rest, back-to-backs, travel, home advantage.
6. **Benchmarks.** Base rate (home ~54–55%), an Elo baseline, and the SBRO closing market where available. The sports model is not required to beat the market; the best-calibrated source wins.
7. **Metrics.** Log loss, Brier, calibration slope and intercept, AUC, band tables (≥60/65/70/75/80), and season stability.
8. **Lock → open holdout once → prospective shadow.** Goalie confirmations and UK h2h are snapshotted live from the start.

**Recommended first step now (cheap, no model):** start forward collection of UK `icehockey_nhl` h2h odds once a day (1 credit) to measure UK book coverage and the 2-way vs 3-way split. Alternatively, defer until credits allow (§17).

## 10. NBA existing-model inventory (verified)

**Engine.** `nba_moneyline.market` v1 (frozen), status VALIDATED_HISTORICAL, `activation_date_utc 2026-10-20`, `FIRST_SCAN_WITHIN_36H`, `money_eligible: false`, multi-research eligible.
- Historical estimator: OddsPortal average closing odds with two-way multiplicative de-vig.
- Live estimator: mean odds across ≥3 non-exchange UK books, then de-vig.

**Data.** `wippa-studios/wippa-nba-data` (MIT), 2016/17–2025/26, 12,825 games, with an SBR cross-check (99.8% winner agreement). Splits:

| Role | Seasons | n |
|---|---|---|
| Development | 2016/17–2021/22 | 7,564 |
| Validation | 2022/23–2023/24 | 2,632 |
| Sealed holdout | 2024/25–2025/26 | 2,629 |

The holdout spec hash was verified, and the spec was committed 2.9 s before opening.

**Holdout results (verified exactly).**
- Log loss 0.5809, Brier 0.1990, AUC 0.754, slope 1.046 [0.956, 1.137].
- **P ≥ 0.80: n = 550 (20.9%), mean predicted 85.5%, actual 87.5% (481/550), Wilson [84.4, 90.0].** All 8 bands with n ≥ 200 fall within their 99.5% intervals.
- Challengers (Elo, a 10-feature logit, a stack) did not beat the market.
- Not pre-registered: away favourites ≥80% won 93.3% (n 165) vs home 84.9% (n 385).

**Provenance defects.**
- `NBA_RETURN_CHECKPOINT.md` cites commit hashes `12561fc` and `abc2b87`, which do not exist. The real ones are `a047ab1` → `8083a43` → `1cd2259`; the order of events is still intact.
- The raw data is not on disk, so results cannot be recomputed without re-fetching.

## 11. NBA 20 October readiness gaps — **NEEDS SMALL FIX** (activation already configured)

Collection starts automatically on 2026-10-20 (registry gate tested).

**Before that, fix:**
1. **Stage B is impossible.** NBA writes `live_price_source = "odds_api best book"`, which `prices.from_ledger_row` rejects (no colon), so every NBA candidate is NO_EXECUTABLE_PRICE. Fix: record the actual best book as `odds_api:<book>` (or add an NBA snapshot path) plus a test.
2. **No σ.** Add a per-band Wilson SE from `NBA_PROBABILITY_BANDS.csv` (pre-registered).
3. **Duplicate rows when the favourite flips.** `prediction_id` includes the selection, so a later scan with the other favourite appends a second row. Fix: one row per game (first snapshot canonical), with a test.
4. **No per-book freshness check** (unlike football's 6h). Add a `last_update` age filter, so a stale book cannot enter the consensus.
5. **Snapshot timing is far from the validated close.** The only paid call is at the 06:30 cron, about 17–21h before tip-off. Record minutes-to-tip, and treat the prospective period as the test of the early-snapshot estimator. A later daily scan would cost more credits.
6. **Exhibitions.** Filter non-regular-season events (All-Star etc.); preseason is covered by the date gate.
7. **Settlement window.** Scores are fetched every 3rd day with `daysFrom=3`, so there is no margin for a missed run. Fix: every 2nd day, or add a free fallback source; verify scores include OT.

## 12. Proposed multi-sport common schema

The existing `Prediction` dataclass (`prediction_platform/schema.py`) already holds most of the probability fields. Proposed **additions**, with probability and financial fields kept separate:

| Field | Purpose |
|---|---|
| `probability_basis` | `P_FIRST_SNAPSHOT` (the immutable prediction of record; for calibration and prospective validation) vs `P_CURRENT_SCAN` (latest same-snapshot P; for decisions). Both are always shown and named. |
| `uncertainty_sigma`, `sigma_method` | e.g. band Wilson SE ⊕ book width; `NOT_ESTIMATED` explicit |
| `calibration_status` | e.g. `HOLDOUT_PASSED` / `EXPOSED_ONLY` / `PROSPECTIVE_ONLY` |
| `market_definition` | Settlement scope, e.g. `2WAY_INCL_OT_SO`, `3WAY_REGULATION`, `90MIN` |
| `data_quality_status` | `OK` / reason codes (stale, wide book, unresolved) |
| `event_start_original`, `event_start_current` | est-1, already implemented |

**Downstream only (Stage B record):** bookmaker, offered odds, quote timestamp, quote age, commission, payout, EV, EV at P−σ, risk / exposure group, placeability (min stake), stake, grade, decision, rule version.

## 13. Unified probability-board architecture

```
sport adapters (tennis | football | NBA | NHL)       ← sport-specific data + frozen engines
   → common Prediction record (+ est-1 start resolution)
   → STAGE A board (stage-a-1 generalised): every valid prediction, ranked by P only,
        σ, calibration status, price status {PRICE_VALID, POOR_PAYOUT, PRICE_QUALITY_FAIL, PRICE_UNAVAILABLE}
   → context / data quality flags
   → STAGE B (bsv2-x): same-snapshot price, quality gates, EV, EV@−σ, payout floor, horizon
   → structure engine (singles default; multis research-only)
   → Daily Bet Card → settlement → calibration / performance monitoring per engine and sport
```

Stage A already exists (`stage_a.py`) and is sport-agnostic, except for σ, which is tennis-only today. Generalising it means a per-engine σ provider and a per-sport price adapter; no new board is needed.

## 14. Cross-sport multi research design (design only; multis stay disabled)

1. **Legs.** Each leg must independently be strong (Stage A ≥ the threshold, a validated engine) and have a clean same-snapshot price.
2. **Dependence.** Different sports and different events are treated as independent by default, with an explicit check for shared-information events (same city or team, same tournament). Same-event legs stay prohibited.
3. **Joint P** is the product of the leg P's, with uncertainty propagated by the delta method. For the covariance of the calibration error across legs of the *same engine*, add an engine-level correlated term (an open item from V2-9).
4. **Pricing.** Product-of-leg odds are **INDICATIVE**. Financial evaluation requires an actual same-bookmaker accumulator quote captured at the same time, which needs a capture design and credits.
5. **Comparison.** Equal-capital comparison against the same legs as singles; exposure caps per sport, per event and per day.
6. **Use the existing tooling.** V2-7 (cer-2) logging and the V2-8 analyser structures generalise from tennis-only to multi-sport. Use a new cohort version; do not alter cer-2.
7. **DC legs** (≥80%, odds 1.10–1.25) are natural multi candidates *for research*. They can't be singles under the payout floor, and they lack a historical financial validation.

## 15. Expected volume by expansion stage (predictions, not bets)

Per week during the in-season periods. These are interpretation from cited shares; financially qualified volume is **not estimated**.

| Stage | Events / wk | Prediction rows / wk | ≥0.70 / wk | ≥0.80 / wk |
|---|---|---|---|---|
| A. Tennis only | 0–60 (highly variable; Odds API covers only big events; 94 validated in 23 Sep–2 Oct) | same | about 44% of predictions | about 19% |
| B. + Football (E0/E1/SC0) | +29 | +87 (1X2) +87 (DC) | +3 (1X2), +27 (DC best) | +1 (1X2), +9 (DC best) |
| C. + NBA (from 20 Oct) | +50 | +50 | +22 | +10–11 |
| D. + NHL (if validated) | +49 | +49 | unknown (expected low; OT/SO compresses) | unknown |

**Sources:**
- Tennis: the prospective ledger (41/94 ≥0.70, 18/94 ≥0.80).
- Football: the historical panel shares (§5).
- NBA: the holdout shares (44.0% ≥0.70, 20.9% ≥0.80) × about 50 games a week.

**Takeaways:**
- Stages B and C roughly **triple to quadruple** the strong-prediction universe.
- Most of the added ≥0.80 volume is DC (not single-eligible) and NBA (money_eligible: false until prospective evidence exists).
- For financially qualified bets: the historical football Stage B produced about 1 qualifier per 5 weeks (V2-6H). **No forecast is made.**

## 16. Bankroll implications (config `bankroll_simulation`; no change proposed)

Limits: max stake 5%, max daily exposure 10%, minimum stake £1 on an exchange and £0.10 at a bookmaker.

| Bankroll | Daily exposure cap | Exchange singles/day at £1 min | Bookmaker singles/day at 1% stake | 1/8-Kelly stake at edge 3%, odds 1.5 |
|---|---|---|---|---|
| £20 | £2.00 | 2 | 10 (at £0.20) | 0.75% = £0.15 (below the exchange min; bookmaker only) |
| £30 | £3.00 | 3 | 10 (at £0.30) | £0.23 |
| £50 | £5.00 | 5 | 10 (at £0.50) | £0.38 |
| £100 | £10.00 | 10 (at £1) | 10 (at £1) | £0.75 |

**Implications:**
- Multi-sport volume does not translate into more stake: the 10% daily cap binds first.
- At £20–£50 the exchange minimum (£1) makes exchange singles chunky (2–5% each). Bookmaker singles at fractional stakes are the only fine-grained option.
- Correlated exposure (same tournament or league, multiple legs on one team) needs per-group caps before multis.
- Fractional Kelly with an eighth or less, or flat 1%, is the only defensible staking until probability quality is prospectively validated per sport. No martingale, no chasing, no forced daily stake.

## 17. Implementation dependencies

| # | Item | Depends on | Effort |
|---|---|---|---|
| 1 | bsv2-4 merge | PASS of the post-V2-10 scan run | trivial |
| 2 | **Credit plan** (re-balance caps or upgrade; your decision, no purchase by me) | — | decision |
| 3 | Football fixes (§6.1–6.6) | — | small |
| 4 | NBA fixes (§11.1–11.4, 11.6–11.7) | before 20 Oct | small–medium |
| 5 | Stage A σ providers (football, NBA) | 3, 4 | small |
| 6 | V2-8 analyser → read `latest_stage_a_board` | V2-10 merged ✓ | small |
| 7 | Multi-sport Stage A display (P basis naming) | 5 | small |
| 8 | NHL data audit | Network access to `nhle.com` (runner) | medium |
| 9 | NHL modelling | 8 + pre-registration | large |
| 10 | Cross-sport multi research cohort | 5, 6, actual acca quotes | medium |

## 18. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Odds API credits exhausted:**<br>• tennis cap 120/month vs ~6/day burn → tennis stops around 20 Oct, exactly when NBA starts<br>• total plan 500 | High | Lost scans / coverage | Re-balance caps (e.g. tennis 150, NBA 50), drop low-value calls, or upgrade (your call) |
| Football live estimator ≠ validated | Medium | Calibration drift | Provenance label; prospective test; no claim transfer |
| DC sealed holdout contaminated by prospective monitoring | Medium | Loss of the only untouched DC test | No-peek rule; guarded opener |
| NBA early snapshot vs closing validation | Medium | Miscalibrated early P | Record minutes-to-tip; prospective test |
| NBA duplicate rows / unpriceable | High (as coded) | Broken Stage B, double counting | Fixes §11 |
| GitHub cron delay (4–6h observed) | High | Missed pre-match windows (8 tennis matches on 30 Sep) | Scheduling research (V2-9 action) |
| Settlement alias gaps | High (2 known) | Unsettled rows | Aliases + migration shadow |
| NHL API unofficial / blocked here | Medium | Data pipeline fragility | Cache raw pulls with hashes; run on the runner |
| NHL UK h2h 3-way contamination | Medium | Wrong target | Per-book Draw detection |
| Over-expansion pressure (bets/day as a goal) | Medium | Standards erosion | Locked principle: more validated markets, not looser gates |

## 19. Priority-ranked October roadmap

1. **Now:** verify the first scan run after V2-10 (PENDING), then **merge bsv2-4**.
2. **By 5 Oct:** a credit-budget decision by you, since tennis, football and NBA together already exceed sustainable caps. Re-balance `config/api_budget.json` without buying anything unless you choose to.
3. **By 7 Oct** (before football fixtures enter the 48h window): football small fixes §6.1–6.6. The first prospective football Stage A rows arrive automatically from about 8 Oct.
4. **By 17 Oct:** NBA fixes §11 and the Stage A σ for football and NBA. Collection starts automatically on 20 Oct, shadow and Stage A only (`money_eligible: false`).
5. **Mid-Oct:** point the V2-8 analyser at the complete Stage A board.
6. **Late Oct:** the NHL data audit (pre-registered), run where `nhle.com` is reachable. Optionally start daily UK NHL h2h snapshotting if credits allow.
7. **Ongoing:** keep thresholds frozen; continue V2-7 prospective collection; scan-timing study.
8. **After 4–6 weeks of prospective rows per sport:** per-engine calibration review → consider `money_eligible` changes, each separately approved.

**Shortest evidence-safe routes:**
- **Tennis + Football:** bsv2-4 merge → football fixes §6 → automatic rows from about 8 Oct → 4–6 weeks of prospective calibration.
- **+ NBA:** NBA fixes §11 and σ → automatic shadow collection from 20 Oct.
- **+ NHL:** data audit → pre-registered discovery and modelling → sealed holdout → prospective shadow. Realistically December at the earliest, and only if the evidence supports it.
