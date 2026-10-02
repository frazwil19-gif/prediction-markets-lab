# Parallel Prospective Validation (Track A) + Football Prop Market Discovery (Track B) — Report

Date 2026-10-02. Directive: "PARALLEL PROSPECTIVE VALIDATION + FOOTBALL PROP MARKET DATA DISCOVERY".
Tracks are kept separate. Track A is on branch `track-a-h1-h2-shadow` (commit `15f50be`). Tracks B, C, D, F and G
are on branch `research-props-c1`. Nothing has been merged. No real money, no prop paper betting, no SGMs, no
production prop model, no paid data and no production rule changes.

Pre-registration for the bounded probe: `PREREGISTRATION.md`. It was written before any computation.
Scripts are `scripts/props_c1_probe.py` and `scripts/props_c1_dependency.py`.
Outputs are `PROBE_RESULTS.json`, `PROBE_TABLE.csv` and `DEPENDENCY.json`.

---

## Track A

### 1. Implementation/audit status
| Item | Status |
|---|---|
| H1 power de-vig shadow | Built and tested. It runs inside the daily scan once merged. Output: `research_shadow/h1_devig/<date>.csv` (append-only, try/except, never read by production). |
| H2 PRE_CLOSE_VALUE | Built and tested. New hourly workflow `pre_close_capture.yml` with its own concurrency group, so it cannot displace a queued production run. Output: `paper_betting_v2/pre_close_value.csv`. |
| H3/H7 panel | Zero-credit script `scripts/live_price_panel.py`. First output: `research/platform_v2/track_a/H3_PANEL{.csv,_SUMMARY.json}`. |
| Tests | 12 new tests. Full suite: 1301 passed, 8 skipped. |
| Production impact | No production change beyond two additions: the scan appends one research file, and the daily-scan commit list gains `research_shadow`. `tier_floor()` was factored out of `tier_floors()` with identical behaviour; its 15 tests pass. |
| Merge | **Needs approval.** The branch touches a production workflow and the scan script. |

### 2. H1 pre-registration (`research/platform_v2/track_a/H1_PREREGISTRATION.md`)
- **Compared quantities:** p_frozen is the production median of per-book proportional fair probabilities. p_power is the median of per-book power de-vig probabilities, where pᵢ = (1/oᵢ)^k and k solves Σ = 1. Normalised versions of both are also reported.
- **Unit and sample:** the first snapshot per match within 48h of kick-off; settled 1X2.
- **Primary metric:** the paired 3-way log-loss difference with a match-cluster bootstrap. The hypothesis is supported only if the CI upper bound is below 0.
- **Secondary metrics:** Brier, calibration, P bands, high-P (≥0.70), league and temporal stability, N, ESS and CIs.
- **Review trigger:** at least 300 settled matches or the protocol INTERIM, whichever comes first. The trigger is evidence-based, not a calendar date.
- Promotion requires separate approval.

### 3. H1 shadow design
- **Where it runs:** inside `run_daily_scan.py`, for every `1x2` market. It copies the production consensus and recomputes power de-vig from the same complete H/D/A books that production uses. It also stores each book's odds as JSON. This is the first time raw football per-book odds are persisted, and that data also feeds H3/H7.
- **Isolation:** zero extra credits. Failures are swallowed with a warning. Manual runs are not written.

