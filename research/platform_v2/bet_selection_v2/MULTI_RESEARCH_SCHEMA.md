# V2-6 Multi Research Schema (pre-registered 2026-09-29) — multis DISABLED

Code: `bet_selection_v2/multi.py` (schema plus dependency assessment only; there is no writer and no selection).

## Leg eligibility
A leg must itself be a valid prediction from a validated engine with a fresh real price, decided `PAPER_BET` or
`MULTI_RESEARCH_ELIGIBLE`. Research-only, provisional (Double Chance) and WATCH-for-engine-status legs are excluded.

## Dependency flags (each assessed; none assumed away)
| flag | rule | effect |
|---|---|---|
| SAME_EVENT | same event_key | **blocked** (same-event multis stay disabled) |
| SAME_PARTICIPANT | a player/team appears in both legs | **blocked** |
| SAME_TOURNAMENT_DRAW | same tennis tournament (bracket paths, conditions, scheduling) | flagged: dependent |
| SAME_COMPETITION_ROUND | same football competition within 72 h | flagged: dependent |
| SAME_DAY_SAME_SPORT | shared day and sport (common shocks: weather, venue, data outage) | flagged: weak dependence |
| NONE_DETECTED | none of the above | independence assumed **for research only** |

`joint_probability_independent = ∏ P` is reported only as an upper-bound working figure. Any dependency flag marks the
joint probability `UNVALIDATED`.

## Combined odds
Never fabricated. `combined_price_source` is `QUOTED` only when a real multi price was observed from a named book at a
timestamp. Otherwise it is `NOT_QUOTED`, and the product of leg prices is shown as `theoretical_product_odds` and never
used for a decision.

## Activation gate (pre-registered)
Paper multis may be switched on (a config change with a new rule_version, Fraser's approval) only when **all** of these hold:
1. each contributing engine has ≥ 100 settled prospective predictions at P ≥ 80%, with a calibration gap ≤ 3 pp and no −10 pp alarm;
2. a dependency study on ≥ 200 prospective pairs of the proposed pair type shows joint hit rate within the 95% CI of ∏P;
3. ≥ 50 settled paper singles show the legs' realised hit rate within 95% CI of predicted;
4. real quoted multi prices are available for the proposed pair type.
Until then: `multi.enabled: false`.
