# Major Next Phase — Automated Daily Bet-Selection Platform: Implementation Checkpoint

**Date:** 2026-09-19
**Responds to:** operator's ("chat gpt:") "MAJOR NEXT PHASE — TURN THE EXISTING PREDICTION MARKETS LAB INTO AN AUTOMATED DAILY BET-SELECTION PLATFORM" instruction, and Fraser's own added framing ("do not redo the existing GitHub/repo infrastructure... audit what exists, preserve it, make the smallest clean migration").
**This is the 18-point return checkpoint the instruction specified.**

## 1. KEEP / MODIFY / ADD / DEPRECATE map (repo + CI audit, Phases 1 and 4)

| Item | Verdict | Notes |
|---|---|---|
| `probability/consensus.py`, `margin_removal.py`, `market_pipeline.py` | **KEEP**, unchanged | Gate 1's winning architecture; V1's probability source. |
| `decisions/grading.py`, `ev/expected_value.py`, `risk/staking.py` | **KEEP**, unchanged | Already built and tested in the prior "GO" instruction. |
| `decisions/confidence.py`, `data_quality.py`, `liquidity.py`, `recommendation.py` | **KEEP**, unchanged this session | Built in the prior instruction; not touched. |
| `storage/schemas.py` (`Exchange` type) | **KEEP**, unchanged this session | Already generalised to `str` in the prior instruction. |
| `ingestion/manual_odds_loader.py` | **KEEP**, unchanged | Stays the fallback/testing/emergency-override path, per the operator's instruction. |
| `ingestion/exchange_price_loader.py` | **MODIFY** (done) | Added `best_price_from_canonical_odds` — the live-panel equivalent of `best_price_for_selection`. Existing functions untouched. |
| `ingestion/the_odds_api_loader.py` | **ADD** (done) | New live-odds adapter for The Odds API v4 (h2h + totals only). See §2/§9. |
| `reports/daily_bet_card.py` | **MODIFY** (done) | Added the frozen JSON/CSV/MD contract (`build_daily_bet_card_contract`, `write_daily_bet_card_outputs`) alongside the existing text renderer. |
| `scripts/run_daily_scan.py` | **MODIFY** (done) | Added `--source {manual,odds-api}`; manual behaviour unchanged; now also writes `daily_cards/<date>/`. |
| `.github/workflows/cycle_001_data_acquisition.yml`, `cycle_002_tennis_data_acquisition.yml` | **KEEP**, unchanged | Correct pattern for bounded, manual, one-shot research jobs; not CI/CD, not touched. |
| `.github/workflows/data_validation.yml`, `weekly_report.yml` | **KEEP**, unchanged | Still correctly disabled placeholders behind their own Stage 2/5 dependencies. |
| `.github/workflows/tests.yml` | **MODIFY** (done) | Was triggered on `branches: [main]`; repo's actual default branch is `master` (confirmed via `git symbolic-ref refs/remotes/origin/HEAD`) — this CI workflow almost certainly never ran. Fixed to `master`. |
| `.github/workflows/daily_scan.yml` | **ADD** (done) | New scheduled workflow — see §11. |
| Asian Handicap exact-line matching | **NOT STARTED**, correctly deprioritised | See §14 — explicitly should not delay this phase's core automation, per the operator's own instruction. |
| Historical research pipeline / Cycle 2/3 hypothesis work | **UNTOUCHED** | Per explicit prohibition: no new sport research cycle, no reopening rejected hypotheses. |

No file was rewritten that did not need to change. Nothing was deleted; nothing superseded was silently removed.

## 2. Odds API audit results (Phase 1)

Documentation-based (no API key was available or purchased this session, per the explicit "do NOT purchase a paid tier" instruction). Verdict: **GO-leaning**, with one caveat flagged below.