### 4. H2 design and exact incremental credit cost
- **PRE_CLOSE_VALUE** = p_ref·(o−1)(1−c) − (1−p_ref).
- **PRE_CLOSE_PRICE_RATIO** = o / best UK price − 1.
- **Reference price:** the Betfair exchange back/lay mid (de-vigged) when available, otherwise the median UK fair price. Exchanges are excluded from the UK set.
- **Labels:** each capture is labelled `NEAR_CLOSE` (≤10 minutes before start) or `PRE_CLOSE`. **It is never called CLV.**
- Decision-time fields are copied, never modified. Nothing is measured after the start time.
- **Exact cost:**
  - An hourly run with no paper selection starting in the next 75 minutes makes no API call and costs 0 credits.
  - Otherwise it makes one free `/events` call (for the credit headers), then one `/odds` h2h uk call per sport key. That `/odds` call costs 1 credit and covers every due selection for that key.
  - **Hard cap: 25 credits/month** (consumer `pre_close_capture`, logged in the credit ledger). That is 5% of the 500 plan.
  - The job also skips whenever remaining credits are below the Tier-2 shadow floor, so Tier 1 football, tennis, NBA and settlement are protected first.
  - Expected spend at current paper volume (about 10 selections across 4 days, clustered by event time) is 10–25 credits/month. **This is within budget, so no STOP was needed.**
- **Known limitation:** GitHub cron runs late, sometimes by hours. Some selections will therefore be missed or captured early. `minutes_before_start` is recorded on every row so this can be accounted for.

### 5. H3/H7 live dispersion status
- **Status:** first zero-credit panel built from 48 evaluated tennis candidates. Football panels will come from the H1 per-book file once it accumulates (currently 0 rows).
- **Descriptive results:**
  - median books per quote: 19;
  - median best/worst dispersion: 6.1%;
  - median exchange back/lay spread: 1.4%;
  - the best price net of commission is at the exchange in 35% of cases;
  - the price recorded in the decision ledger is the best gross price in 56% of cases.
- **Finding (no rule change):** in 15 rows the ledger recorded the exchange price while a sportsbook offered a better net price. All 15 are REJECTs with `EXCHANGE_SPREAD_TOO_WIDE`. In that case bsv2 has no usable candidate and records a fallback quote. **So prices on REJECT rows in the decision shadow are not best-available prices.** Execution-quality analysis must use the panel, not the ledger price.
- **Evaluation trigger:** evidence conditions (≥100 PAPER_BET panels, or football H1 ≥300 matches), not calendar time.

---

## Track B — football prop market discovery

### 6. Market universe (B1)
**Player markets:**
- shots
- shots on target (SOT)
- anytime / first / last goalscorer
- assists
- to be carded (and booking points)
- fouls committed
- fouls won
- tackles
- passes
- goalkeeper saves

**Team and match markets:**
- team shots
- team SOT
- team cards / booking points
- team fouls
- team corners
- match total corners
- corners handicap
- corners 1X2
- match total cards
- cards handicap
- team goals / team totals
- BTTS (also first half)
- double chance
- draw no bet
- correct score
- HT/FT

The Odds API soccer list confirms these keys:
- `alternate_totals_corners`, `alternate_team_totals_corners`, `alternate_spreads_corners`, `corners_1x2`
- `alternate_totals_cards`, `alternate_spreads_cards`
- `btts`, `btts_h1`, `draw_no_bet`, `double_chance`, `correct_score`, `halftime_fulltime`
- player props: goalscorer, cards, shots on target, shots, assists

The API's own note on player props: "Coverage is currently limited to US bookmakers" (EPL, Ligue 1, Bundesliga, Serie A, La Liga, MLS). It lists no team-SOT, fouls, tackles, passes or saves market.

### 7. Existing-data inventory (held now)
| Source | Content | Coverage |
|---|---|---|
| xgabora `Matches.csv` (Football-Data derived) | Team shots, SOT, fouls, corners, yellow and red cards; goals; Elo; form; 1X2, O/U 2.5 and AH odds | 238,858 matches, 2000-07 to 2026-09. About 51% of rows carry stats. The 10 project leagues have full stats from roughly the 2000s onward. |
| Project cycle_001 / h_fb2 processed | 1X2 per-book markets, opening and closing | Tier-1/2 leagues |
| `cycle_002_bookmaker_markets_ou25` | O/U 2.5 per-book prices | Tier-1/2 leagues |
| Player-level data | **None held** | — |
| Prop prices | **None held** (historical or live) | — |
| Referee | Not in xgabora. Football-Data's raw English CSVs carry a `Referee` column (to verify per division). | E0 and likely E1–E3 |

