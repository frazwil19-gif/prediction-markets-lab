# Layer B — Bet-Selection Engine Specification (design, not implemented)

Input: a Layer A prediction plus current quotes. Output: BET / WATCH / PAPER_ONLY / REJECT, reasons, and a stake.

## Order of checks (every failure recorded, not just the first)
1. **Prediction eligibility:** the engine is registered and validated; support ≥ ADEQUATE; p_interval width ≤ a configured max;
   data quality OK; no unresolved material warning. Failing here gives PAPER_ONLY (a prediction is still logged).
2. **Timing:** kickoff inside the money window (existing 24h gate, unchanged); quotes fresh (existing staleness gate).
3. **Probability floor:** existing `money_qualification` floors (0.50 / 0.60), unchanged. V2 applies them to the
   *lower* end of p_interval as a later, separately approved change, not now.
4. **Payout:** existing payout policy (1.33 floor, 1.40–2.50 preferred), unchanged.
5. **Value against a reference independent of the priced book:** log EV against inclusive consensus (current),
   leave-one-out, and exchange/sharp. The existing EV floors apply to the current method until prospective data
   shows which reference predicts realised return and CLV (Phase 5 R1–R3).
6. **Risk:** exposure and loss-lock gates (existing modules, to be wired in); no duplicate exposure; correlated
   positions are counted together (same match, same team).
7. **Stake:** existing fixed £-by-grade staking. Fractional Kelly only after probability quality is validated
   prospectively (V2 §43), and on the lower end of p_interval.

## Outcomes
- **BET:** all checks pass.
- **WATCH:** prediction strong, but price fails payout or value (for example, 82% at 1.15). Logged as "strong prediction, poor
  bet", which is useful for the multi pool.
- **PAPER_ONLY:** prediction support thin, or a research-stage engine.
- **REJECT:** fails prediction eligibility or risk.

## Grades
Grade follows the V2 hierarchy: probability tier × support × uncertainty. Value is a gate, not the ranking key. The
old EV-based grade is kept as `research_grade` so all history stays comparable.
