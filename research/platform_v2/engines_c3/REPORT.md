# Profit-engine directive — status at the next decision point (2026-10-02)

Directive: "NEXT DIRECTIVE — TURN THE RESEARCH PLATFORM INTO PROFIT ENGINES".

## A. Master / code
- **research-parallel-c2 merge:**
  - Master before the merge: `0e79ff6`. Merged as `551757d`.
- **Fix 1, `7cd3258` (test-only):**
  - Problem: today's Daily Bet Card is legitimately empty (international break; the fixtures-first gate skipped every
    odds call). That broke `tests/unit/test_v2_17_first_rows.py`, which read the latest card. It was **failing on
    `0e79ff6` before my merge**, and it would have blocked every production workflow's `pytest` gate.
  - Fix: the test now uses the latest card that has candidates.
- **Fix 2, `a13fb1b` (dependency-only):**
  - Problem: `scipy` was missing from `requirements.txt`. The merged research tests import it, so CI collection
    would fail.
  - Found by: the new collector's first CI run, then confirmed in a clean virtualenv.
- **Current master:** `a13fb1b`. 1311 passed, 8 skipped (clean venv).
- **Production behaviour:** unchanged. No engine, threshold, grade, stake or money logic was touched.
- **This directive's work:** branch `engines-c3`, at `8df3678`.
  - Tests: 1330 passed, 8 skipped, in a clean venv.
  - New files only: one new research workflow, research modules, scripts and docs.
  - **Not merged; needs Fraser's approval.**

## B. Corners
- **Pre-registration:** `research/platform_v2/corners_abc/PREREGISTRATION.md`, `cd98ec8`. Written before any corners
  market evidence existed.
- **Methodology:**
  - **A:** corners-A-1.0, the frozen Model A specification refit once on data before 2026-07-01
    (`corners_A_v1_params.json`).
  - **B:** median, across venues, of proportional two-way de-vigged P(over). Exchange quotes use the back/lay mid
    when the spread is ≤ 10%.
  - **C:** logistic stacking of logit B and logit A. It is fitted on the first 150 eligible events and then frozen.
  - **Primary metric:** log loss at each event's main line, i.e. the two-sided line with B closest to 0.5.
  - **Confirmatory tests:**
    - A vs B;
    - C vs B, which also tests whether A adds information given B (with the fit-block likelihood-ratio test reported).
  - **Uncertainty:** event bootstrap, 2,000 resamples.
  - **Data-quality rules:**
    - quote age ≤ 30 minutes;
    - overround between 0 and 0.15;
    - capture at least 60 minutes before kick-off;
    - unknown commission makes a venue non-executable;
    - no imputation.
  - **Evidence trigger:** 300 evaluation events, with an INTERIM look at 150. Not a calendar date.
- **Collector readiness:**
  - Built and tested; the workflow ran successfully three times on the branch.
  - Zero credits: it uses football-data.co.uk fixtures and results, and the downloads work.
  - It writes Model A predictions (all lines, plus team lines and history flags) and outcomes to
    `research_shadow/corners/`.
  - The consensus, best-executable and decision price columns are separate and still empty
    (`NO_PRICE_SOURCE_ENABLED`).
  - It has produced no predictions yet: during the international break `fixtures.csv` lists only lower divisions.
