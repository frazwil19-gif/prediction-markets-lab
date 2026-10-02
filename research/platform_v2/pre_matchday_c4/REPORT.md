# Pre-matchday progress (2026-10-02): 10 October is a checkpoint, not a pause

- Branch: `pre-matchday-c4`, commit `8e0213e`. Not merged; needs approval. Merging will use `scripts/safe_merge.sh`.
- Tests: 1343 passed. Branch CI passed.
- Scope: research only. No production change. No API credits used.

## A. Completed now
1. **Betfair `--discover` mode.** One command that needs no fixture hunting:
   ```
   python3 scripts/betfair_catalogue_audit.py --discover
   ```
   - It picks the 25 busiest football events within 36 hours, in any competition.
   - It records every marketTypeCode it finds, with names, runner structures, hours to kickoff, two-sided share and
     spread.
   - This is schema discovery only. It is NOT coverage evidence for the project's leagues.
   - Read-only, tested.
2. **Player SOT data:**
   - Source: the openly licensed **Wyscout public dataset** (CC BY 4.0; 2017-18; EPL, LaLiga, Serie A, Bundesliga,
     Ligue 1). It was acquired in GitHub Actions; no account was needed.
   - **Data gate PASSED:**
     - 1,826 matches and 40,172 starter observations;
     - exactly 11 starters in every team-match;
     - no duplicates or SOT/goal violations;
     - SOT per match within 1–3% of Football-Data in every league.
   - Starter base rates: P(1+ SOT) 24.8% and P(2+) 6.8%. By role, FW 54.6% / 22.2%, MD 29.3%, DF 11.7%.
3. **Player SOT pilot** (pre-registered `487d21a`, frozen `FROZEN_SPEC.json`, holdout opened once). **PILOT_SIGNAL.**
   - Holdout: March–May 2018, 10,780 starter-matches.
   - Model: sports-only logistic regression.

   | Target | Model A log loss | Best baseline log loss | Δ [95% CI] | Calibration slope / intercept |
   |---|---|---|---|---|
   | 1+ SOT (primary) | 0.4968 | 0.5129 | −0.0161 [−0.0198, −0.0126] | 1.00 / 0.02 |
   | 2+ SOT | 0.2107 | 0.2175 | −0.0068 [−0.0094, −0.0043] | 0.97 / −0.01 |

   - The 1+ SOT result holds in all 5 leagues and is largest for forwards (−0.030).
   - **Limits:**
     - one historical season;
     - the best baseline is itself miscalibrated (slope 0.82);
     - **no market comparison.** Exchange prices will already encode player usage.
4. **Player SOT pipeline** (`research_shadow/player_sot.py`):
   - canonical schema and audit;
   - targets;
   - leakage-safe prior features, tested to use only earlier matches;
   - chronological splits and baselines;
   - evaluation and a one-shot holdout guard;
   - `data/private/` is gitignored for restricted data such as API-Football.
5. **Corners A/B/C analysis** (`research_shadow/corners_abc.py`) implements the pre-registered rules end to end:
   - quote quality rules;
   - main-line selection;
   - capture at least 60 minutes before kickoff;
   - Model A must be computed before the capture;
   - model C stacking fitted on the first 150 events, then frozen;
   - staged evaluation (COLLECTING / INTERIM / CONFIRMATORY).

   It is tested and waits only for a quotes file.

## B. What genuinely waits for matchday (10 October)
- Coverage of corners, bookings and player markets for the EPL and the other project leagues on Betfair, measured
  within 36 hours of kickoff.
- The approved Odds API corners/cards probe, scheduled at T−8h.

## C. Betfair schema discovery before 10 October
- **Can it be advanced?** Yes. `--discover` can run as soon as there are busy football events within 36 hours, such
  as this weekend's lower or other leagues, or international fixtures.
- **Who runs it:** Fraser runs it on the Mac, because GitHub runners are blocked by Betfair.

## D. API-Football
- **Who must act:** support is only reachable through the API-Football dashboard (`dashboard.api-football.com`),
  which needs a free account that Fraser creates.
- **Where to send the question:** through that dashboard's support.
- **Still needed, though less urgent:** current-season data would need API-Football (or similar) for a live engine.
  The openly licensed Wyscout data covers the pilot question without it.

## E. Clearer free source
Yes: the Wyscout public dataset (CC BY 4.0). Its limitation is that it is one season, 2017-18 only.

## F–I. Status and next decisions
| Item | Status | Next decision |
|---|---|---|
| Player SOT pipeline | Ready | — |
| Corners collector | On master, daily; no top-flight fixtures until next week | — |
| Corners A/B/C | Analysis ready | Needs a quote source |
| Track A, tennis paper, settlement | Unchanged, running | — |
| Corners | Price source | Does Betfair or the Odds API price two-sided corners near kickoff? (10 Oct) |
| Player SOT | Current-season source plus a market check | Licensing (API-Football) and Betfair player-SOT coverage, then a current-season Model A cycle vs Betfair consensus |
| Next family | If capacity allows | Player goalscorer: the same pipeline and data (goals target); Betfair "To Score" markets are known to exist. Do not start before SOT's market check |