- **Provider:** The Odds API (the-odds-api.com), v4.
- **Free tier:** "Starter" plan, 500 credits/month, no card required (per their published pricing at the time this was checked).
- **Quota formula:** `credits = (markets requested) × (regions requested)` per call to `/v4/sports/{sport}/odds`, charged once regardless of how many events or bookmakers the response contains. `/v4/sports` and `/v4/sports/{sport}/events` are quota-free (but still require a key).
- **Caveat:** the exact `sport_key` strings used in `TheOddsApiConfig` for Championship (`soccer_efl_champ`) and Scottish Premiership (`soccer_spl`) are sourced from a third-party API wrapper's documented sport table, **not independently confirmed against the live `/v4/sports` endpoint** (that call needs a key even though it is quota-free). The Premier League key (`soccer_epl`) is the one most consistently referenced across documentation and is lower-risk. This is the one piece of this audit that a real key will need to validate on day one — if a `sport_key` is wrong, `fetch_odds_raw` will surface a clear HTTP error rather than silently returning nothing (see the module's error handling).

## 3. Supported leagues (V1 scope)

Configured in `TheOddsApiConfig.sport_keys`: Premier League (`soccer_epl`), Championship (`soccer_efl_champ`), Scottish Premiership (`soccer_spl`) — matching the operator's specified V1 scope exactly. Extending to another league is a one-line addition to that dict, not a code change.

## 4. Supported markets (V1 scope)

`h2h` → this project's `1x2`, and `totals` filtered to exactly the 2.5-goals line → `over_under_2_5`. `spreads` (Asian Handicap) is deliberately not wired yet — see §14.

## 5. UK bookmaker coverage

Per The Odds API's documentation, `regions=uk` includes William Hill, Ladbrokes, Betfair, Unibet, Paddy Power, BetFred, Matchbook, "and more." Bet365's presence was **not** confirmed in the documentation checked this session. The live response itself is the authoritative source — the adapter does not filter by bookmaker name, so whatever the account's key actually returns is what gets used.

## 6. API credit cost per scan

`len(markets) × len(regions)` per `sport_key`, per the documented formula: with `markets=("h2h","totals")` (2) and `regions="uk"` (1 region string) as configured, that is **2 credits per league per scan**. With 3 configured leagues and one scan/day, that is **6 credits/day**.

## 7. Projected monthly credits

6 credits/day × ~30 days ≈ **180 credits/month** for the single scheduled morning scan as currently configured. (If a future pre-match refresh is added — explicitly not built this phase, see §14/§Phase 8 — that would roughly double this; still comfortably inside the free tier even at 2x.)

## 8. Free-tier viability

**Comfortable.** 180/month against a 500/month free allowance leaves ample headroom for manual on-demand runs (`workflow_dispatch`), a failed run being retried, or a second daily scan being added later without needing a paid tier.

## 9. Implemented live-data architecture (Phase 2)

`src/prediction_markets_lab/ingestion/the_odds_api_loader.py` (new, 12/12 tests passing): parses and validates The Odds API's documented v4 JSON schema (`parse_odds_response`), then canonicalises it (`build_canonical_odds_and_metadata`) into the **exact same** `{market_id: {bookmaker: {selection: decimal_odds}}}` + per-market metadata shapes `ingestion.manual_odds_loader` already produces from a CSV — so `scripts/run_daily_scan.py`'s probability/EV/grading pipeline is fully source-agnostic, per the operator's explicit instruction. The API key is read only from the `THE_ODDS_API_KEY` environment variable (`TheOddsApiConfig.resolve_api_key`), never hard-coded, never logged, never committed — per Fraser's own added security instruction. No credential is available this session, so `fetch_odds_raw`'s actual network call has **not** been exercised against a real response; this is the genuine credential gate this build stops at (see §16/§17).

`ingestion/exchange_price_loader.py` gained `best_price_from_canonical_odds`: for live data, "the best price" is simply the best of the bookmakers already returned together in one fetch, so no separate best-price file is used or needed in `--source odds-api` mode (unlike manual mode, which still requires a human-curated best-price CSV).