### 8. Free external-data options
| Source | Data | Notes |
|---|---|---|
| Football-Data.co.uk (raw CSVs) | Team stats as above plus referee (England) | Already the upstream source. Free. |
| Understat | Shot-level events per player (result: Goal, SavedShot, BlockedShot, MissedShot, ShotOnPost), xG, minutes, position | Covers EPL, La Liga, Bundesliga, Serie A, Ligue 1 and RFPL from 2014-15. There is no official API: data is embedded JSON in the pages and the licence is unclear. **Use only after a ToS review.** |
| StatsBomb Open Data | Full event data, lineups and minutes | Covers selected competitions and seasons only, not continuous league seasons. Free with attribution. Good for definition and dependency research, too thin for a production model. |
| FBref | Basic box-score history | Advanced (Opta) data was removed in Jan 2026. The Sports-Reference terms restrict scraping, so **do not scrape**. |
| API-Football (free tier) | Fixtures, lineups, per-player match stats (shots, SOT, fouls, cards, tackles, passes, saves, minutes) | 100 requests/day. Season access on the free tier is restricted, so check before relying on it. Sign-up only; no purchase. |
| The Odds API (current plan) | Live prices for corners and cards markets via the event endpoint; player props only at US books | Costs credits; see item 16. |

### 9. Paid-data options (not purchased)
- **The Odds API paid tier:** historical additional markets and props from 2023-05-03 at 5-minute intervals, 10 credits per region per market per event snapshot.
- **Opta / Stats Perform, Sportradar:** licensed event and player data. Enterprise pricing.
- **API-Football paid tiers:** full seasons and higher rate limits.
- **SportMonks:** player stats and lineups.
- **Betfair historical data:** exchange markets; check which prop markets exist.
- **OddsPortal-type aggregators:** **not acceptable.** They are ToS-restricted.

### 10. Target reproducibility (B3)
| Market | Quality | Reason |
|---|---|---|
| Team goals / team totals / BTTS | HIGH | Goals are unambiguous (regulation time). |
| Match/team corners | HIGH | Corners are counted the same way by data providers and books (taken corners, regulation time). The remaining risk is a "corner awarded but not taken" edge case. |
| Match/team cards (count) | MEDIUM | Books differ on whether a second yellow counts as yellow + red or as 1 card, on cards to non-players or managers, and on post-whistle cards. Booking-points markets (10/25) are a different target. Football-Data counts a second yellow as a red. |
| Team SOT | MEDIUM-HIGH | Opta-style definition (woodwork and blocked shots excluded) is broadly matched, but the provider must be pinned. |
| Player SOT / shots | MEDIUM | Same definitional issue, plus non-runner rules. Blocked shots count as shots but not SOT. |
| Anytime goalscorer | HIGH for the label, MEDIUM for settlement | Own goals are excluded. Non-starter or substitute rules vary. |
| Player cards | MEDIUM | Cards after substitution, bench cards, second-yellow handling. |
| GK saves | MEDIUM-LOW | Provider definitions of a save vary (e.g. whether blocks count). |
| Player fouls, tackles, passes | LOW | Opta-only definitions. No free consistent label since FBref lost Opta. Tackle definitions vary (won vs attempted). |

### 11. Historical sample sizes (B4)
- **Team level, held data:**
  - the 10 project leagues give about 3,450 matches/season;
  - the probe used 45.6k training and 13.9k test matches with complete stats;
  - each match gives 2 team observations.
- **Player level:** about 28 player-match observations per match, so roughly 95–100k per season across the 10 leagues. Understat's 5 leagues give about 1,826 matches/season, about 50k player-match observations.

### 12. Expected prospective candidate volume
- **In season:** the 10 leagues play about 60–80 matches/week. Each match carries roughly 2–4 lines per team market and 20–30 player lines per player market.
- **Team corners and cards:** about 120–160 match-level lines/week (around 20/day, concentrated at weekends).
- **Player SOT:** more than 1,500 lines/week, but only at US books via the API.

