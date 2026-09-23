# Platform V2 — Architecture / Audit / Roadmap: Return Checkpoint (2026-09-23)

Design only. **No production change, no threshold change, no multi deployed, no data bought, no new model built.**

1. **Objective:** a multi-sport probability platform plus disciplined bet selection. First ask "what is most likely to happen?",
   using the best validated estimator (market included), then separately "is this price worth the risk?". `MASTER_OBJECTIVE.md`.
2. **Current architecture:** Odds API → proportional de-vig consensus → EV-based A+/A/B/C grade → money-qualification gate → Daily
   Money Card → paper/real ledgers → settlement/performance, all on GitHub Actions. `CURRENT_VS_TARGET.md` §A.
3. **Target:** Layer A probability engines (registry, intervals, support) → Prediction Board → Layer B bet selection → Layer C
   portfolio/multi → Bet Card → Fraser.
4. **Major gaps:** Prediction Board; engine registry and uncertainty intervals; current context; multi engine; raw quote
   archive and closing snapshots; risk gates not wired live; tennis live feed.
5. **Keep unchanged:** ingestion pattern, consensus pipeline, money gate and payout values, ledgers, settlement, Actions, all research records.
6. **Eventual refactor:** `grading.py` (probability-first), `confidence.py` (→ quote quality + interval), pluggable
   margin removal, schemas, card → board + card, risk wiring.
7. **Current engines:** football 1X2, O/U 2.5, BTTS; tennis winner (Betfair market, Global Elo).
8. **Strongest estimator for each:** consensus · consensus · market-implied Poisson · Betfair market (candidate, not yet formally validated as an engine).
9. **Historical samples:** 5,776 · 4,640 · 4,595 · 7,136 (Betfair-priced 2021–23) / 2,921 (Elo 2025 holdout).
10. **Calibration:** football engines within ~±2 pp in dense bands. **Football 1X2 favourites under-predicted** (≥80%:
    83.7% priced vs 88.3% won). Tennis market within ±0.6 pp from 65–90% (96.3% won vs 93.8% at 90%+). Tennis Elo overconfident at the top.
11. **High-probability coverage (share of events ≥80%):** 1X2 3.3%, O/U 0.1%, BTTS 0%, **tennis market 20.7%**.
12. **Uncertainty limits:** only band-level Wilson CIs exist. No per-candidate interval yet; the HIGH/MEDIUM label is quote dispersion, not uncertainty.
13. **Context limits:** none automated in any engine; `current_context` is empty by design.
14. **Next candidates:** margin-removal calibration (cross-cutting), tennis market engine, football league breadth, AH, NBA.
15. **Data for each:** all in repo except NBA (none) and extra football leagues (free football-data.co.uk files, not yet downloaded).
16. **High-P potential:** tennis very high; 1X2 favourites moderate; US sports unmeasured.
17. **Live compatibility:** football strong (44 soccer keys); **tennis weak on the Odds API** (1 active tournament today);
    Betfair Delayed key is the candidate path (terms to verify).
18. **Recommended next research cycle:** **V2-1 margin-removal calibration study**, then **V2-2 tennis market engine**.
19. **Why:** every current engine is market-based. The evidence shows the de-vig method misprices exactly the
    high-probability region V2 and multis depend on. It is free, uses existing data and improves everything
    downstream. Tennis is where strong predictions actually live.
20. **New data needed:** no purchase. Possibly free extras: more football-data.co.uk leagues, and a Betfair Delayed app key.
21. **Multi architecture:** eligibility → dependency screen → joint P + Monte Carlo interval → per-bookmaker combined odds →
    EV vs independent reference → exposure → PAPER only. `MULTI_ENGINE_SPEC.md`.
22. **Leg eligibility:** passes every single-bet check except the payout floor; support STRONG initially; value ≥ 0 against an independent reference; context checked.
23. **Dependency method:** a relation table (same event / team / competition-day / shared shock), each checked empirically.
    Cross-event 1X2 favourite pairs showed no dependence beyond marginal calibration (63.1% realised vs 60.2% product, explained by favourite under-prediction).
24. **Joint P:** product only after the screen passes; flagged relations use a measured joint/product ratio; decisions use the
    lower bound of the joint interval.
25. **Same-game:** DISABLED. Measured joint ÷ product: Over 2.5 & BTTS 1.54, home win & Over 1.18, home win & BTTS 0.85.
    Future method is one scoreline model for all same-game markets.
26. **Cross-event:** 2 legs first, 3 max; **a multi multiplies edge or margin and never creates value** (three consensus-priced legs ≈ −8.7% EV).
27. **Exposure:** multi stake ≤ smallest leg single stake; one multi per leg; combined leg exposure; daily multi cap; max 1 multi/day initially; shared loss locks.
28. **Prediction Board:** every candidate by P, with interval, support, engine, context. No odds. Settled daily for calibration. `DAILY_OUTPUTS_SPEC.md`.
29. **Bet Card:** header counts, singles table, optional PAPER multi block, "NO BETS QUALIFIED TODAY" as a valid output.
30. **Promotion standard:** a 10-item research → PAPER checklist. `MODEL_PROMOTION_STANDARD.md`.
31. **Prospective standard:** ≥300 settled predictions in betting bands (or 8 weeks), calibration within historical CI,
    CLV ≥ 0 as the primary money test, automatic demotion.
32. **Phases:** 0 blueprint → 1 evidence plumbing → 2 registry + Prediction Board → 3 de-vig study → 4 tennis engine → 5 probability-first
    grading → 6 multis in PAPER → 7 breadth → 8 context → 9 money reviews. `V2_ROADMAP.md`.
33. **Tests:** 1,015 / 1,015 passing (re-run this session).
34. **Files:** `research/platform_v2/` (MASTER_OBJECTIVE, CURRENT_VS_TARGET, PROBABILITY_ENGINE_SPEC, BET_SELECTION_SPEC,
    MULTI_ENGINE_SPEC, DAILY_OUTPUTS_SPEC, MODEL_PROMOTION_STANDARD, CROSS_MARKET_RESEARCH_STATUS, NEXT_MARKET_AUDIT, V2_ROADMAP,
    RETURN_CHECKPOINT, CROSS_MARKET_*.csv/json, ODDS_API_ACTIVE_SPORTS json), `scripts/run_v2_cross_market_probability_audit.py`,
    Research Atlas v1.2.
35. **Commit:** see `git log` (the V2 blueprint commit).
36. **Production impact:** none. 0 Odds API credits spent (the sports list is free).
37. **Needs Fraser's approval:** (a) accept the blueprint; (b) **start Phase 1 (evidence plumbing)**, an additive,
    log-only change to the live scan that archives raw quotes, closing snapshots and three EV references and wires risk
    gates in log-only mode, with zero decision changes; (c) in parallel, allow research Cycle V2-1 (de-vig calibration), which is research-only.