- **Parity check:** prospective features vs the research features on 1,160 EPL/Championship/Scottish Premiership
  matches from 2025-26.
  - About 93% of team values are identical.
  - Explained differences:
    - lower divisions are not held locally (CI downloads them);
    - the research file lacks some corner values that Football-Data has (e.g. 35 Nott'm Forest matches);
    - some rescheduled match dates differ.
  - **Disclosed:** the frozen research build's league mean includes earlier same-day matches. That is a negligible
    look-ahead in the research features; prospective features are strictly prior.
- **Blockers:** no corners price source yet. The options:
  - **10 Oct Odds API probe:** approved, scheduled for 03:25 UTC.
  - **Betfair:** needs Fraser to run the audit.
  - **Recurring Odds API capture:** would need Fraser's approval. It costs about 1 credit per event per market.
- **Promotion/rejection rule:** taken directly from §10 of the pre-registration.
  - **CASE 1 (A beats B):** go to a financial shadow study.
  - **CASE 2 (C beats B):** the hybrid goes to a financial shadow study.
  - **CASE 3 (neither):** reject sports-only corners as an independent edge source, and do not rescue it.
  - **Ceiling:** whatever the case, the furthest corners can go is prospective shadow. Paper betting needs Fraser's
    explicit approval.

## C. Betfair
- **Readiness:**
  - Script: `scripts/betfair_catalogue_audit.py`. It uses only the Python standard library and can only read.
  - Allowed calls: listCompetitions, listMarketTypes, listEvents, listMarketCatalogue and listMarketBook.
  - Tested with a mocked API: it refuses order methods, classifies market families, builds the coverage matrix, and
    never writes credentials to its outputs.
- **It must run on Fraser's Mac:** Betfair blocks the USA, and GitHub runners are US-based.
- **Manual steps** (in `price_execution/BETFAIR_AUDIT_STEPS.md`):
  1. Fraser logs in to his own Betfair account.
  2. In the Accounts API Visualiser, run createDeveloperAppKeys and copy the **Delayed** key (free).
  3. In the project folder: `export BETFAIR_APP_KEY=…` and `export BETFAIR_USERNAME=…`, then run
     `python3 scripts/betfair_catalogue_audit.py`. The password is typed at the prompt; with two-step
     authentication, type the password followed by the 6-digit code.
  4. Tell Claude when it has run.
- **Secret names (no values):**
  - `BETFAIR_APP_KEY`
  - `BETFAIR_USERNAME`
  - optionally `BETFAIR_PASSWORD` (the prompt is preferred)
  - No GitHub secret is needed.
- **Immediately after:** I commit the 10-league × 8-family coverage matrix (GOOD / PARTIAL / RARE / ABSENT /
  UNRESOLVED) using the real marketTypeCodes. That decides whether Betfair can price corners A/B/C and player SOT.
  Recurring capture would be a separate, approved step.

## D. Player SOT
- **API-Football terms (ToS of 2025-05-21): AMBIGUOUS. STOP before acquisition.**
  - Betting use "may require additional licenses from the relevant rights holders", and responsibility sits with the
    user.
  - There is no clause on storing data or on building derived models.
  - Automated collection is allowed within rate limits, on one account only.
- **Hard constraint:** the repository is public, so raw API data and player-level derived data must not be
  committed. They would stay private on Fraser's Mac.
- **Endpoint granularity (corrected):**
  - `fixtures?league&season` takes 1 request.
  - `fixtures?ids=` takes up to **20 fixtures per request**, with players' statistics included.
  - So one EPL season is **20 requests**.
- **Corrected estimate:**
  - **2 seasons:** 40 requests. **3 seasons** (2022–2024, if the free plan allows): 60 requests.
  - **Calendar time:** about 1 day of the free quota (100 per day).
  - **Sample:** about 16.7k (2 seasons) to 25.1k (3 seasons) confirmed-starter observations.
  - **Storage:** roughly 50–150 MB raw (to be measured).
  - **The previous 7–10-month estimate was wrong.**
- **Should the pilot proceed?** It is practical. Whether it is legitimate is Fraser's decision on the terms.
- **Blockers:**
  - Fraser's decision on the terms;
  - Fraser creating a free account (only he can);
  - Betfair coverage of player SOT outside the EPL is unverified.

## E. Active profit-engine table
Full registry: `research/platform_v2/PROFIT_ENGINE_REGISTRY.csv`.

| Market | Probability | Market comparison | Price | Prospective | Financial | Next action |
|---|---|---|---|---|---|---|
| Football 1X2 (consensus) | Consensus calibrated; power-de-vig H1 shadow | Consensus is the estimator | Odds API, executable | H1/H2 live (no rows yet: international break) | No settled football paper bets yet | Evidence triggers (300 matches / 30 captures) |
| Football O/U 2.5 | Market best | Exhausted | Executable | Live consensus | — | None |
| Tennis ATP/WTA | Holdout passed (exchange mid) | Market-derived | Executable | Paper since 2026-09-23 | 10 paper bets (1 under the current rule, unsettled) | Accumulate settled paper |
| **Corners (Model A)** | **PROBABILITY_VALIDATED** (sealed holdout vs non-market baselines) | Pre-registered, not started | **None yet** | Collector built (zero credits) | — | Gate 0 on 10 Oct + Betfair audit, then a price source |
| Team corners | Holdout slopes 0.90–1.03 (secondary) | Not started | None | Logged by the collector | — | Own verdict later |
| Player SOT | Not built | — | Betfair (EPL, unverified elsewhere) | — | — | Terms decision + account, then 1-day pilot |
| Team SOT | Predictable | Impossible | None legitimate | — | — | Frozen |
| Cards | Referee effect not established | — | Unknown | — | — | Queued |
| Goals team totals | Market-implied best | Exhausted for data-only | Not checked | — | — | Frozen |
| SGM / joint | Dependency atlas only | — | Needs real same-game builder prices | — | — | After individual engines validate |

## F. Project decision
1. **Closest to monetising:**
   - Tennis match winner is closest operationally: it is priced, executable and paper-running, but its edge is
     unproven.
   - Corners is the best *new independent* candidate, but it has zero market evidence.
2. **Missing evidence:**
   - Corners: any two-sided executable price, then A vs B on 300 events.
   - Tennis and football: settled prospective paper outcomes and pre-close value.
   - Player SOT: data, plus Betfair coverage.
3. **Next:**
   - 10 Oct probe;
   - Betfair coverage audit (needs Fraser);
   - merge `engines-c3` so the corners collector runs daily (needs approval);
   - the Track A evidence triggers.
4. **Stop:** the directive's stop list, plus these, on evidence:
   - data-only goals models;
   - independent team-split corners models;
   - team-SOT price searching.
5. **Fraser, right now:**
   - (a) Approve merging `engines-c3`.
   - (b) Run the Betfair audit (about 10 minutes: steps in C).
   - (c) Decide on the API-Football terms, and if yes, create the free account.

   Nothing needs buying.