### 13. Predictor availability and probe result (B5, pre-registered, one run)
- **Setup:** train before 2022-07-01, test from then to 2026-09. Poisson GLM via IRLS, rolling prior-10-match features. Compared against a league rolling-mean Poisson baseline (M0).
- **Models:** M1 uses sports data only. M2 adds 1X2 and O/U implied probabilities, with uncertain timing, so it is an upper bound.

| Target, line | Base rate | M1 Δlogloss vs M0 [95% CI] | M2 Δlogloss | Calibration gap M1 | Overdispersion |
|---|---|---|---|---|---|
| Total corners > 9.5 | 0.53 | −0.0024 [−0.0039, −0.0010] | −0.0034 | 0.044 (NB 0.032) | 1.17 |
| Total corners > 10.5 | 0.41 | −0.0032 [−0.0046, −0.0018] | −0.0046 | 0.026 | 1.17 |
| Total cards > 3.5 | 0.59 | −0.0049 [−0.0070, −0.0028] | −0.0097 | 0.055 | 1.08 |
| Total cards > 4.5 | 0.41 | −0.0048 [−0.0070, −0.0024] | −0.0085 | 0.053 | 1.08 |
| Home SOT > 4.5 | 0.52 | −0.0578 [−0.0631, −0.0525] | −0.0648 | 0.037 | 1.17 |
| Away SOT > 4.5 | 0.36 | −0.0499 [−0.0553, −0.0448] | −0.0540 | 0.017 | 1.18 |

- **What the gains mean:**
  - All targets pass the pre-set "predictable beyond baseline" rule.
  - **But the gains for corners and cards are tiny:** 0.3–0.5% of log loss, with correlation(μ, y) of 0.15 for corners.
  - Team SOT is strongly predictable from team strength, which the market also knows.
  - **This measures predictability, not value.** No prop prices are held, so no EV claim is possible.
- **What the data lacks:**
  - The cards signal is missing **referee** (the largest known driver).
  - Corners and SOT lack lineup and possession expectations.
- **Overdispersion:** 1.08–1.18. The negative binomial (NB) improves calibration for corners and SOT.

### 14. Expected minutes / lineups (B6)
- **Team markets** need no minutes model.
- **Player markets** need starting XI, substitution history, a pre-match expected-minutes proxy and confirmed lineups.
  - Confirmed XIs are published about 60–75 minutes before kick-off.
  - A pre-lineup model needs P(start) × E[minutes | start] built from history. A post-lineup model is cleaner but leaves a narrow window and needs late price capture (credits, and the delayed-cron issue already seen).
  - Actual minutes may be used only as exposure or outcome.
- **Feasibility:**
  - With Understat or API-Football, lineup and minute history can be reconstructed.
  - Live confirmed lineups would need an API call at about T−60 minutes.
  - **Not solvable with held data.**

### 15. Historical price availability (B7)
| Market | Class | Notes |
|---|---|---|
| Team goals / O/U 2.5 | C | Held (Football-Data, closing-ish). Team totals not held. |
| Corners / cards totals | D now; A later | None held. Historical data only through the paid Odds API (10 credits per region per market per snapshot). |
| Team SOT | D | No API market found. |
| Player props | D | Historical data paid only, and US books only. |

### 16. Prospective price availability and API cost
- **Endpoint:** additional markets need the event-odds endpoint. It is charged per market returned, per region: corners totals plus cards totals is about 2 credits per event per region.
- **Cost at volume:**
  - 60 matches/week costs about 120 credits/week, about 500/month. **That is the entire plan, so it is unaffordable on the current plan.**
  - A minimal EPL-only sample (about 10 matches/week, 2 markets) costs about 85 credits/month. **That still materially exceeds spare budget.**
- **Unknowns:**
  - Which UK books quote corners and cards through the API is **unverified**. Verifying it needs one ≤2-credit call.
  - Exchange availability for these markets via the API is unverified (Betfair lists corners and bookings markets on major leagues).