## 10. GitHub changes made

- Confirmed (read-only checks): repo is public, default branch is `master`, existing workflows audited (see §1).
- Committed this session: `the_odds_api_loader.py` + tests, `exchange_price_loader.py` additions + tests, `daily_bet_card.py` JSON/CSV/MD contract + tests, `run_daily_scan.py` `--source` support, `.github/workflows/daily_scan.yml` (new), `.github/workflows/tests.yml` (branch fix), `docs/GITHUB_TO_CHATGPT_HANDOFF_DESIGN.md`, this checkpoint. Full test suite: **794/794 passing** after all changes (see §15).
- Nothing was pushed to a remote by this session — per the standing project rule, Fraser pushes from his own Terminal. All commits above exist locally on the connected machine's checkout and are ready for Fraser to `git push`.

## 11. GitHub Actions workflow (Phase 4)

New: `.github/workflows/daily_scan.yml`. Triggers: `schedule` (`0 7 * * *`, i.e. 07:00 UTC daily) and `workflow_dispatch` (manual/on-demand, with an optional `run_label` input). Steps: checkout → install deps → run the full test suite first (fails fast before spending any API credits on a broken engine) → `python scripts/run_daily_scan.py --source odds-api` (reading `THE_ODDS_API_KEY` from `secrets.THE_ODDS_API_KEY`) → upload the full run output as a build artifact (always, even on failure) → commit only `daily_cards/` back to the repo (the frozen contract; `data/processed/daily_cards/*_candidates.csv` stays gitignored, matching the existing `data/processed/*` policy — not a data-loss gap, since `card.json`/`card.csv` already carry the identical full candidate list). Requires one manual action from Fraser — see §17.

## 12. Daily Bet Card schema (Phase 5)

Frozen in `reports/daily_bet_card.py`. Card-level: `run_timestamp`, `data_timestamp`, `engine_version`, `bankroll_gbp`, `fixtures_scanned`, `markets_scanned`, `candidates_analysed`, `grade_counts`, `recommended_total_exposure_gbp`, `optional_multi` (always `null` in V1), `candidates`, `system_warnings`. Per-candidate: `date`, `sport`, `competition`, `event`, `market`, `selection`, `bookmaker`, `available_odds`, `estimated_probability`, `fair_odds`, `confidence`, `uncertainty`, `historical_statistical_support`, `current_context` (deliberately always empty — no automated context source exists, so this is a schema placeholder, not a fabricated value), `expected_payout`, `ev_value_indicator`, `risk`, `recommended_stake`, `grade`, `reason`, `model_version`, `price_timestamp`. Written as `card.json`, `card.csv`, `card.md` to `daily_cards/<date>/` at the repo root. 8 new unit tests cover this contract; see §15.

## 13. ChatGPT handoff design (Phase 6/7)

Full design in `docs/GITHUB_TO_CHATGPT_HANDOFF_DESIGN.md`. Summary: because the repo is public, `daily_cards/<date>/card.md` is fetchable at a predictable `raw.githubusercontent.com` URL with zero credentials. Recommended: a ChatGPT scheduled task fetching that URL shortly after the 07:00 UTC scan and relaying (not recomputing) the numbers to Fraser in 2–4 lines. **One assumption is explicitly flagged as unverified**: OpenAI's public documentation did not confirm that a *scheduled* ChatGPT task retains the same general URL-fetch capability an interactive chat has (interactive fetching is well-established; scheduled-task fetching specifically is not documented either way in what was checked this session). A zero-uncertainty manual fallback (paste the same URL into any ChatGPT chat) is documented alongside it. No direct Claude-to-ChatGPT integration was invented; GitHub remains the sole shared channel.

## 14. Asian Handicap status (Phase 3)

