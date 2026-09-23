# Phase V2-2 — ATP Prospective Engine + WTA Match Winner + Betfair Delayed Audit: Return Checkpoint (2026-09-23)

**Workstream A: ATP prospective (paper)**
1. **ATP prospective engine:** BUILT and LIVE-TESTED. The protocol was frozen before the first live prediction
   (`tennis_prospective/ATP_PROSPECTIVE_PROTOCOL.md`, commit `0783361`). Code: `src/prediction_markets_lab/tennis_prospective/`
   (engine, ledger, settlement, performance, board), `scripts/run_tennis_prediction_board.py`,
   `scripts/run_tennis_settlement.py`, `.github/workflows/tennis_prediction_board.yml` (runs once pushed).
2. **Odds API tournaments (provider docs):** ATP Slams, 1000s and 500s (AO, RG, Wimbledon, USO, IW, Miami, MC,
   Madrid, Rome, Canada, Cincinnati, Shanghai, Paris; Barcelona, Halle, Queen's, Hamburg, Washington, Dubai, Qatar,
   China Open, Munich); WTA Slams, 1000s and 500s. Keys exist only while the tournament runs (today: 1 key, WTA Singapore).
3. **Probability source:** `betfair_ex_uk` back + lay midpoint → two-runner proportional normalisation (EXCHANGE_MID).
   Back-only is a flagged fallback. Bookmaker consensus is RESEARCH_ONLY. Otherwise no prediction.
4. **Compatibility:** close to, not identical to, the historical estimator (exchange quote midpoint vs last-traded
   price; scan time vs T−30 min). Historical evidence that earlier snapshots stay calibrated (ATP 2021–23, exposed):
   ≥80% at 6 h 87.2 → 87.6%, 1 h 87.2 → 87.9%, 30 min 87.2 → 88.0%. Equivalence is **tested prospectively, not assumed**.