- **Player props:** UK books are unavailable through the API; US books are not executable for Fraser.

### 17. Market margins (B8)
- **No prop margin data is held**, so nothing has been measured.
- **Prior expectation (to verify, not assumed):** corners and cards totals likely carry more margin than 1X2. Player props likely carry 2–3× the 1X2 margin, often priced one-sided (Over only), which prevents fair-price reconstruction.
- **How to measure:** the ≤2-credit probe would show both-sides availability and overround for corners and cards.

### 18. Settlement rules (B9)
| Situation | Rule and implication |
|---|---|
| Player does not start or does not play | Usually void for shots and SOT. Varies for goalscorer (void vs lose for a late substitute). |
| Player starts then leaves early | Bet stands. Exposure risk sits entirely with us. |
| Player comes on as substitute | Bet stands for SOT and shots at most books. |
| Match abandoned | Void unless the outcome is already determined; corner and card thresholds already reached may stand. Rules vary by book. |
| Extra time | Excluded (90 minutes plus stoppage). |
| Cards after substitution | Bench cards often excluded for players. Team-card markets vary. |
| Booking points | 10 per yellow, 25 per red, often capped at 35 per player. A second yellow handled differently. |
| Stat corrections | Most books settle on the official or Opta feed at settlement time and ignore later corrections. |

**Conclusion:** rules differ enough that venue-specific settlement handling would be mandatory before any deployment.

### 19. Leakage risks
- xgabora `C_*` columns are possibly post-match and were excluded.
- Football-Data odds columns have no decision timestamp, so they are an upper bound only (M2).
- Same-day rolling features: only strictly prior matches are used (shift(1)).
- Actual minutes or lineups must never be used as pre-match inputs.
- Referee appointment is public before kick-off (usually days ahead), so it is legitimate.
- Historical post-match result may characterise dependency (item 24), never predict.

### 20. Feasibility scorecard (research feasibility, not profit; 1 = poor, 3 = good)
Columns:
- Data = historical data
- Label = target reproducibility
- N = sample size
- Feat = pre-match features
- Mins = expected-minutes solvability
- HPx = historical prices
- PPx = prospective prices
- Mgn = margin observability
- Vol = opportunity volume
- Settl = settlement consistency
- Trac = modelling tractability
- Leak = leakage safety
- Cost = data cost

| Market | Data | Label | N | Feat | Mins | HPx | PPx | Mgn | Vol | Settl | Trac | Leak | Cost | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Team goals / team totals | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 2 | 3 | 3 | 3 | 3 | 3 | **36** |
| Match/team corners | 3 | 3 | 3 | 2 | 3 | 1 | 2 | 2 | 3 | 3 | 3 | 3 | 2 | **33** |
| Match/team cards | 3 | 2 | 3 | 2 (needs referee) | 3 | 1 | 2 | 2 | 3 | 2 | 3 | 3 | 2 | **31** |
| Team SOT / shots | 3 | 2 | 3 | 2 | 3 | 1 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | **29** |
| Player SOT / shots | 1 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 3 | 2 | 2 | 2 | 2 | **22** |
| Anytime goalscorer | 1 | 3 | 2 | 2 | 1 | 1 | 1 | 1 | 3 | 2 | 2 | 2 | 2 | **23** |
| Player cards | 1 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 3 | 1 | 2 | 2 | 2 | **21** |
| GK saves | 2 (team proxy) | 1 | 2 | 2 | 2 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | **22** |
| Player fouls / tackles / passes | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 2 | 1 | **16** |

### 21. Tier classification
- **TIER 1:** team goals / team totals (and BTTS), match/team corners, match/team cards.
- **TIER 2:**
  - team SOT/shots: well predicted, but no price source;
  - player SOT/shots and anytime goalscorer: need Understat or API-Football plus a lineup model, and UK prices are unavailable via the API;
  - player cards, GK saves.
