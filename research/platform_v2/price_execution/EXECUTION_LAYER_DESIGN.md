# Price / execution layer — design (reusable, research module)

Module: `src/prediction_markets_lab/research_shadow/execution.py`. Tests: `tests/unit/test_execution_layer.py`.
Not wired into production. bet_selection_v2 keeps its frozen logic; this is the common interface that future engines
(corners, player SOT) will use.

## Pipeline
prediction p (with lower bound p_lo)
→ fair odds 1/p
→ quotes (venue, side, back, lay, observed_at, is_exchange)
→ quality filters: stale or untimed quote, odds < 1.01, exchange spread above policy, unknown commission
→ consensus probability: median of per-venue proportional de-vig over venues quoting every side (exchange uses the
  back/lay mid)
→ best executable net odds: max over valid venues; exchange net = 1 + (o − 1)(1 − c)
→ central EV = p · o_net − 1
→ uncertainty-adjusted EV = p_lo · o_net − 1
→ decision (outside this layer)

## Invariants
- Every quote is kept, as either used or excluded-with-reason.
- MARKET_CONSENSUS, BEST_EXECUTABLE and DECISION are separate fields. `decision_price` is only ever set by a
  separate decision step.
- Unknown commission means the venue is not executable. It is never assumed to be zero.
- One-sided quotes never enter consensus, and a missing side is never manufactured.

## Worked example (from the directive; a unit test)
- Inputs: P = 0.64, so fair odds = 1.5625. Book A 1.50, Book B 1.58, Book C 1.63, Betfair back 1.705 at 5%
  commission (net about 1.670).
- Result: best executable venue = Betfair, net 1.670, central EV = 0.64 × 1.670 − 1 ≈ +6.9%.
- The consensus probability is reported separately from the venues that quote both sides.
