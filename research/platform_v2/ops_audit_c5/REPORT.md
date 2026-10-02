# Operational audit c5 (2026-10-02) — engine integration, prospective evidence, 10 Oct readiness

Scope (directive relayed 2 Oct 23:01): audit only. Corners Model A, the corners A/B/C pre-registration and the Player SOT
pilot/cycle-2 specifications are untouched. No probability model, threshold, grade, staking rule or Track A hypothesis was changed.
No Odds API credits used. No new market family started.

## (a) Daily Bet Engine end-to-end

| Stage | Status | Notes |
|---|---|---|
| Fixture discovery | Working (tennis daily; football via daily_scan) | Football had 0 fixtures in the latest run (international break) — expected, not a defect. |
| Stage A predictions | Working for tennis + football 1X2/totals | Corners collector writes its own rows (`corners_collector.yml`, daily); SOT has no live predictor (research only). |
| Market acquisition | Working (Odds API h2h/totals) | `pre_close_capture.yml` (hourly cron) has run only 2 times since 29 Sep: GitHub throttles the schedule. H2 pre-close captures will therefore be sparse. Reported, not changed (Track A frozen). |
| Stage B candidates / financial evaluation / grades | Working | Decision shadow 118 rows: REJECT 94, MULTI 22, WATCH 2. Reasons (multi-label): NET_EV_NOT_POSITIVE 110, EXCHANGE_SPREAD_TOO_WIDE 34, NET_EV_BELOW_PAPER_GATE 7, ODDS_BELOW_PAYOUT_FLOOR 5. |
| Paper ledger | Working | bsv2 paper selections: 10 (9 under superseded bsv2-1, 1 under bsv2-3). Latest run bsv2-4: 36 events, 0 paper bets. |
| Settlement | **Gaps** (below) | Tennis settled via TennisCourtLog (weekly refresh). Legacy football ledger has 4 bets (kickoff 20 Sep) stuck. |
| Bankroll/performance | Working on settled rows only | `paper_betting_v2/settlements.csv` does not exist yet (0 paper settlements). |

### Missing integration before a validated Corners or Player-SOT engine can plug in (not built — specification frozen, nothing qualified yet)
1. Adapter from collector rows (`corners_collector.prediction_rows`) to the common `Prediction` record (`prediction_platform/adapters.py`) + registry entry + model version.
2. Quote source: bsv2 `prices.py` only knows Odds API h2h/totals. Corners/SOT quotes need a generic quote source wired to `research_shadow/execution.py` (consensus vs best executable net odds, commission never assumed zero).
3. Live Betfair prices must come from a UK machine (Fraser's Mac); GitHub Actions/US IPs are blocked. A daily automated corners/SOT card therefore needs a Mac-side runner or another exchange/book source.
4. Settlement: `settle.py` has no corners totals or player-SOT outcomes. Corners can settle from football-data.co.uk; SOT needs a player-stat source.
5. Stage A uncertainty (sigma) per engine and an `engine_statuses` policy entry (policy config — needs approval when an engine qualifies).
6. **Blocker for operational SOT (not for the research):** the API-Football free plan only serves seasons Y-4..Y-2, i.e. no current-season fixtures/lineups/player stats. An operational SOT engine needs a current-season player-data source for features and settlement. Decision deferred until SOT qualifies on the holdout (~14 Oct).

### Settlement infrastructure defects found (reported; not fixed in this pass)
- `status/settlement_shadow.json`: 36 D1/N1 team names unresolved in alias tables; F1 missing from shadow sources; Football-Data shadow migration gate 0/100 comparisons.
- 4 legacy football paper bets (kickoff 2026-09-20) remain PENDING because the primary settlement source does not cover them.
- Fixing these needs fixture-matched alias mapping with verification. Not done in a rushed pass; proposed as the next infra task (no model/threshold impact).

## (b) Prospective evidence (descriptive; no inference, no tuning)

| Item | Count |
|---|---|
| Unified ledger tennis predictions | 167 (WTA 103, ATP 64) |
| Settled | 12 (7 correct / 5 incorrect) — mean p 0.713, hit rate 0.583, Brier 0.2553 |
| Started >6h ago but unsettled | 119 — cause: TennisCourtLog source refresh is weekly (latest tourney_date 2026-09-27); lag, not a defect |
| bsv2 paper selections | 10; paper settlements 0 |
| Legacy football paper ledger | 24 pending (4 stuck, see above) |
| Track A H1/H2 rows | 0 (no football fixtures / no due selections during the international break) |

12 settled predictions are far too few for calibration; no calibration claim is made. Nothing is interpreted as evidence of profitability.

## (c) 10 October readiness

| Check | Result |
|---|---|
| Probe 2 scheduled | Yes — 2026-10-10 03:25Z (one-shot; script pays only if an EPL event is 1–24h out; never twice; branch `probe/prop-price-c2` at da34fec, guard run recorded NO_PAID_CALL). |
| Betfair windows A/B/C scheduled | Yes — 08:15Z, 12:58Z, 13:40Z, bound to Fraser's MacBook, firing into this session. |
| Fresh-container robustness | Fixed: all 4 task prompts now clone + install the repo if the container was reclaimed and message Fraser on failure. |
| Credentials | Betfair: env `BETFAIR_APP_KEY`/`BETFAIR_USERNAME` + getpass password, never stored. Odds API key is a GitHub secret. Prompts never ask for values. |
| Read-only | Betfair client whitelists listCompetitions/listMarketTypes/listEvents/listMarketCatalogue/listMarketBook only. |
| Private prices cannot be committed | Verified with `git check-ignore`: `betfair_audit/raw/` and `data/private/` are ignored; only CAPTURE_SUMMARY/COVERAGE aggregates are committable. |
| Idempotency | Each capture writes timestamped files (no overwrite); the new report de-duplicates by `capture_ts`. |
| Aggregate report | New `scripts/betfair_liquidity_report.py` (multi-window table, corners + player SOT only, 10% gate shown unchanged); dry-run test on mock summaries passes. |
| Failures surfaced | Probe workflow failure / missing attempts row and Betfair script errors are reported to Fraser by the task prompts. |

## Stop
Development stops here. Next decisions: ~6 Oct SOT 2022/23 development-data audit; 10 Oct market/liquidity evidence; ~14 Oct sealed SOT holdout.
