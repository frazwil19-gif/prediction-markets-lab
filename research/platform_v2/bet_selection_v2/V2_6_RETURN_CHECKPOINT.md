# Phase V2-6 — Production Audit + Bet-Selection V2 + Prospective Paper Betting: Return Checkpoint (2026-09-29)

All figures come from the GitHub Actions API, repository artefacts at `38a07ee` (origin/master, 29 Sep 02:08 UTC), and local runs.

## 1. Production health and GitHub run IDs
**Healthy in scheduling and exit codes, with one repaired defect that was losing tennis evidence (§14).** Since 24 Sep
15:40 UTC, every production run has succeeded:
| workflow | runs (ID · start UTC) | result |
|---|---|---|
| daily_scan | 36023253292 (24 Sep 15:51, manual) · 36136033933 (25 Sep 12:37) · 36240894984 (26 Sep 12:06) · 36320401324 (27 Sep 12:51) · 36440968070 (28 Sep 15:05) | ✅ all |
| tennis_prediction_board | 36023546752 · 36048224462 · **36056050697 (V2-5 manual board, 24 Sep 20:36)** · 36078480704 · 36132875054 · 36179839955 · 36205913435 · 36239575726 · 36263401672 · 36283417391 · 36318539499 · 36343527534 · 36364191218 · 36435040903 · 36485475123 · 36511147967 (29 Sep 02:07) | ✅ all |
| settlement_and_performance | 36052896877 (manual) · 36074679937 · 36202853263 · 36279573777 · 36359694768 · 36505467867 (29 Sep 00:55) | ✅ all |
| tests (push) | 36021901773 · 36052807610 · 36056020346 | ✅ all |
Outage history is preserved: runs 35939370795, 35996755062 and 36000120922 (24 Sep, SHA 301aa36) failed. That is the tail of the
22–24 Sep outage already recorded in `PRODUCTION_RECOVERY_LOG.md`. The push-triggered `weekly_report` and `data_validation` "failures"
(0 s, every push) came from placeholder files with no `jobs:`. They are now fixed with a manual-only no-op job.

**V2-5 artefact validity (not just exit codes):** run 36056050697 committed `cb88ae4` with the unified ledger (+9 rows), board
JSON/CSV/MD and performance JSON. The current `reports/latest_prediction_board.md` (29 Sep 02:08) is well-formed, HEALTHY, and shows
credits of 412.
- 0 post-event predictions (every `prediction_timestamp < event_start`)
- 0 duplicate IDs in the unified ledger or settlements
- 0 mutated historical rows across all git revisions of `unified_ledger.csv`, `ledger_predictions.csv` and `paper_bets.csv`, ignoring the documented `money_qualified` column add and status fields

## 2. Prospective predictions / settlements by engine
| engine | ledgered | valid | settled | correct |
|---|---|---|---|---|
| wta_match_winner | 29 | 10 | 10 | 5 (mean P 72.1% → 50%; n = 10, uninformative) |
| atp_match_winner | 12 | 0 | 0 | — |
| football 1X2 / O-U / DC | 0 | 0 | 0 | — (no fixture inside 48 h: the next fixtures are 9–11 Oct, consistent with the published PL calendar) |
| NBA | 0 | — | — | activates 20 Oct |
The 31 China Open rows (12 ATP + 19 WTA, starting 30 Sep–1 Oct) are all research-only (bookmaker consensus ~28–55 h pre-start). See §14.

## 3. Observed timing problems
GitHub cron delays are large and getting worse.
| workflow | cron (UTC) | actual starts since 24 Sep | delay |
|---|---|---|---|
| daily_scan | 07:00 | 12:06–15:05 | **5.1–8.1 h** |
| tennis morning board | 06:30 | 11:40–14:18 | 5.2–7.8 h |
| tennis afternoon board | 15:30 | 18:40–21:20 | 3.2–5.8 h |
| tennis settle | 22:30 | 00:38–02:07 (next day) | 2.1–3.6 h |
| settlement | 21:00 | 23:28–00:55 | 2.5–3.9 h |
Consequences:
- Commit and board labels carry the *run* date (the 22:30 settle is labelled the next day).
- Tennis settlement lagged 2–5 days, because TennisCourtLog updates weekly (all 10 settlements landed on 29 Sep 02:08).
- The 25 Sep morning board ran with a median of 14 min to start.

