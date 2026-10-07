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