- **TIER 3:** player fouls committed/won, tackles, passes. No reproducible free label, no API price.

### 22. Recommended first markets (at most three)
1. **Match total corners (with team corners)**
   - highest label reproducibility;
   - 20+ seasons held;
   - signal is small but real;
   - the market exists in the Odds API soccer list.
2. **Match total cards**
   - only if a referee feature is added (Football-Data England first);
   - settlement variants must be pinned per book.
3. **Team goals / team totals**
   - cheapest to run because it reuses goal data and the existing O/U work;
   - acts as a control family for the Model A/B/C framework.

**Player markets are not recommended for cycle 1.**

### 23. Data-first design for #1 (corners), to be pre-registered before any fit
- **Data and labels:**
  - Rebuild from Football-Data raw for the 10 leagues.
  - Labels: total corners and team corners (regulation time).
- **Feature discovery:** let the data rank candidates (mutual information / permutation importance on train only). Candidates:
  - team and opponent rolling for/against corners;
  - shots for/against;
  - Elo;
  - home/away;
  - league and season level;
  - rest days;
  - referee (England);
  - (Model C only) 1X2 and O/U-implied state.
- **Models:** Poisson and NB GLMs, plus a bivariate or team-split model, compared on log loss, Brier and calibration at lines 8.5–11.5.
- **Validation:**
  - chronological walk-forward by season;
  - a sealed final season;
  - match-cluster bootstrap.
- **Prospective step:** Model A frozen first. Then price capture (Model B = market fair probability from both sides; Model C = hybrid). Probability quality decides; the independent model is not preferred automatically.
- **Exit condition:** if Model A ≥ Model B cannot be tested for lack of prices, the cycle ends as "predictable, unpriceable" and that is recorded.

---

## Track C — independent prop architecture
The probe already follows this ordering: sports data → P (M1), with no price needed. M2 is the leakage-flagged upper bound.

| Model | Definition | Status |
|---|---|---|
| A | Sports-only | M1 now |
| B | Market consensus | Needs prices |
| C | Hybrid | Needs prices |

The comparison is impossible until two-sided prop prices are captured (item 16). The H1-style shadow pattern (persist P_A at decision time, add P_B later) is reusable.

---

## Track D — winner + prop dependency

### 24. Feasibility (bounded, descriptive, held data, no prices)
- **Data:** 14,131 matches, 10 leagues, 2022-07 onward.
- **Definitions:** "Favourite" = the higher implied 1X2 probability. P(favourite wins) = 0.533.

| Prop event | P | P given favourite wins | P given not | Joint | If independent | Joint / independent |
|---|---|---|---|---|---|---|
| Total corners > 9.5 | 0.524 | 0.501 | 0.549 | 0.267 | 0.279 | **0.96** |
| Total cards > 4.5 | 0.403 | 0.368 | 0.444 | 0.196 | 0.215 | **0.91** |
| Favourite SOT > 4.5 | 0.566 | 0.695 | 0.419 | 0.371 | 0.302 | **1.23** |

Multiplying marginals would understate "favourite wins + favourite SOT over" by about 23%. It would overstate "favourite wins + cards over" by about 9%. **This confirms D1 empirically: dependent probabilities must never be multiplied.** Team-level joint modelling is feasible with held data. Player-level joint modelling needs player data.

### 25. Same-game joint-probability research requirements
- **Data:** joint outcome labels from the same source; pre-match features for both legs.
- **Model:** a joint model, e.g. a bivariate or copula, or a direct model of the joint event, calibrated on the joint event itself.
- **Inputs:** individually validated legs first.
- **Validation:** chronological, at the joint level.
- **Rule:** no post-match state as a predictor.

### 26. Same-game pricing requirements
- Actual SGM builder prices from the same book at the same timestamp, logged with the leg definitions.
- None is available through the Odds API; this needs a book-specific source.
- Multiplying displayed odds is never an executable price.
- Without this, probability research may proceed, but **no financial claim**.

---

## Track F / data gaps

