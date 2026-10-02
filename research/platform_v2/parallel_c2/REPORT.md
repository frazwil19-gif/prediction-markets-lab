# Parallel probability research while Track A and the price gate run — report (2026-10-02)

Directive: "CONTINUE PROGRESS NOW — PARALLEL PROBABILITY RESEARCH WHILE TRACK A AND PRICE GATE RUN".

| Item | Value |
|---|---|
| Branch | `research-parallel-c2`, from master `4ae203c`; not merged |
| Probe branch | `probe/prop-price-c2`, untouched |
| Scope | Research only. No production, threshold, grade, stake or money change. No prices used in any model. No API calls. No purchases. |

## 1. Branches and SHAs
| Commit | Content |
|---|---|
| `44a6961` | Corners Model A pre-registration, written before any computation |
| `b6dff83` | Discovery and development results; `FROZEN_SPEC.json` committed before the holdout |
| `3ba5cf6` | Sealed holdout, opened once; a second opening is refused by the guard |
| `a3075b8` | Plans for the goals probe and the dependency atlas, written before computation |
| (this commit) | Goals probe, dependency atlas, player-data and price-source audits, registries, tests |

## 2. Track A
Track A is untouched. No commit on this branch touches `src/`, `config/`, `.github/` or any production script. Master `4ae203c` still contains the H1, H2 and H3/H7 code from `cbaaca2`. H2 has made no paid call so far, because no paper selection has fallen inside the 75-minute window. H1 writes rows when the daily scan runs.

## 3. Corners — Model A (sports-only)
Pre-registration: `props_c1/corners/MODEL_A_PREREGISTRATION.md` (`44a6961`).

**Prior exposure, disclosed in advance:**
- The one-run C1 probe and the descriptive Phase 1 audit had already touched the holdout period.
- The holdout is therefore sealed *for this model*, not pristine.

**Raw behaviour (EXPLORATORY; discovery set 2005-07 to 2019-06, n ≈ 31k):**

*Total corners:*
- Total corners are only weakly predictable from team history.
- The best single correlate of the total is the league's recent mean (ρ +0.15). Next come rolling 20-match corners for the home team (+0.11) and corners conceded by the away team (+0.09).
- These are sign-stable in every season and in 7–10 of 10 leagues.

*Team corners:*
- Team-level corners are far more predictable than totals. Rolling 20-match corners for the home team correlate +0.19 with home corners.
- Elo difference correlates +0.24 with home corners and −0.21 with away corners. But it moves corners *between* teams, so it adds almost nothing to the total (+0.05).

*Weak or unstable variables:*
- Shots and goals are weak and unstable for the total; their sign is inconsistent across seasons.
- Rest days and stage of season are about zero.

*Redundancy:* windows 10 and 20, and venue-specific versus pooled rates, overlap heavily (ρ 0.82–0.85).

*Home/away dependence:*
- Home and away corners are negatively correlated within league-season (−0.21).
- The dependence remains after conditioning on the model means: copula ρ is −0.17 to −0.18 in every fold.

**Feature selection** (pre-set forward-stepwise rule on 5 walk-forward folds):
- Only **G3, rolling 20-match corners for and against for both teams**, was added (+0.0042 nats per match, 4 of 5 folds).
- Shots10 missed the pre-set threshold narrowly (+0.00047 against 0.0005 required). By the rule it was not added.

**Count families tested** (mean development log score of the total; lower is better):

| Family | Log score |
|---|---|
| MA1 Poisson | 2.6308 |
| MA2 negative binomial (NB) | 2.6256 |
| MA3 team-split, independent | **2.6328 (worst)** |
| MA4 team-split + Gaussian copula | **2.6250 (selected)** |

**Independence of home and away corners is rejected empirically.** Adding two independent team models gives the worst total distribution.

**Development comparison** (vs the best non-market baseline, B2 = league-mean NB):
- Δprimary is −0.0032 [−0.0043, −0.0020].
- Every fold is negative: −0.0040, −0.0019, −0.0005, −0.0049, −0.0049.
- The pre-set rule to proceed was met.
- Development calibration slopes were 0.83 at the 9.5 line and 0.86 at 10.5.

