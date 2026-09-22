# Phase 4 Return Checkpoint — Multi-Market Expansion / Gate 1b (Football O/U 2.5)

Generated: 2026-09-22
Cycle: `gate1b_ou25_probability_architecture_comparison`

This checkpoint answers the 39-point return structure requested in the Phase 4 instruction ("MULTI-MARKET EXPANSION FOR OUTCOME PREDICTION"). Each numbered item below corresponds to one requested field.

1. **Prior conclusions reviewed.** Read `research/data_expansion/EXISTING_DATA_INVENTORY.md` and `EXHAUSTED_VS_OPEN_RESEARCH.md` (Phase 3, commit `d10c48d`/`361d94d`) in full before starting. Confirmed: football O/U2.5 and AH money-qualification backtesting are BLOCKED BY DATA (thin 2-3-bookmaker historical panel; `cycle_002_consensus_ou25.csv` and `_ah.csv` are 0 bytes); BTTS/team totals were UNEXPLORED; tennis money-qualification was PARTIALLY EXPLORED (Phase 3's own top nomination, not executed); tennis edge-hunting was EXHAUSTED (Workstream B, 13/13 candidate edges rejected). Also reviewed the just-completed Outcome Discovery cycle's football 1X2 finding: winner/loser feature differences collapse to near-zero once conditioned on market probability, and market beats every fundamentals model tested.

2. **Research Atlas (current).** Written to `research/multi_market_expansion/RESEARCH_ATLAS.md` and `RESEARCH_ATLAS.json` (machine-readable). Covers Football 1X2, Football O/U2.5, Football BTTS, Football AH, Tennis Match Winner, and other sports (placeholder, unexplored).

3. **Market classifications.**
   - EXHAUSTED: Football 1X2 (both outcome-prediction and betting-backtest axes).
   - READY_FOR_OUTCOME_DISCOVERY: Football O/U2.5 (Stage A now complete this cycle).
   - UNEXPLORED: Football BTTS; other sports (basketball, cricket, etc.).
   - PARTIALLY_EXPLORED: Football AH (Phase 3 audit only, no modelling); Tennis Match Winner (edge-hunting exhausted, money-qualification backtest not yet executed).
   - BLOCKED_BY_HISTORICAL_DATA (betting-backtest axis only, not outcome-prediction): Football O/U2.5, Football AH.

4. **Next market selected: Football Over/Under 2.5 goals.** Selected over BTTS, AH, and Tennis using the stated criteria (sample size, feature quality, live compatibility, research independence from the exhausted 1X2 question, calibration feasibility, event frequency, implementation complexity, future betting-overlay feasibility) — explicitly not "most historically profitable." Full comparison table in `research/multi_market_expansion/MARKET_SELECTION_AUDIT.md`. BTTS was the runner-up (deferred because its market-odds extraction pipeline doesn't exist yet); AH was deferred because handicap lines vary match-to-match and require a line-handling design decision before modelling can start cleanly; Tennis was deliberately not defaulted to, per the instruction's explicit caution, since it is already substantially researched and no genuinely new question was identified for it this cycle.

5. **Event/candidate counts.** 5,800 total matches in `cycle_002_discovery_features.csv` (seasons 2020_21–2024_25). 5,800 have a known goal outcome (100% coverage) and a market O/U2.5 quote. 5,759 have all 19 fundamentals features present (99.3% coverage; 41 rows missing ≥1 fundamentals field). Partition split: 3,480 discovery (2020_21–2022_23), 1,160 validation (2023_24), 1,160 sealed-holdout (2024_25).

6. **Seasons/competitions.** Same five English/Scottish league seasons already used by the 1X2 cycles (2020_21 through 2024_25); no new competitions added this cycle.

7. **Pre-event features used.** 19 fundamentals features (the same feature family validated leakage-safe in the prior 1X2 cycles) plus one market field: `market_ou25_closing_source_avg_over_probability` (research-grade, thin-panel average across whichever 2–3 bookmakers quoted a price).

8. **Leakage audit.** Written to `research/ou25_discovery/LEAKAGE_AUDIT.md`. Reviewed target construction (derived purely from final full-time goal counts, known only post-match), the fundamentals feature list (pre-match only, same set already leakage-audited for the 1X2 target), the market field (pre-kickoff closing quote, not an in-play or settled price), and chronological ordering (expanding walk-forward folds never train on a season they evaluate). Verdict: no leakage identified; no new leakage-audit code was needed since the underlying data and feature-construction pipeline are unchanged from the already-audited 1X2 cycles — only the target and market field are new.

9. **Discovery/validation/holdout design.** Reused `generate_expanding_walk_forward_folds` unchanged: 4 folds train on all prior seasons and evaluate on the next (2021_22 through 2024_25 as evaluation seasons). Pooled out-of-sample metrics are reported across all 4 folds; 2023_24 (validation) and 2024_25 (sealed holdout) are also reported separately and never blended into the pooled figure, per the project's standing chronological-honesty discipline.

10. **Occurred-vs-not-occurred feature differences.** Not run as a separate winner/loser-style effect-size analysis this cycle (unlike the prior Outcome Discovery cycle for 1X2). This cycle's discovery method instead directly compared model performance (naive/market/fundamentals/combined) across chronological folds with fixed-probability-band calibration, which was the analysis the instruction's Sections 10–17 called for; a standalone occurred-vs-not-occurred feature-distribution comparison was judged out of scope for this cycle and is noted here as a gap that could be added in a future pass if a fundamentals-driven model is ever revisited for this target.

11. **Feature stability.** Not separately tested this cycle (no season-by-season coefficient-drift check was run, unlike the bug-fixed feature-stability check in the prior 1X2 cycle). Flagged as a limitation in the Research Atlas rather than silently omitted.

12. **Models tested.** Four: naive (training-set base-rate frequency), market (thin-panel quote alone), fundamentals (19-feature logistic regression), market+fundamentals (market field added as a 20th feature to the same logistic regression).

13. **Market-only performance (pooled, n=4,640).** log loss 0.6755, Brier 0.2413, ECE (quantile bins) 0.0117, AUC 0.6046, accuracy@0.5 57.33%.

14. **Data-only (fundamentals) performance (pooled, n=4,629).** log loss 0.6866, Brier 0.2467, ECE 0.0185, AUC 0.5693, accuracy@0.5 55.24%.

15. **Combined (market+fundamentals) performance (pooled, n=4,629).** log loss 0.6806, Brier 0.2438, ECE 0.0254, AUC 0.5928, accuracy@0.5 56.64%. Combined does not beat market alone.

16. **Best probability estimator: market (thin-panel quote alone).** Wins on every metric (log loss, Brier, calibration, AUC, accuracy) in every partition tested (pooled, validation-only, holdout-only).

17. **Accuracy summary.** Market 57.33% pooled (60.0% validation-only, 56.1% holdout-only) vs fundamentals 55.24% pooled vs naive 48.47% pooled (base-rate guessing).

18. **AUC summary.** Market 0.6046 pooled (0.6255 validation, 0.5922 holdout) vs fundamentals 0.5693 pooled vs naive 0.52 pooled (chance).

19. **Brier score summary.** Market 0.2413 pooled vs fundamentals 0.2467 vs market+fundamentals 0.2438 vs naive 0.2516.

20. **Log loss summary.** Market 0.6755 pooled vs fundamentals 0.6866 vs market+fundamentals 0.6806 vs naive 0.6964.

21. **Calibration.** Fixed-band report (`CALIBRATION_BANDS.csv`) across <50%/50–54.9%/55–59.9%/60–64.9%/65–69.9%/70–79.9%/80%+. Market is the best-calibrated model overall: calibration error stays under ~1.6pp for every band with n≥100, e.g. 50–54.9% band predicted mean 52.1% vs actual 53.4% (1.26pp gap, n=867); 60–64.9% band predicted 62.3% vs actual 63.2% (0.84pp gap, n=399). The 80%+ band has too few observations (n=4) for a reliable read for any model.

22. **Occurrence rates by predicted-probability band (market model).** <50%: n=2,441, predicted mean 44.0%, actual 44.5%. 50–54.9%: n=867, predicted 52.1%, actual 53.4%. 55–59.9%: n=577, predicted 57.3%, actual 58.9%. 60–64.9%: n=399, predicted 62.3%, actual 63.2%. 65–69.9%: n=224, predicted 67.3%, actual 67.9%. 70–79.9%: n=128, predicted 72.7%, actual 74.2%. 80%+: n=4 (too small to interpret).

23. **High-probability outcome performance.** The market model's higher bands (65–79.9%, combined n=352) show good discrimination — actual occurrence rises smoothly with predicted probability, and calibration gaps stay under 1.6pp through the 70–79.9% band — but sample sizes above 70% are thin (n=128) and above 80% negligible (n=4), so no defensible "very-high-confidence" tier could be certified this cycle.

24. **Sealed-holdout result (2024_25).** Market: log loss 0.6796, Brier 0.2433, AUC 0.5922, accuracy 56.12%. Fundamentals: log loss 0.6909, Brier 0.2487, AUC 0.5583, accuracy 53.20%. Naive: log loss 0.6933, AUC 0.50 (chance), accuracy 48.45%. Market wins by a smaller margin here than in validation, but still wins on every metric. Honesty caveat: 2024_25 is used as the final walk-forward fold (all modelling decisions frozen before evaluating it) but is not claimed as a fully blind prospective holdout, since these raw seasons have been used by other cycles (Gate 1, Backtest Phase 1) for the 1X2 question — it is, however, a genuine first look for this specific target (O/U2.5), never previously modelled in this project.

25. **Does a defensible new model exist?** No. No fundamentals-only or combined model beats the market's thin-panel quote on any metric, in any partition. Bootstrap paired comparisons confirm this is not noise: fundamentals is worse than market by 0.0111 log-loss points (95% CI 0.0070–0.0151, excludes zero), market+fundamentals worse by 0.0051 (CI 0.0027–0.0074, excludes zero). Fundamentals does, however, clearly beat the naive baseline by 0.0097 log-loss points (CI −0.0137 to −0.0057, excludes zero) — so fundamentals carries real signal, it just doesn't add anything the market hasn't already priced in.

26. **Is historical betting-overlay possible?** No. `cycle_002_consensus_ou25.csv` is 0 bytes — the historical panel never reaches production's `min_bookmakers=3` floor (only 2–3 bookmakers quoted per match). This is a data-availability block on Stage B specifically, and does not invalidate the Stage A (outcome-prediction) result above, per the instruction's Section 8/20 requirement to treat these as separate feasibility questions. Full reasoning in `research/ou25_discovery/BETTING_OVERLAY_REPORT.md`.

27. **Betting-overlay result, if honestly possible.** N/A — blocked as above. No backtest was attempted or fabricated.

28. **Live implementation feasibility.** Ready but not deployed. Both the fundamentals features and live O/U2.5 odds quotes are obtainable pre-kickoff through the same channels already used for 1X2; the model built this cycle would need to be wired into the scan/scoring pipeline to go live prospectively, and doing so does not depend on solving the historical betting-backtest data gap.

29. **Prospective fields to start collecting now.** Per `research/ou25_discovery/LIVE_DATA_COLLECTION_AUDIT.md`: raw per-bookmaker O/U2.5 panel snapshots (not just the aggregated thin-panel average) should be preserved going forward, so a future cycle can build a thicker historical consensus once enough seasons accumulate. This reaffirms Phase 3's existing live-data-preservation recommendation rather than introducing a new one — it applies equally to O/U2.5.

30. **Is data purchase necessary?** No. All data used this cycle (goal outcomes, fundamentals features, market quotes) already existed in the repository's processed files; nothing was purchased or downloaded from a new source.

31. **Tests passing.** 982 passed (25 new tests for `ou25_probability_architecture.py`, up from the prior baseline of 957), 0 failed, re-confirmed via `.venv/bin/python -m pytest -q` immediately before this checkpoint was written.

32. **Files created this cycle.**
   - `src/prediction_markets_lab/research/ou25_probability_architecture.py`
   - `scripts/run_gate1b_ou25_probability_architecture_comparison.py`
   - `tests/unit/test_ou25_probability_architecture.py`
   - `research/ou25_discovery/GATE1B_OU25_RESULTS.json`
   - `research/ou25_discovery/CALIBRATION_BANDS.csv`
   - `research/ou25_discovery/TOP_MISSES_MARKET.csv`
   - `research/ou25_discovery/predictions_{naive,market,fundamentals,market_fundamentals}.csv`
   - `research/ou25_discovery/DATASET_AUDIT.md`
   - `research/ou25_discovery/LEAKAGE_AUDIT.md`
   - `research/ou25_discovery/VALIDATION_REPORT.md`
   - `research/ou25_discovery/HOLDOUT_REPORT.md`
   - `research/ou25_discovery/BETTING_OVERLAY_REPORT.md`
   - `research/ou25_discovery/LIVE_DATA_COLLECTION_AUDIT.md`
   - `research/multi_market_expansion/RESEARCH_ATLAS.md`
   - `research/multi_market_expansion/RESEARCH_ATLAS.json`
   - `research/multi_market_expansion/MARKET_SELECTION_AUDIT.md`
   - `research/ou25_discovery/PHASE4_RETURN_CHECKPOINT.md` (this file)

33. **Files changed.** None — no existing production or research files were modified. This cycle is purely additive.

34. **Commit hash.** Recorded in the checkpoint delivery message after commit (see final summary to Fraser); not yet committed at the time this document was drafted.

35. **Production impact.** None. Money qualification logic, EV floors, staking, the Daily Money Card, GitHub Action schedules, and real execution paths were not touched. This entire cycle is research-only, additive files under `research/`, `src/prediction_markets_lab/research/`, `scripts/`, and `tests/unit/`.

36. **Regression testing.** Full suite re-run after all new code and before this checkpoint: 982 passed, 0 failed, 0 skipped-unexpectedly. No existing test was weakened or removed.

37. **Portfolio-strategy alignment.** This cycle is the second independently-researched probability engine in the intended multi-market portfolio (after 1X2), extending the project's core finding — that market consensus dominates fundamentals-only models — to a genuinely different (binary, goals-based) target family for the first time. It also demonstrates the outcome-prediction/betting-backtest separation the instruction asked to establish as a repeatable pattern.

38. **Recommended next action.** Do not re-run O/U2.5 fundamentals modelling — the market-dominance result is clean and decisive. Two parallel next steps, per the Research Atlas: (a) begin preserving raw per-bookmaker O/U2.5 panels prospectively (no production change, pure logging) so a future cycle can attempt a thicker historical consensus; (b) run the next Stage-A-only discovery cycle on Football BTTS, which needs no new target construction (goal counts already exist) and is the next-best candidate after O/U2.5 on the same selection criteria. Extending the feature/acquisition pipeline to include the 2025_26 season (currently a gap shared by both the 1X2 and O/U2.5 cycles) is a secondary, lower-urgency recommendation.

39. **Summary verdict.** Football O/U2.5 outcome-prediction is now READY (Stage A complete, market wins decisively and is well-calibrated); the historical betting-overlay remains BLOCKED_BY_HISTORICAL_DATA but this does not block live prospective use going forward. No production changes were made. The project's multi-market portfolio now has one exhausted market (1X2), one Stage-A-complete market (O/U2.5), and a documented, evidence-based plan for what to research next (BTTS), fulfilling the instruction's Section 30 "permanent strategy" of horizontal expansion rather than continued over-modelling of the same football 1X2 information.