5. **Credits per scan:** 0 for discovery plus 1 per active key (verified: first call cost exactly 1; lay prices were included).
6. **Projected monthly:** about 60–240 tennis credits (2 scans/day × 0–4 active keys). Guard at 150 remaining protects football.
7. **Board:** `tennis_predictions/<date>/board_<HHMM>.{md,json}`; ranked by validated P; shows the engine's unseen-data hit rate for each band.
8. **Ledger:** `tennis_predictions/ledger_predictions.csv`, append-only with a byte-prefix immutability guard; first snapshot is canonical; id = sha256(engine@version|event).
9. **Settlement:** free TennisCourtLog 2026 results (ATP and WTA; TML's GitHub stopped updating in Jan 2026). Retirements count, W/O → VOID, never guessed; a separate append-only file.
10. **Maturity rules (fixed before results):** COLLECTING < 50 settled · EARLY 50–299 · INTERMEDIATE ≥ 300 and ≥ 100 at P ≥ 80% · MATURE ≥ 1,000 and ≥ 300 at P ≥ 80%.
11. **First predictions (2026-09-23, WTA Singapore, all EXCHANGE_MID):** Gibson 90.9% · Sakkari 83.6% ·
    Eala 79.5% · Wang 75.3% · Andreeva 70.6% · Mertens 64.8%. No ATP tournament was active today (ATP China Open
    / Shanghai keys should appear when those events open).
12. **No money:** paper only. No stakes, no bankroll change, no Money Card, no BET/WATCH language.

**Workstream B: WTA**
13. **Data:** TennisCourtLog WTA results (Sackmann-derived to 2024, tennis-data.co.uk-derived from 2025; CC BY-NC-SA)
    + Fraser's Betfair archive (169,062 singles markets re-extracted). TML WTA itself is blocked by the allowlist.
14. **Seasons:** 2021–2025 evaluated; 2018–20 Elo warm-up.
15. **Matches:** 10,352 with fresh two-sided prices (dev 6,013 · holdout 4,339). Non-walkover results 2021–25: 12,973.
16. **Surfaces (holdout):** Hard 2,766 · Clay 1,029 · Grass 544.
17. **Betfair coverage:** MATCHED 83–93% per year (2025 highest); fresh-priced 78–89%.
18. **Holdout:** genuinely untouched (WTA never analysed). Protocol `95f91cc` and script `dd2ecd0` committed before opening once.
19. **Best estimator:** Betfair market (proportional).
20. **Accuracy:** 66.8% (expected 67.8%).
21. **Brier:** 0.2063.
22. **Log loss:** 0.5967.
23. **Calibration:** slope 0.979 [0.900, 1.063]. The multiplicity-aware band rule **passed**.
24–31. **Holdout thresholds (n, share, pred → actual):** ≥60 2,967 · 68.4% · 73.5 → 73.0 | ≥65 2,263 · 52.2% · 77.0
    → 77.3 | ≥70 1,704 · 39.3% · 80.1 → 80.0 | ≥75 1,191 · 27.4% · 83.4 → 83.2 | **≥80 768 · 17.7% · 86.9 → 87.0**
    | ≥85 430 · 9.9% · 90.4 → 91.4 | ≥90 217 · 5.0% · 93.5 → 93.5 | ≥95 59 · 1.4% · 96.6 → 100.
32. **Band table:** `wta/WTA_PROBABILITY_BANDS.csv` (summarised in `wta/WTA_RETURN_CHECKPOINT.md`).
33. **ATP vs WTA:** both validated. ATP is slightly sharper and more stable (slope 0.986 vs 0.979; ≥80% share 19.8%
    vs 17.7%). WTA has a wider year swing at ≥80% (91.0 / 83.5) and a weak grass signal (77.9%, n = 95), both flagged
    for monitoring. **WTA becomes the second tennis probability engine.**

**Workstream C: Betfair Delayed**
34. **Terms (official):** for development and functional testing; the delayed key, not the Live key, for read-only collection.
35. **Cost:** delayed free; Live **£499** one-off (updated 12 Sep 2026). Not purchased.
36. **Auth:** self-signed 2048-bit certificate uploaded to the account, username/password, `X-Application` app key, certlogin; UK sessions 24 h with Keep Alive.
37. **GitHub automation:** **not feasible on hosted runners.** Betfair auto-blocks API requests from restricted
    regions, **including the USA**. Local-only (Fraser's Mac) or a paid UK runner.
38. **ATP coverage:** Odds API ≈ Slams/1000/500 (61% of historical ATP ≥80% predictions); Betfair: all.
39. **WTA coverage:** Odds API: Slams, 1000, 500; Betfair: all.
40. **Recommended live source:** The Odds API now; Betfair Delayed as a later local complement for 250s/Challengers.
41. **Decision: A** — The Odds API is sufficient for initial prospective validation.

**Wrap-up**
42. **Atlas:** v1.4. WTA VALIDATED; ATP and WTA prospective COLLECTING; live-source decision; Basketball ML entry added.
43. **Next family: Basketball Moneyline (NBA)**, starting with a Stage-0 data audit. Most compatible free route: a
    Betfair BASIC basketball archive (the same pipeline as tennis; Fraser would download it, as he did for tennis).
    Alternatives: SBR/Kaggle odds archives (reachability through the allowlist unverified). NBA is live on the Odds API
    from October. A genuinely different sport, per the operator's preference.
44. **Tests:** **1,094 / 1,094** (1,077 + 17 new).
45. **Files:** `research/platform_v2/tennis_prospective/*`, `research/platform_v2/wta/*`, `config/tennis_engine_registry.json`,
    `src/prediction_markets_lab/tennis_prospective/*`, tests, 4 scripts, 1 workflow, `data/interim/v2_wta_*.csv`,
    WTA SHA256SUMS, `tennis_predictions/` (first board, ledger, credit log), Atlas.
46. **Commits (in order):** `95f91cc` WTA protocol/data → `dd2ecd0` WTA holdout script → `0783361` tennis
    prospective protocol + code → final V2-2 commit (WTA results, first live board, reports, Atlas). No squashing.
47. **Production impact:** none to football/Money Card/ledgers/thresholds. A new additive workflow
    (`tennis_prediction_board.yml`) activates when pushed; it shares the production concurrency group and a credit
    guard. 2 API credits spent this phase.
48. **Needs Fraser:** (a) push (this activates the paper tennis workflow); optionally run it once by hand
    (Actions → tennis_prediction_board → Run workflow → board). (b) Approve the Basketball Moneyline Stage-0 audit;
    if the Betfair route is chosen, download the free Betfair BASIC basketball history the same way as the tennis archive.
    (c) Optional, not needed now: create a Betfair *delayed* app key + certificate locally if you want the
    full-coverage tennis complement later. Don't buy the £499 Live key.