**Sealed holdout** (2024-07 to 2026-09, n = 7,153; trained on 54,364; opened once):

| Metric | Model A | B2 (league NB) | B0 (league Poisson) | B1 (team rate) |
|---|---|---|---|---|
| Primary (mean log loss over lines 8.5–11.5) | **0.65007** | 0.65390 | 0.65448 | 0.66061 |
| Log score of the total | 2.6164 | 2.6220 | — | — |

- Δ vs B2 is **−0.0038 [−0.0056, −0.0020]**.
- Mean predicted total is 9.92 against 9.85 actual.

**Holdout results by line:**

| Line | Model A log loss | B2 log loss | Calibration slope | Calibration intercept | AUC (A vs B2) |
|---|---|---|---|---|---|
| 7.5 | 0.5634 | 0.5664 | 1.03 | −0.06 | 0.582 vs 0.563 |
| 8.5 | 0.6485 | 0.6519 | 1.03 | −0.04 | 0.582 vs 0.564 |
| 9.5 | 0.6848 | 0.6880 | 0.90 | −0.01 | 0.574 vs 0.556 |
| 10.5 | 0.6670 | 0.6706 | 0.89 | −0.04 | 0.576 vs 0.557 |
| 11.5 | 0.6000 | 0.6051 | 0.92 | −0.09 | 0.582 vs 0.555 |
| 12.5 | 0.5121 | 0.5165 | 0.86 | −0.18 | 0.581 vs 0.552 |
| 13.5 | 0.4104 | 0.4135 | 0.83 | −0.31 | 0.584 vs 0.558 |

**Stability on the holdout:**
- All 10 leagues are negative (−0.0010 in N1 to −0.0065 in SP1).
- 2024-25: −0.0044 [−0.0069, −0.0019]. 2025-26: −0.0040 [−0.0067, −0.0014].
- 2026-27 partial (n = 274) is +0.0058, CI including 0. It is below the 1,000-match threshold, so it is not part of the verdict, but it is reported.

**Team-line calibration (secondary):** slopes are 0.90–1.03 and calibration-in-the-large is within ±0.07.

**Failure modes:**
- The probability range is narrow; deciles at 9.5 run from 0.40 to 0.64. Model A separates matches only modestly (AUC about 0.58).
- At extreme lines (12.5, 13.5) calibration slopes are 0.83–0.86, so predictions are slightly too extreme.
- Effects are small in absolute terms: about 0.6% relative log-loss gain.

**Pre-registered verdict: all 3 criteria pass → PROBABILITY_VALIDATED / PRICE_GATE_PENDING.**
- This is validated against non-market baselines only. It makes **no** claim against bookmaker consensus and no EV claim.
- Prior expectation, for honesty: in O/U 2.5 and BTTS the data models beat naive baselines by far more than this, yet still lost to the market. Model B is the real test.

## 4. Goals / totals
**Inventory:**
- Football-Data/xgabora: goals for all 10 leagues, 2000+.
- 1X2 and O/U 2.5 closing-ish odds in the file (2–3 books historically: class C/B proxy).
- Project files `cycle_001/002` cover E0/E1/SC0 2020–2025 with per-book 1X2 and O/U 2.5.
- Live production consensus for 1X2 and O/U 2.5 (class A, via the Odds API).
- No historical BTTS, team-total or alternate-total prices are held.

**Prior research reused, not re-run:**
- **O/U 2.5** (`research/ou25_discovery/`): the market is best on every split and fundamentals are worse. Production already uses consensus.
- **BTTS** (`research/btts_outcome_prediction/`): the data-only model was REJECTED on its sealed holdout (AUC 0.496). The market-implied Poisson was selected.
- **1X2:** consensus is best (earlier cycles).

**New exploratory probe** (plan `a3075b8`; walk-forward 2019-20 to 2023-24; n = 17,114; no holdout touched):