The V2-5 external-trigger rule (≥ 10% missed or late eligible events over 14 days) cannot be evaluated yet, because no eligible-event
denominator is logged. That is an open item.

## 4. API credits
28 Sep 21:21 UTC: **88 used / 412 remaining** (plan 500). **V2-6 adds 0 credits.** The October forecast is ~281–381, within the target
of ≤ 425 with a reserve of ≥ 75 (`PRICE_CAPTURE_AND_API_BUDGET.md`).

## 5. V2-6 features and files
- `src/prediction_markets_lab/bet_selection_v2/{prices,evaluate,paper_ledger,bankroll,report,multi}.py`, `scripts/run_bet_selection_v2.py`
  (evaluate / settle / report / diagnose), `config/bet_selection_v2.yaml` (rule_version `bsv2-1`).
- Docs, pre-registered in commit `15cc1de` before any evaluation: `BET_SELECTION_V2_SPEC`, `PRICE_CAPTURE_AND_API_BUDGET`,
  `STAKING_FRAMEWORK`, `MULTI_RESEARCH_SCHEMA`, `LIVE_GATE_PREREGISTRATION`.
- `scripts/run_tennis_prediction_board.py`: 0-credit capture of all bookmaker/exchange prices from the response it already pays for
  (`tennis_predictions/price_snapshots.csv`). The capture is wrapped so it cannot affect the frozen ledger.
- Workflows: one `continue-on-error` step each in daily_scan (evaluate), tennis (evaluate/settle) and settlement (settle). Each is
  gated on tests passing and uses per-path `git add`.
- Unchanged: frozen engines, the Money Card, `paper_ledger/`, grading and the money gates.

## 6. Real-price coverage and limitations
- Tennis: the Betfair back price for every validated prediction, plus UK bookmaker prices from the next board run onward.
- Football: the card's best price per selection (0 credits).
- Double Chance: **no executable price** (synthetic dutch excluded by design; not fetched).
- **Structural finding:** against its own source, a consensus engine has EV ≤ 0. The retrospective diagnostic
  (`reports/bet_selection_v2_retrospective.json`, not selections) scored **10/10 settled WTA predictions at negative net EV** at the
  recorded Betfair back price (mean −4.2%; 2 would have been MULTI_RESEARCH, 8 REJECT). Positive EV can only come from
  bookmaker prices above the exchange-derived fair price, which is what the new tennis capture now measures.
- Football P is an inclusive consensus that contains the priced book (tagged `INCLUSIVE_CONSENSUS`), so it is a weak value reference.
- Matchbook commission is unknown, so those candidates are rejected until verified.

## 7. Genuine pre-event paper selections: **0**
No validated upcoming prediction exists yet; all 31 upcoming rows are research-only. Dry run at 08:07 UTC: 31 events scanned, 0 valid,
31 REJECT (`PREDICTION_NOT_VALID`, `NO_EXECUTABLE_PRICE`). The Money Card had 0 money-qualified bets on every card from 22 to 28 Sep.

## 8. Paper expected / realised results
None yet. The only numbers are the retrospective diagnostic above: hypothetical −3.25 units on 10 level stakes. That is descriptive,
not a paper result.

## 9. Staking and bankroll framework
The £20/30/50/100 × flat 1%, flat 2%, ⅛ Kelly (2% cap) and minimum-stake policies are built and tested, with a 5% per-bet cap, a
10% daily exposure cap, a −10% daily lock and a −30% drawdown stop. There is no martingale (`policy_stake` refuses unknown kinds).