### 27. Data gaps and acquisition list (nothing purchased)
| Source | Data | Leagues / seasons | Player events | Timestamps | Prices | Licence / access | Cost | Free alternative | Information value |
|---|---|---|---|---|---|---|---|---|---|
| Football-Data raw CSVs | Team stats, referee (England) | 20+ seasons | No | Date only | 1X2, O/U, AH (closing-ish) | Free, attribution | 0 | — | **High** (referee for cards) |
| Odds API ≤2-credit probe | Corners and cards books, both sides, margin | 1 event | — | Yes | Live | Current plan | ≤2 credits | — | **High** (decides #1 feasibility) |
| API-Football free tier | Lineups, player stats, minutes | Many / limited seasons | Yes | Kick-off | No | ToS ok, 100 requests/day | 0 | — | Medium-high (player track) |
| Understat | Shots and xG per player | Big 5 + RFPL, 2014– | Shots only | Kick-off | No | Unclear; ToS review needed | 0 | API-Football | Medium |
| StatsBomb Open | Events, lineups | Selected | Yes | Yes | No | Free, attribution | 0 | — | Low-medium (definitions) |
| Odds API historical (paid) | Prop and corner/card price history | Major leagues, 2023– | — | 5 minutes | Yes | Paid plan | Paid | Prospective capture | High, **needs approval** |
| Betfair historical | Exchange prop markets | Major leagues | — | Yes | Exchange | Account and terms | Free basic / paid | — | Medium |

**Main gaps:**
- prop prices of any kind;
- referee for non-English leagues;
- player-level data and lineups;
- book-specific settlement rules.

---

## Track G — Claude's assessment

### 28. Independent recommendation (the 15 questions)
1. **Is a prop family justified?** Yes, as research at team level. Not yet at player level.
2. **Most suitable markets:** count markets with clean labels: corners, team goals, cards.
3. **Strongest data:** team corners, cards, SOT and goals (held, 20+ seasons).
4. **Enough observations:** all team markets (about 3,450 matches/season). Player markets once player data exists.
5. **Modellable without prices:** all team markets (probe M1).
6. **Realistic prices:** corners and cards prospectively via the Odds API (cost-limited). Player props none for UK. Team SOT none.
7. **Acceptable definitions:** corners, goals and SOT (with the provider pinned).
8. **Problematic settlement:** cards (second yellow, booking points), all player props (non-runner/substitute), saves.
9. **Impossible now:** fouls, tackles, passes, saves at player level, and anything needing UK player-prop prices.
10. **What is being overlooked:**
    - Predictability is not value. Team SOT is very predictable because it tracks team strength, which the market already prices.
    - Prop margins and one-sided pricing may erase small edges.
    - The binding constraint is **prices and credits, not models**: 500 credits/month cannot sustain prop price capture next to Tier-1 football.
    - Referee data is the main free lever for cards.
    - Odds API player props are US-book only, so they are not executable here.
11. **One market first:** match total corners.
12. **Second and third:** total cards (with referee), then team goals / team totals.
13. **Is winner+prop joint modelling feasible?** At team level, yes with held data (item 24). At player level, only after player data and validated marginals.
14. **Data required:**
    - joint labels;
    - player minutes and lineups;
    - same-book, same-time SGM prices.
15. **Should SGM research wait?** Yes. Same-game combination research should wait until individual prop models validate. The descriptive dependency map can continue now at zero cost.

### 29. Exact next smallest evidence-driven step
1. **Fraser approval needed:** one Odds API event-odds call for a single upcoming EPL match with `alternate_totals_corners,alternate_totals_cards`, region uk. **Cost ≤2 credits**, logged to the credit ledger. It will show which UK books quote these markets, whether both sides are quoted, the overround, and whether Betfair appears. That one result decides whether corners has a prospective price source at all.
2. **Zero cost, in parallel:** pre-register the corners data-first study (item 23) and add Football-Data referee columns for the English divisions.
3. Do not spend further credits on props until (1) is reviewed.