| Target | Base rate | League baseline | Data-only Poisson | Market-implied Poisson | Data − baseline [CI] | Data − market [CI] |
|---|---|---|---|---|---|---|
| Home > 0.5 | 0.77 | 0.5423 | 0.5150 | **0.5110** | −0.027 [−0.031, −0.024] | +0.0040 [0.0028, 0.0053] |
| Home > 1.5 | 0.44 | 0.6837 | 0.6366 | **0.6299** | −0.047 | +0.0068 [0.0051, 0.0084] |
| Away > 0.5 | 0.70 | 0.6136 | 0.5858 | **0.5804** | −0.028 | +0.0054 |
| Away > 1.5 | 0.35 | 0.6454 | 0.6071 | **0.6005** | −0.038 | +0.0066 |
| Total > 1.5 | 0.76 | 0.5417 | 0.5372 | **0.5340** | −0.0045 | +0.0032 |
| Total > 3.5 | 0.30 | 0.6052 | 0.5966 | **0.5914** | −0.0086 | +0.0053 |

- Data-only models are well calibrated (slopes 0.97–1.06) and beat baselines strongly. **The market-implied estimator beats them on every target, with CIs excluding 0.**
- The pre-set rule (within 0.002 of the market) fails everywhere. **A data-only goals cycle is NOT justified.**

**Goals/totals research map:**

| Target | Classification |
|---|---|
| 1X2, O/U 2.5, BTTS | **ALREADY EXHAUSTED** (market or market-implied best; in production via consensus) |
| Team totals (home/away over 0.5 and 1.5) | DATA-READY; predictable, but the data-only route is **NOT WORTH PURSUING**. The best estimator is market-implied (already priceable from 1X2 + O/U). Team-total prices themselves are unchecked. |
| Alternate totals (1.5, 3.5) | Same as team totals. Likely PRICE-READY through the Odds API `alternate_totals` (unverified, would cost credits). |
| HIGH PRIORITY data-only targets | **None.** A "market-implied team totals" extension of the consensus engine is a possible later priced product, but it is not new predictive research. |

## 5. Player data (Workstream C)
**C1 — repository inventory:**
- Searched the cloud repo and Fraser's local `data/` (raw, interim, processed, external, samples).
- **No football player-level data exists.** Every player/minutes column belongs to tennis datasets (`workstream_b_*`, `v2_wta_*`).
- Football files have team-level fields only, e.g. `home_team_appearance_number` in `cycle_002_discovery_features.csv`.

**C2 — free sources** (desk research, no sign-ups):

| Source | Player events | Leagues (of our 10) | Seasons | Lineups / minutes | Licence / automation | Verdict |
|---|---|---|---|---|---|---|
| API-Football free | Per player per fixture: shots, SOT, goals, assists, cards, fouls, tackles, passes, saves, minutes, position, substitute flag. Events with sub minutes. | All 10 listed (per-league player-stat coverage unverified) | **Free plan: 2022–2024 only** (live error message reported 2026-09-18) | Yes. Lineups about 20–40 minutes before kick-off, but the current season is not free. | API, 100 requests/day. ToS: betting use "may require additional licenses". | Most credible path; slow (about 7–10 months of free quota to backfill 3 seasons) |
| Sportmonks free | Fixtures, events, lineups, player statistics | Scottish Premiership only (plus Denmark) | Unverified | Yes (timing unverified) | API, 3,000 calls/entity/hour | Useful for SC0 only |
| StatsBomb Open Data | Full events, lineups with minutes | Fragmentary seasons; none for E1/SC0/N1/P1/B1 | Not continuous | Yes, post-match | **No commercial exploitation** (cl. 1.2.2) | Definitions research only |
| Understat | Shot outcomes per player, minutes, positions, cards | Big 5 (+RFPL), 2014+ | — | Minutes yes, lineups no | No API or licence found; robots.txt reported to disallow fetchers | Do not automate |
| FBref | Basic history (Opta advanced data removed Jan 2026) | Many | Deep | — | **Bots/scrapers prohibited** | Do not use |
| Wyscout public (Pappalardo 2019) | Events incl. shots on/off target | Big 5 | **2017-18 only** | Derivable | CC BY 4.0 | Definitions and dependency research |
| Transfermarkt datasets (dcaribou) | Minutes, goals, assists, cards, lineups, subs; **no shots/SOT/fouls/saves** | Likely all 10 | Multi-season, to 2026-07 | Yes / yes | Repo CC0; upstream provenance uncertain | Minutes model only |
| football-data.org free | No player data on the free tier | — | — | — | — | No |