Findings from the rules alone:
- £30 × 2% = £0.60 is rounded up to the £1 exchange minimum (3.3%).
- **On £20 the £1 exchange minimum is exactly the 5% cap. After one loss, exchange bets become infeasible (skipped).**
- £3 on £30 (10%) is never allowed.

## 10. Multi readiness
The schema and dependency flags are built (SAME_EVENT / SAME_PARTICIPANT blocked; SAME_TOURNAMENT_DRAW / SAME_COMPETITION_ROUND /
SAME_DAY_SAME_SPORT flagged). Combined odds are `NOT_QUOTED` unless a real multi price is observed. `multi.enabled: false`. The
activation gate is pre-registered. Readiness is **0 of 4 gate criteria**.

## 11. Settlement shadow comparison
0 / 100 comparisons and 0 disagreements. There were no football matches in the window, and none are possible before 9 Oct.
187 football-data results were loaded, with 2 unresolved names (Bolton, Lincoln).

## 12. Tests
- Local: **1,168 passed, 8 skipped**.
- Clean clone of the V2-6 branch: **1,168 passed, 8 skipped**. The baseline before changes was 1,132 / 8.
- New tests: 3 for Amendment A1 and 33 for bet_selection_v2. They cover fair odds, EV, commission, break-even, stale / after-start
  prices, no post-event selections, immutability and tamper detection, idempotent retries, fail-closed settlement, bankroll arithmetic
  and locks, price-source compatibility, config guards, workflow wiring, and the separation from the money layer.

## 13. Commits and deployment status
- `966d45e`: Step 0 repair (Amendment A1 + placeholder workflows), pushed to branch `fix/tennis-first-valid-snapshot`.
- `15cc1de`: V2-6 pre-registration.
- `789f996` + this checkpoint: V2-6 build, on branch `v2-6-bet-selection`, which contains the fix.
- **Nothing is on master and nothing is deployed.** No GitHub run has exercised V2-6 yet.

## 14. Unresolved blockers
1. **Snapshot-canonicality defect (fixed, not yet deployed).** A research-only first snapshot blocked the first validated snapshot, so
   the whole China Open would have yielded 0 valid predictions. It must be merged before the next board run. Matches that start
   before the merge are lost as validated evidence. Documented in
   `research/platform_v2/tennis_prospective/PROTOCOL_AMENDMENT_A1_FIRST_VALID_SNAPSHOT.md`.
2. Four legacy paper bets (20 Sep, no provider IDs) have been stuck PENDING for 9 days. Fail-closed is correct, but only the shadow
   adapter can settle them. There are also five duplicate legacy research bets across the two ID schemes. These are pre-existing
   Money-Card-side issues; they were left untouched and flagged.
3. Cron delays (§3). There is no missed-event denominator yet.
4. The football shadow gate can't progress until 9 Oct.

## 15. Exact next action for Fraser
1. Merge `fix/tennis-first-valid-snapshot` now, **before ~11:30 UTC today**. Then, optionally, run **tennis_prediction_board (mode:
   board)** once manually (≈ 2 credits) so exchange snapshots for the 30 Sep 02:00 matches don't depend on a delayed cron.
2. Merge `v2-6-bet-selection` (a fast-forward on top of the fix), then run `git pull` on the Mac.
3. After the next board run, I verify the upgrade rows, `price_snapshots.csv` and the first real `reports/bet_selection_v2.md`.

## 16. Recommendation
**Continue collection. V2-6 now runs passively inside it. Fix operations only where evidence is being lost.**
- No new sport and no gate changes.
- The first evidence review happens when the pre-registered sample thresholds approach, not on early P&L.
- The key open question is empirical and now measurable at zero cost: how often does any UK bookmaker quote above the Betfair-derived
  fair price by more than 2%, at ≥ 1.33, within 24 h of start? If that rate is near zero, the honest conclusion is "accurate
  probabilities, no purchasable value," and it should be recorded as a negative result.
