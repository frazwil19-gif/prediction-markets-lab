# Direction record — 7 October 2026 (Fraser + ChatGPT; approved with amendments)

**North star:** Prediction Markets Trading is a multi-sport quantitative prediction and bet-selection platform. It
automatically scans the day's sporting events, estimates the probability of relevant outcomes using validated
sporting, contextual and market information, ranks the strongest predictions by probability and confidence, then
evaluates available odds, payout and risk to produce a disciplined Daily Bet Card.

This restates `MASTER_OBJECTIVE.md` (23 Sep), which already put outcome prediction first. In practice, research had
drifted to edge-first work ("prove the market is inefficient before predicting it"). That emphasis is now
**superseded**:
- research asks "can we predict this outcome accurately before the event?";
- price, EV and risk decide bets afterwards.

Frozen experiments (Corners A/B/C, Player SOT cycle 2, Track A H1/H2/H3/H7, 10 Oct probe and Betfair windows)
continue unchanged under their pre-registrations.

## Approved order of work
1. Verify the API-Football data, then continue SOT cycle 2 as pre-registered.
2. Unified Daily Prediction Board V1 from existing engines.
3. Corners and team SOT as clearly marked research predictions:
   - fair odds plus "RESEARCH — NOT MONEY ELIGIBLE";
   - no "bet if ≥ X" instruction until promoted.
4. One Daily Bet Card underneath. Sections: best predictions → best bets → strong predictions with too low a price →
   research.
5. Private live ledger and deposits ledger.
6. Fresh-price infrastructure (staleness, Matchbook/Smarkets commission).
7. 10 Oct experiments as planned.
8. Open the SOT holdout only when acquisition is complete and the frozen spec exists.
9. Decide on £1 manual live bets.
10. Expand prediction families by predictability and candidate volume.

## Betting policy decisions
- **Bet rule:** bsv2-4 stays the bet rule for V1 (P ≥ 0.50, net EV ≥ +2%, clean fresh price). +2% is not a permanent
  law. EV > 0 with uncertainty-adjusted rules may be evaluated later, never tuned from small samples.
- **Stakes:**
  - £1 default on a £50 bankroll;
  - £2 only under a future quantitatively justified, approved rule (no confidence-based doubling);
  - £5 daily exposure cap;
  - one bet per event.
- **Real money:** OFF until Fraser explicitly activates it. Fraser places every bet manually.
- **Preferred profile** (preference, not a filter):
  - 55–70%+ probability, many bets around decimal 1.5–2.0 when available;
  - a realised win rate must emerge from calibration, never be manufactured.

## Controlled live phase (approved 2026-10-07, Fraser + ChatGPT)
- Manual only. A live bet requires both bsv2-4 PAPER_BET and `money_eligible=true` in the engine registry. Today that
  means `football_1x2.market_consensus` and `football_ou25.market`. Tennis engines are VALIDATED_HISTORICAL but not
  money-eligible in the registry; their PAPER_BET rows show as "PAPER ONLY" until that flag is changed by a separate,
  explicit decision.
- £1 per qualifying bet; £5 per day; one bet per event; £2 disabled. Research and provisional rows stay at £0.
- Private live ledger: the "Fraser's Bet Log" artifact (owner-only; not in the public repo). It records bookmaker,
  card odds, odds taken, time, stake and result.
- Player SOT frozen until the one-time holdout. Team SOT cycle 1 = NOT_CONFIRMED; a calibration follow-up will be
  separately pre-registered.

## Fresh-price findings (evidence, 7 Oct)
- At bsv2 evaluation time prices are fresh (median age 0.2 min). The latest 45 candidates were rejected mainly for
  NET_EV_NOT_POSITIVE (44), then PREDICTION_NOT_VALID (14) and EXCHANGE_SPREAD_TOO_WIDE (9). Only 1 was PRICE_STALE
  and 0 were COMMISSION_UNKNOWN.
- So stale prices are not what blocks bets at decision time. The staleness seen on the first card came from building
  it in a later run.
- What GitHub's lateness does cost is timing. Morning scans run 5–9 h late (07:00 cron → 12:00–15:40 UTC; tennis
  06:30 → 11:50–15:10 UTC), so the card often appears after Fraser's useful window or near kickoff.
- Fix: a Mac dispatcher (`scripts/setup_dispatcher_mac.sh`) triggers the scans at 07:15 and 16:15 UK. The cron stays as
  a fallback, and `scripts/recent_run_guard.py` skips a late duplicate so credits are not spent twice.
- Matchbook commission stays `null` (unknown → rejected). Public sources were not authoritative, and Matchbook did not
  appear among recent best quotes. No price-quality rule changed.

## 2026-10-08 (Fraser approval)
- **Tennis ATP/WTA and NBA moneyline are now money-eligible** (registry). NBA applies from season start (20 Oct).
  bsv2-4 PAPER_BET is still required for any live bet.
- **Big Card (multi):**
  - shown only when ≥ 3 independently qualifying, money-eligible legs on different events exist (max 5);
  - joint P = product of leg P;
  - placed only if the bookmaker's acca price ≥ (1.02 / joint P);
  - £1, counted inside the £5 daily cap.
- **Next sports:** NHL and NFL consensus engines, validated historically on free MIT-licensed SBR archives
  (2011–2021, closing moneylines) before any live use.


## 2026-10-08 consolidated operating directive (13:02) — implemented items
- NFL → `live_tier: PROVISIONAL_LIVE` (registry status unchanged, still bsv2-4 gated): £1, max 1 live bet/day, no Big Card
  legs. Pre-registered promotion/demotion rule: `nhl_nfl/NFL_PROMOTION_RULE.md`. NHL unchanged (paper only).
- Card `card-v1.1`: rejection-reason summary; decision record fields (engine_version, decision_evaluated_at, source
  bookmaker/price, min bookmaker odds); explicit "strong / price too low rows are NOT live — do not manually rescue".
- Manual bookmaker shopping applies ONLY to BEST BET rows: accept any bookmaker at ≥ the card's min odds
  = max(1.33, 1.02/P). Rejected rows are never rescued; prices seen on them may be noted as research only.
- Reports: `reports/qualified_capacity.{md,json}` (QTC, expected profit/wins vs realised, rejection categories,
  bankroll scenarios — illustrative only); credit utilisation review section in `reports/credit_report.md` (advisory).
- Production freeze 10–11 Oct: no registry/threshold/model change; any later change is versioned.
- Future research (recorded, not started): dependency between different-event Big Card legs (same-league/same-day
  shocks, shared-price-source errors) — Big Card currently assumes independence; joint P = product.
- Scaling criteria (draft, not active): consider raising stake above £1 only after ≥ 100 settled LIVE bets with
  realised profit ≥ 0, positive mean CLV with 95% CI excluding 0 or ≥ 200 bets, and probability KPIs within calibration
  tolerance — requires Fraser's approval and a pre-registration.