**C3 — player market feasibility:**

| Market | Historical outcomes | Lineups / minutes / subs | Sample (10 leagues) | Target reproducibility | Settlement complexity | UK price source | Historical price | Prospective price | Class |
|---|---|---|---|---|---|---|---|---|---|
| Player SOT | API-Football (2022–24 free), Understat (big 5) | API-Football; Transfermarkt minutes | ≈ 95k player-matches per season | MEDIUM (provider definition must be pinned) | Medium (non-runner, sub rules) | **Betfair Exchange player SOT 1+/2+ (EPL Grade-1, 2025+)** | Betfair Historical BASIC (inclusion unverified) | Betfair API (delayed key free) | **DATA SOURCE IDENTIFIED** |
| Player shots | Same | Same | Same | MEDIUM | Medium | None found (Betfair has no player shots) | — | — | PRICE BLOCKED |
| Goalscorer | Broad (Transfermarkt CC0 goals, API-Football) | Same | Large, rare event | HIGH | Medium (late sub, own goals) | Betfair To Score / First Goalscorer | Betfair Historical (unverified) | Betfair API | DATA SOURCE IDENTIFIED |
| Player cards | API-Football, Transfermarkt | Same | Large | MEDIUM | **High** (bench, after sub, 2nd yellow) | Betfair Player Shown a Card (EPL Grade-1) | Unverified | Betfair API | DATA SOURCE IDENTIFIED |
| GK saves | API-Football | Same | 2 per match | MEDIUM-LOW (definitions) | Medium | Betfair GK saves 3+/4+ (top tier, 2025) | Unverified | Betfair API | DATA SOURCE IDENTIFIED |
| Player fouls | API-Football | Same | Large | LOW | High | Betfair fouls **removed 30 Jan 2026** | — | — | LOW PRIORITY / PRICE BLOCKED |
| Tackles, passes | API-Football | Same | Large | LOW | High | None found | — | — | LOW PRIORITY |

None is READY FOR DATA ACQUISITION without a Fraser decision: an account action, and the ToS caveat about betting use.

**C4 — expected-minutes architecture (design only):**

- **Pre-lineup model: P(start) × E[minutes | start].**
  - Needs historical lineups and minutes plus *pre-match availability* (injuries, suspensions, rotation news).
  - Free sources do not provide that availability information point-in-time, so P(start) would rest on recent start share alone.
  - Validation requires per-match lineups, minutes and a reconstruction of what was knowable before kick-off. **That cannot be validated leakage-safely with free data.**
- **Post-lineup model: confirmed starter → E[minutes | starter].**
  - Needs historical lineups, minutes and substitution minutes (API-Football, Transfermarkt).
  - Validation is straightforward and chronological.
  - Operational cost:
    - lineups arrive about 20–60 minutes before kick-off, so the scan and price capture must run in that window;
    - GitHub cron is 2–7 hours late, so it needs a push-triggered or always-on runner;
    - Betfair streaming or polling.
  - Actual minutes are only ever the exposure or outcome, never a feature.
- **Recommendation:** post-lineup first.

**C5 — first player market: Player shots on target (1+ / 2+), conditional.**

*Why:*
- It is the only player market where all three of these exist:
  - a reproducible outcome label (shots on target per player, with provider definitions to pin);
  - a large sample;
  - a two-sided UK-executable price at the Betfair Exchange (back and lay, so fair P is constructible).
- Goalscorer has better pricing but a rarer event and probably a more efficient market.

*Honest status:* **not ready.**
- The data must first be acquired: API-Football free covers 2022–24 only, at 100 requests/day.
- Betfair coverage outside EPL is unverified.

