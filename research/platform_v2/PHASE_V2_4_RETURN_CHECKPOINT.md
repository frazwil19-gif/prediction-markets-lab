# Phase V2-4 — Production Recovery + Settlement Migration Gate + Football Double Chance: Return Checkpoint (2026-09-24)

## Production recovery
1. **daily_scan: VERIFIED HEALTHY.** Run 36023253292 (manual, 1cd2259), 15:51:36–15:52:40Z, tests passed, 38 fixtures,
   190 candidates, 0 money-qualified; outputs committed as 8a1b1b6; 6 credits.
2. **tennis_prediction_board: VERIFIED HEALTHY.** Run 36023546752 (8a1b1b6), 15:54:05–15:55:19Z, WTA Singapore, 3 events, 3
   valid predictions, 1 new ledger row, ledger prefix byte-identical; 1 credit.
3. **tests workflow green** at 1cd2259 (run 36021901773).
4. **settlement_and_performance: NOT YET VERIFIED.** Its first post-fix run is the next 21:00 cron (it usually starts around 23:30). A manual dispatch would verify it sooner.
5. **Outage recorded:** 22 Sep 12:27 → 24 Sep 15:40 UTC = SYSTEM OUTAGE / NO PROSPECTIVE DATA; nothing reconstructed
   (`PRODUCTION_RECOVERY_LOG.md`).
6. The manual WTA predictions of 23 Sep stay in the ledger and will settle normally.
7. Board display note: already-ledgered events show the current snapshot. The ledger's first snapshot is the one that counts.

## Schedule reliability (`SCHEDULE_RELIABILITY_AUDIT.md`)
8. daily_scan (07:00 cron) starts 5.1–6.7 h late; settlement (21:00) 2.6–3.0 h; tennis 06:30 → 5.6 h, 22:30 → 2.2 h.
9. Now instrumented: `tennis_predictions/run_log.csv` records configured cron, trigger, run id, actual start and median minutes to start.
   Ledger rows already carry prediction and event times, so minutes-to-event is exact per prediction.
10. Recommendation: an external free trigger (cron-job.org → workflow_dispatch). It needs a fine-grained token that Fraser creates;
    it is proposed only. Redundant crons are possible but limited by credits.

## API budget
11. `config/api_budget.json`: plan 500, target ≤ 425, reserve ≥ 75; caps football scan 180, settlement 60, tennis 120,
    NBA 60 (sum 420).
12. Guard `ops/api_budget.py`: monthly spend from the consumer's credit log plus a floor on remaining credits. Optional consumers have a floor of 150
    and the core floor is 75, so optional consumers stop first. Wired into the tennis board, with tests.
13. Credits today: 49 → 50 used (450 remaining) after the single DC probe.

## Settlement migration (`SETTLEMENT_MIGRATION.md`)
14. Adapter `settlement/football_data_results.py` built: exact-alias matching, and MATCHED / AMBIGUOUS / NOT_FOUND /
    UNRESOLVED_NAME. Ambiguous or unresolved fixtures are never settled. 12 tests.
15. **Provenance catch:** my first edit to `football_team_aliases.yaml` broke a hash-frozen research test. It was reverted, and new
    names now live in a settlement-only overlay `config/settlement_team_aliases.yaml` (a conflict is an error).
16. Shadow step added to settlement_and_performance (continue-on-error, never writes the ledger, 0 credits). Odds API score payloads are now archived.
17. Gate: ≥ 100 matched comparisons with 0 disagreements, then the switch, with the Odds API kept as fallback. Expected in about 1–2 match weeks (the international break
    delays it). `settlement_source`/`mapping_status` columns are added at switch time.
18. Currently 22 pending paper bets; 4 have passed kickoff and cannot be settled by the Odds API (backfill rows).

## Registry
19. `PROBABILITY_ENGINE_REGISTRY.json/.md` is the source of truth; DC entry updated (below).
20. NBA paper board design is frozen as approved. Not activated, no recalibration.

