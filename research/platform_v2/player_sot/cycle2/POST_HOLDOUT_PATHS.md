# Player SOT cycle 2: post-holdout paths (decided 2026-10-08, BEFORE the holdout opens)

The sealed holdout (2023/24 + 2024/25) stays untouched until the planned single opening around 13 Oct. The verdict
comes from the pre-registered rule in `FROZEN_SPEC.json` / `IMPLEMENTATION_ADDENDUM.md`, and nothing here changes it.

This file fixes what happens **after** each verdict, so the result cannot shape the plan.

## FAIL
1. Record the result, keeping `HOLDOUT.json` and the verdict, and add it to the negative-results registry. No
   retuning, no re-run, no new feature set on the same holdout.
2. Stop the live-development path for player props (the whole family pauses).
3. **Kept (reusable):**
   - API-Football ingestion plus the private data layout;
   - the name/club mapping and the "Nottm Forest"-style alias lessons;
   - HoldoutGuard and the pre-registration templates;
   - the Betfair market-matching code from the 10 Oct windows, for corners;
   - the minutes data, archived privately.
4. **Next #1 independent direction:**
   - corners Model B/C, **if** the 10 Oct Gate 0 = A (robust) and the decision rule in
     `research/platform_v2/props_c1/corners/DECISION_RULE_2026-10-08.md` says GO;
   - otherwise the tennis cross-market games model, **if** probe C3 shows UK games markets (see
     `research/platform_v2/tennis_serve_return/LICENSING_AND_FEASIBILITY.md`);
   - otherwise NBA line dispersion, if probe C3 passes.

## MIXED
MIXED means the pre-registered verdict is not a clean pass, e.g. calibrated but not beating the comparator, or
unstable across the two chronological halves.
- No live betting and no retuning.
- **Prospective paper study, pre-registered before any prospective data:**
  - frozen spec;
  - post-lineup predictions for every EPL fixture;
  - Betfair back and lay recorded at T−30 and T−5 for each player-SOT market.
- **Analysis:**
  - single look at N = 400 player-markets (about 2–3 months of EPL);
  - compare A (model) vs B (market-implied) vs C (blend);
  - primary: C beats B, Δlogloss 95% CI < 0;
  - secondary: calibration slope CI contains 1.
- **Reconsider for a VALIDATED-style path only if** both of those hold **and** Betfair liquidity meets the
  VALIDATED criteria below.

## VALIDATED (strict sequence; each step a gate)
1. **Market comparison.**
   - Use A/B/C on Betfair historical BASIC if player-SOT markets are in the files (unverified); otherwise
     prospectively (as in MIXED, N = 400).
   - The model must beat or complement B.
2. **Current-season data source.**
   - The free API-Football tier has no current season, so options are its paid tier or another licensed provider.
   - **Fraser decides; the cost is not verified here.** Kill if the cost is above BASE first-year profit at £1–£5.
   - Build the as-of-date feature pipeline with a leakage guard.
3. **Lineup / expected minutes.**
   - Post-lineup model first: confirmed starter → E[minutes | starter].
   - A pre-lineup P(start) model is deferred.
4. **Betfair market mapping.**
   - Map player to selection id per fixture.
   - Unmapped players are logged, never guessed.
5. **Liquidity** (over 4 weekends):
   - median back/lay spread ≤ the bsv2 spread gate;
   - ≥ £2 available at the decision price on ≥ 50% of candidate markets;
   - else kill.
6. **Execution timing.**
   - Fixture-driven runs at T−70 to T−20 from the Mac dispatcher; GitHub cron is unusable for this.
   - Betfair Exchange account (Fraser), with commission in net EV.
7. **Paper → live.**
   - ≥ 150 prospective predictions and ≥ 6 weeks;
   - calibration slope CI contains 1;
   - mean fair-CLV vs Betfair close ≥ 0 (point estimate) with no significant negative.
   - Then registry `live_tier: PROVISIONAL_LIVE`: £1, ≤ 1 per day, no Big Card. Promotion and demotion rules are
     pre-registered in the same style as NFL.

## Family potential (PROJECTED; EPL only; nothing assumed viable)
| Market | UK price route | Candidates/month at P ≥ 0.5 | Status if SOT validates |
|---|---|---|---|
| Player SOT 1+ | Betfair EPL Grade-1 | 80–160 | first market |
| Player SOT 2+ | Betfair | 10–30 | +1 week, own holdout |
| Player shots 1+/2+ | **none found** (price-blocked) | 250–400 if prices appear | REJECT until a UK price exists |
| Goalscorer | Betfair To Score | < 20 (the P ≥ 0.5 floor binds; the "No"/lay side is a separate research question) | DEFER |
| GK saves 3+ | Betfair (top tier) | 20–40 | +2 weeks, own holdout |

- **Unique-event ceiling:** about 40 EPL matches a month under the one-bet-per-event rule.
- So the family's qualified ceiling in the EPL is about 40 a month, whatever the candidate count.
- Going above that needs Betfair coverage of other leagues (unverified) or a dependency-analysed change to the
  per-event rule. SOT and match-result dependency ratio = 1.25 (measured).
- **Family qualified estimate** (P): LOW 0 / BASE 8 / HIGH 30 a month.