**Not started this phase**, correctly and deliberately deprioritised. The operator's own instruction states AH "needs exact-line matching... but should not delay core automation," and Phase 3 was explicitly lower priority than Phases 1/2/4/5 (the live-data path and the frozen contract, both now done). `the_odds_api_loader.py`'s docstring notes `spreads` is not handled, matching this project's existing pre-instruction decision. Building AH support is a self-contained addition (map `spreads` outcomes + points to a line-matched market_id) that does not require touching anything built this session, and is recommended as the next unit of work once a real API key confirms the live path end-to-end.

## 15. Tests / status

**794/794 tests passing** after every change this session (started this instruction at 782; net +12 for `the_odds_api_loader.py` in the prior partial session, +12 more for the daily-card contract and `best_price_from_canonical_odds` this continuation — see the git log for the exact commits). `scripts/run_daily_scan.py` itself is validated by real execution rather than a unit-test harness (consistent with how it was validated in the prior "GO" instruction): a manual-mode regression run against the existing dry-run fixtures reproduced the prior all-Reject result exactly and additionally emitted a correct `card.json`/`card.csv`; an `--source odds-api` run with `THE_ODDS_API_KEY` deliberately unset stopped cleanly at the credential gate (exit code 1, the exact actionable message from `resolve_api_key`) rather than crashing or fabricating data; passing `--odds`/`--best-price` together with `--source odds-api` is rejected by argument validation, so the two sources cannot be silently mixed.

## 16. Remaining blockers

1. **No real `THE_ODDS_API_KEY` exists yet.** This is the single genuine external dependency blocking a real live scan — everything downstream of obtaining one is built and tested against documented/constructed data, but `fetch_odds_raw`'s actual network call has never touched a real response. The first real key should be treated as a validation step, not assumed correct because the unit tests pass (per the module's own docstring).
2. **The `sport_key` values for Championship/Scottish Premiership are not independently confirmed** against the live `/v4/sports` endpoint (see §2) — the first live run for those two leagues specifically should be checked for a clear HTTP error rather than silent emptiness.
3. **The ChatGPT scheduled-task browsing assumption is unverified** (see §13) — needs one real test in Fraser's own ChatGPT account.
4. Nothing in this session's work has been pushed to GitHub — it exists as local commits on the connected machine, per the standing rule that Fraser pushes.

## 17. Exact manual action required from Fraser

1. **Get a free API key** at https://the-odds-api.com (Starter plan, 500 credits/month, no card required per their published pricing).
2. **Add it as a GitHub Actions repository secret** named `THE_ODDS_API_KEY`: repo Settings → Secrets and variables → Actions → New repository secret. Never paste it into any file or commit it, per your own instruction — the workflow and the Python loader both only ever read it from the environment.
3. **Push this session's commits** (`git push`) from your own Terminal, as usual.
4. **(Optional, for a manual verification before waiting for tomorrow's 07:00 UTC schedule)**: trigger `daily_scan.yml` once via GitHub's "Run workflow" button (Actions tab → daily_scan → Run workflow) to see the first real live-data run end-to-end.
5. **(Optional, for the ChatGPT side)**: set up the scheduled task described in `docs/GITHUB_TO_CHATGPT_HANDOFF_DESIGN.md` §3, and check the next day whether it actually fetched the URL — this is the one part of the design that could not be verified from this session.

## 18. Distance from FIRST REAL AUTOMATED DAILY BET CARD

**One external dependency away.** Every piece of code, every test, the scheduled workflow, and the frozen output contract are built, tested (794/794), and committed locally. The only thing between this checkpoint and a first real, fully automated, zero-manual-CSV Daily Bet Card is Fraser completing the two manual steps in §17 (get a key, add the secret, push) — no further engineering work is required to reach that milestone. Asian Handicap, the ChatGPT scheduled-task verification, and any future pre-match refresh/settlement automation are correctly sequenced as work that follows the first real card, not work that blocks it.