## V2-4 Football Double Chance (`double_chance/`)
21. **Pre-registered first** (`DC_PROTOCOL.md`, commit 217c7fb), before any evaluation.
22. **No untouched historical data exists**; all 2020/21–2025/26 is exposed. 2026/27 Aug–Dec is sealed (HOLDOUT_SPEC +
    sha256), opens ≥ 2027-01-03.
23. Estimator: frozen production 1X2 consensus, DC = pairwise sums, nothing fitted. 1X, X2 and 12 are separate binary events.
24. **32.6% figure: not reproduced exactly** (the original code wasn't saved). Closest: 32.5% (1,875/5,763) and 32.4%
    (1,879/5,800), with 86.4 → 86.4. "n = 1,885" was the ≥80 count. Pre-registered primary: 31.5%, 86.3 → 87.1.
25. ≥60/65: 100% of matches, 77.5 → 78.3. ≥70: 92.9%, 78.1 → 78.5.
26. ≥75: 52.0%, 82.7 → 83.2.
27. **≥80: 31.5% (1,855), 86.3 → 87.1**; validation 86.5 → 88.0; confirmation 85.2 → 89.1 (n 129).
28. ≥85: 16.4%, 89.9 → 91.7. ≥90: 7.8%, 92.8 → 95.0. ≥95: 1.2%, 95.8 → 98.6.
29. Every band with n ≥ 200 is inside the 99.5% Wilson interval (validation and confirmation, both views).
30. Slopes: dev 1.06 [0.98, 1.15], val 1.09 [0.98, 1.20], conf 0.95 [0.74, 1.18]. AUC 0.65–0.71.
31. Pattern: slight under-confidence at ≥85 (+1.5–2 pp). Reported, not corrected.
32. Home/away: 1X gives 73% of ≥80 picks; X2 gives 502 picks (86.2 → 86.9). 12 is never the best at ≥80.
33. League: ≥80 share is E0 ~40–45%, SC0 ~36–44%, E1 ~16–26%. Weakest cell: E1 2021/22.
34. Season: 30–35% each season; 2025/26 24% (partial). All seasons ≥ 15%.
35. Sensitivity: Shin and odds-ratio 32.7–33.0% at similar calibration; the all-books panels are within 1 pp.
36. **Live DC prices:** the Odds API `double_chance` market is live per event (4 UK books), costing 1 credit per event per region. Probe archived.
37. **Payout reality:** a ≥80% DC has fair odds ≤ 1.25, below the 1.33 floor, so no DC ≥80 single can pass current policy. DC books'
    margin is about 5%.
38. **Decision: A (provisional; exposed data).** Validated probability product and leg pool; not money-eligible.
39. Prospective DC board designed (`DC_BOARD_DESIGN.md`): rows come from the daily_scan's existing h2h (0 credits), with a synthetic DC price.
    **Not activated.**

## Expand vs consolidate
40. **Recommendation: consolidate.** Four validated engines (ATP, WTA, NBA, DC) share one pattern: ledger, settlement,
    performance. Build one **unified cross-sport paper Prediction Board** (single ledger schema with engine@version, one
    settlement dispatcher, one performance report) before adding another sport. It is cheaper in credits and code, and it is the prerequisite
    for evidence-based multis.
41. Expansion candidates stay parked: NHL/MLB moneyline (data partly sourced), which have lower high-P potential.

## Engineering
42. Local suite: **1,122 passed**. Clean-clone suite: see 43.
43. Clean clone (at 8ce0e83, before the DC files): 1,111 passed, 8 skipped. Re-run at the final commit below.
44. Commits: 8ce0e83 (recovery, schedule, settlement shadow, budget guard), 217c7fb (DC pre-registration), plus the DC results commit.
45. Nothing touches frozen engines or the production money gate. No purchases. 1 credit spent on research.
46. **Needs Fraser:** `git push`; then verify settlement tonight (or dispatch it manually). Decisions: approve the unified board (40) and the
    DC board activation (39), and optionally create the external-trigger token (10).