## 6. Price sources (Workstream D), desk research only, NO PURCHASE
**Team SOT:**
- Betfair Exchange "Match Shots" and "Match SOT" markets were **removed 30 Jan 2026**.
- No legitimate historical team-SOT price source was found.
- UK bookmakers offer team SOT for manual betting only; there are no public APIs, and their terms generally prohibit scraping.
- Team SOT stays **PREDICTABLE / PRICE_REQUIRED**. The only route would be manual fair-odds comparison, which cannot be validated systematically.

**Player props:**
- The Betfair Exchange lists player SOT 1+/2+, Player Shown a Card, To Score/First Goalscorer and GK saves 3+/4+ on EPL Grade-1 matches.
- The Odds API remains US-only for soccer player props.
- Commercial feeds claiming UK props have undisclosed or scraping-based provenance (OddsPapi, odds-api.io, UK Odds API, BetsAPI), or are US-focused and priced by contact-sales (OpticOdds, OddsJam).

**Corners and cards on Betfair:** unverified. No public market-type list was found.

**Costs** (as published; not verified by purchase):
- Betfair API: delayed app key free; live key £499 one-off (only for actual API betting; read-only use is not permitted on the live key).
- Betfair Historical Data: BASIC free (1-minute last-traded price, 2015+); Advanced and Pro unpriced publicly.
- Smarkets API: £150. Betdaq API: £250. Matchbook API: usage-based.

**Ranking:**

| Bucket | Sources |
|---|---|
| FREE NOW | Betfair delayed app key (read-only catalogue check of which football market types exist per league: corners, bookings, player SOT, saves); Betfair Historical BASIC (check that these markets are in the files); the approved Odds API probe 2; API-Football free (100 requests/day; history 2022–24 only) |
| CHEAP / HIGH VALUE (later, only if a model validates) | Betfair live key £499 when API betting is wanted; a paid API-Football month for the backfill (price unchecked) |
| EXPENSIVE / POTENTIALLY VALUABLE | OpticOdds or OddsJam enterprise feeds (only with written UK coverage); Betfair Advanced historical |
| NOT WORTH IT | Smarkets, Matchbook and Betdaq API fees for now; OddsPapi, odds-api.io, UK Odds API, BetsAPI and Oddsportal-type sources (provenance/ToS risk); any scraping |

## 7. Dependency (Workstream E)
Bounded set of 8 pairs (plan `a3075b8`); n = 36,252; seasons 2015-16 to 2025-26.

| Pair | P(A) | P(B) | P(A∩B) | P(A)P(B) | Ratio [CI] | P(B given A) / P(B given not A) | Same side of 1 (seasons / leagues) |
|---|---|---|---|---|---|---|---|
| Favourite win × favourite SOT > 4.5 | 0.530 | 0.561 | 0.371 | 0.297 | **1.248** [1.239, 1.257] | 0.70 / 0.40 | 100% / 100% |
| Favourite win × corners > 9.5 | 0.530 | 0.531 | 0.270 | 0.281 | 0.962 [0.952, 0.971] | 0.51 / 0.55 | 91% / 100% |
| Favourite win × cards > 4.5 | 0.530 | 0.399 | 0.192 | 0.212 | 0.905 [0.893, 0.917] | 0.36 / 0.44 | 100% / 100% |
| Goals > 2.5 × SOT > 8.5 | 0.523 | 0.494 | 0.350 | 0.258 | **1.357** [1.346, 1.368] | 0.67 / 0.30 | 100% / 100% |
| Goals > 2.5 × corners > 9.5 | 0.523 | 0.531 | 0.272 | 0.277 | 0.979 [0.970, 0.988] | 0.52 / 0.54 | 91% / 90% |
| Goals > 2.5 × cards > 4.5 | 0.523 | 0.399 | 0.203 | 0.209 | 0.974 [0.961, 0.987] | 0.39 / 0.41 | 91% / 80% |
| SOT > 8.5 × corners > 9.5 | 0.494 | 0.531 | 0.288 | 0.262 | 1.096 [1.086, 1.106] | 0.58 / 0.48 | 100% / 100% |
| SOT > 8.5 × cards > 4.5 | 0.494 | 0.399 | 0.190 | 0.197 | 0.963 [0.949, 0.975] | 0.38 / 0.41 | 91% / 100% |

