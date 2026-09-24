# Phase V2-5 — Unified Cross-Sport Prospective Prediction Platform: Return Checkpoint (2026-09-24)

## Production
1. **settlement_and_performance: VERIFIED HEALTHY.** Run 36052896877 (manual, d4bb169), 20:08:54–20:10:12Z. Tests passed; settle,
   shadow-compare, performance and status steps all succeeded; outputs committed as 3616d77 (performance JSON, status, shadow JSON,
   3 archived score payloads). About 6 credits (3 leagues × scores; not logged by that workflow). 0 bets settled: no completed matches in the
   window. Shadow: 187 football-data results loaded, 0 comparisons (no league match in the Odds API's 3-day window), 0 disagreements.
   The would-settle view matched 3 of the 4 stuck 20 Sep backfill bets (Bolton is still unmapped).
2. **All workflows healthy:** tests 36052807610 (d4bb169) ✅ · daily_scan 36023253292 ✅ · tennis 36048224462 (15:30 cron, started 19:27;
   a 4 h delay) ✅ · settlement 36052896877 ✅. Clean-clone CI ✅.
3. **Master:** GitHub is at 3616d77 (V2-4 pushed, synced before V2-5 work). Local commits ce76167 (protocol, pre-registered first), e6fc280 (platform) and this
   checkpoint are waiting for Fraser to push.

## Platform
4. **Registry** (schema v2, the source of truth): ATP/WTA VALIDATED_HISTORICAL · COLLECTING; NBA VALIDATED_HISTORICAL · AWAITING_SEASON
   (2026-10-20); DC **PROVISIONAL_PROSPECTIVE** · COLLECTING; 1X2 & O/U VALIDATED_HISTORICAL · COLLECTING (money engines); BTTS
   RESEARCH_VALIDATED · NOT_WIRED. Validated in code: no money eligibility without validated status.
5. **Canonical schema:** 33 prediction fields plus 6 settlement fields in a separate file (`UNIFIED_BOARD_SPEC.md`).
6. **Unified ledger:** `predictions/unified_ledger.csv`, append-only with header and byte-prefix guards; the first snapshot wins; IDs are deterministic
   (retries and later scans cannot duplicate or overwrite).
7. **Tennis:** mirrored, not migrated; the original IDs are kept, so tennis settlements join directly. The dry run mirrored all 8 rows cleanly.
8. ATP prospective: **0**. 9. WTA prospective: **8** (9–31 h before start). 10. Settled tennis: **0** (first settlement at 22:30 today).
11. **NBA:** adapter (frozen method: bookmaker mean odds → proportional; exchanges excluded; ≥ 3 books), budgeted collector and scores
    settlement built and tested. 12. **Activation:** automatic from **2026-10-20** (opening night), only when games start within 36 h. No calls before then.
13. **DC:** integrated from the 1X2 data already fetched (0 credits), 3 rows per match, synthetic dutch price, flagged PROVISIONAL_PROSPECTIVE.
14. **DC prospective:** 0 rows yet. The Odds API feed has no league fixture before 9 Oct, so the first snapshots come from the ~8 Oct scan.
15. **Football 1X2 / O-U:** integrated on the same terms (0 credits). BTTS deliberately not wired.
16. **Board:** built; `reports/latest_prediction_board.{json,csv,md}` plus performance JSON, rebuilt by every workflow.
17. **Board example** (dry run on a clone, 24 Sep 20:27Z): "Upcoming events 4 · Valid predictions 4 · Sports: tennis · ≥70: 1 · ≥80: 0 ·
    System HEALTHY · credits 449". No ≥80% row, so the top table is empty and says so. The prospective evidence table covers all 7 engines.
18–23. **Current upcoming predictions:** ≥70: 1 · ≥75: 0 · ≥80: 0 · ≥85: 0 · ≥90: 0 · ≥95: 0 (tennis only; no football in window).

## Evidence
24–28. **Prospective performance:** pooled n = 0 settled; ATP 0; WTA 0 settled; NBA 0; DC 0. Nothing can be said yet (no settlements).
29. **Maturity:** all engines COLLECTING. Pre-registered thresholds: EARLY ≥ 50 · INTERMEDIATE ≥ 300 settled and ≥ 100 at ≥ 80% · MATURE ≥ 1,000 / ≥ 300.
    Counted in events (1X2/DC rows are grouped per match), per engine and for the ≥80% subset. A −10 pp alarm applies at ≥ 100 settled ≥80% rows.
30. **Timing:** each row now records configured time, workflow start, prediction time and minutes to event. Delays so far (2–6.7 h)
    have not caused a missed or late snapshot; all tennis snapshots were 9–31 h pre-start. The external trigger will be proposed only if ≥ 10% of eligible events are missed or late
    over 14 days. **No token requested.**
31. **Shadow comparisons: 0 / 100.** 32. **Disagreements: 0.** Accumulation starts with the 9–11 Oct fixtures. The Odds API stays primary.
33. **Credits:** 449 remaining (51 used in September).
34. **Projected:** ~315–440/month; DC and unified settlement cost 0; the new settlement guard removes up to ~6 credits/day of calls that
    could not settle anything (about 80 credits before 9 Oct alone) (`API_USAGE_PLAN.md`).
35. **Health output:** per-component OK/STALE/OUTAGE/FAILED/UNKNOWN, an overall HEALTHY / HEALTHY_WITH_WARNINGS / DEGRADED, a banner on the
    board, and outage and stale booleans in the JSON.
36. **Stale safeguards:** card > 6 h, outside the window, started, bad or duplicated triplet, unknown engine or invalid registry → no row (fail
    closed, counted by reason). A failed scan still rebuilds the board so staleness is visible.
37. **ChatGPT handoff:** read-only contract on the board JSON (schema v1) plus the performance, status and money-card JSON. It must not recompute or override anything.
38. **Money-layer separation:** confirmed and enforced by a test (the board package cannot import decisions/risk/ev). The Money Card is unchanged.
39. **Multi statuses:** prediction_valid / single_eligible (pre-filter only) / multi_research_eligible (≥ 80%) are separate fields. Multis
    and same-game combos stay disabled.
40. **Clean-clone protection:** new tests need no gitignored data. Workflow add-steps are per-path and tolerant; unified steps are
    continue-on-error, so a board failure cannot block the scan, settlement or Money Card.

## Engineering
41. Local: **1,140 passed**. 42. Clean clone: **1,132 passed, 8 skipped**.
43. **Files:** `src/prediction_markets_lab/prediction_platform/{schema,registry,ledger,adapters,settle,performance,health,board}.py`,
    `scripts/run_unified_prediction_board.py`, `tests/unit/test_prediction_platform.py` (17 tests), a settlement guard plus test,
    `research/platform_v2/unified_board/{PROSPECTIVE_PROTOCOL,UNIFIED_BOARD_SPEC,ENGINE_INTEGRATION_AUDIT,API_USAGE_PLAN,
    SYSTEM_HEALTH_SPEC,PROBABILITY_ENGINE_REVIEW_STANDARD,V2_5_RETURN_CHECKPOINT}.md`, registry JSON/MD v2.
44. **Commits:** ce76167, e6fc280 and the checkpoint commit.
45. **Production impact:** additive steps in daily_scan, tennis_prediction_board and settlement (continue-on-error); a workflow-start timing step; the settlement
    scores guard (the only behaviour change: it skips calls that could not settle anything; the default code path is unchanged). No change to the scan, grading,
    Money Card or frozen engines.

## Decision
46. **B — READY WITH MINOR LIMITATIONS.** The pipeline is built, tested and wired, with zero new credits for football/tennis. Limitations: (a) it has not yet
    run inside GitHub Actions; the first real run comes after the push; (b) no football events until ~8 Oct and no NBA until 20 Oct, so the
    first weeks will be tennis-only; (c) daily_scan doesn't log credits; (d) football-data settlement for the board isn't exercised on live data
    until the 9–11 Oct matches.
47. **Recommended next phase: D, more prospective collection.** No new development until the unified board has run for ~3–4 weeks
    (through the first NBA week and two football rounds). Then run a short operational review (missed-snapshot rate, settlement
    coverage, shadow gate). Paper Multi Engine (A) only after the first engines reach EARLY maturity at the ≥80% level.
48. **Fraser approval needed:** push ce76167/e6fc280/checkpoint, then run **tennis_prediction_board (mode: board)** once to exercise the
    unified step on GitHub. I will verify the run and the first real `latest_prediction_board.md`.