- Shots on target are strongly positively tied to goals and to the favourite winning.
- Corners and cards are mildly negatively tied to winning and to goals.
- Directions are stable across seasons and leagues.
- Atlas entries: BA-DEP-004 to 011 and BA-CRN-002.

## 8–9. Registries
`props_c1/MARKET_STATUS.csv` and `props_c1/ATLAS_ENTRIES.csv` have been updated.

## 10. Null and negative findings
- The data-only goals models lose to the market-implied estimator on all 6 team and total targets.
- The independent team-split corners model is the worst count family.
- Shots, goals, rest and season stage add nothing material for the total once corners history is in the model (shots10 was just below the threshold).
- The 2026-27 partial season is +0.006 for corners Model A (n = 274; not decisive).
- No free legitimate source provides current-season player data for 9 of 10 leagues.
- No legitimate team-SOT price source exists.

## 11. STOP (evidence-based)
- Data-only goals models (O/U, BTTS, team totals): exhausted.
- Independent team-split corners models.
- Player fouls, tackles and passes.
- Searching for team-SOT prices (frozen).
- Any further Odds API prop probes beyond the approved 10 October probe.

## 12. CONTINUE
- Track A evidence collection.
- 10 October Gate 0 probe.
- Corners Model A → Model B/C comparison if Gate 0 = A.
- Prospective check of Model A on new 2026-27 data.
- Cards: decide whether to pre-register a full cycle with referee (E0/E1/SC0).
- Player SOT data-acquisition planning.
- Dependency atlas as reference.

## 13. Strongest new direction
**The Betfair Exchange as a single free, UK-executable, two-sided price source.**
- A read-only catalogue check with a free delayed key would settle at once whether corners, bookings, player SOT, player cards and GK saves exist, in which leagues, and with what liquidity.
- Those are exactly the price gates that block the corners Model A comparison and the first player market.
- Corners Model A is the first sports-only model in this project to validate on a sealed holdout against non-market baselines. Its market test is next.

## 14. Next smallest evidence-driven step
1. Run the 10 October probe as scheduled.
2. With Fraser's approval: Fraser creates a free Betfair developer *delayed* app key (an account action Claude must not take) and stores it as a GitHub secret.
3. Claude then writes a read-only, zero-cost catalogue enumeration (`listMarketTypes` / `listMarketCatalogue` for the 10 leagues' upcoming fixtures). No betting and no logging beyond a one-off snapshot.

## 15. Decisions for Fraser
1. Approve merging `research-parallel-c2` into master. It is research files, scripts and tests only.
2. Optionally create a free Betfair delayed app key for the read-only catalogue check.
3. Optionally create a free API-Football account (100 requests/day; free history 2022–24 only; ToS caveat on betting use) to start a slow player-data backfill.
4. Whether to pre-register a full cards cycle including referee (England/Scotland only).

Nothing requires purchase.

### Sources (desk research, accessed 2026-10-02)
**API-Football:**
- api-football.com/pricing
- api-football.com/terms
- api-football.com/coverage
- github.com/nimeshjm/fantasy-football/issues/58

**Sportmonks:**
- sportmonks.com/football-api/free-plan/

**Open data and data-use terms:**
- github.com/statsbomb/open-data (LICENSE.pdf)
- sports-reference.com/data_use.html
- sports-reference.com/blog/2026/01/fbref-stathead-data-update/
- nature.com/articles/s41597-019-0247-7
- github.com/dcaribou/transfermarkt-datasets
- football-data.org/coverage

**Betfair:**
- support.developer.betfair.com (API costs; Historical Data)
- betting.betfair.com Exchange newsletters (Mar 2025, Aug 2025, Jan 2026)

**Other exchanges:**
- help.smarkets.com (API T&Cs)
- developers.matchbook.com/docs/pricing
- betdaq.zendesk.com (API access)

**Odds data providers:**
- the-odds-api.com (betting markets; historical)
- oddspapi.io
- odds-api.io
- ukoddsapi.com
- opticodds.com
- oddsjam.com/odds-api
