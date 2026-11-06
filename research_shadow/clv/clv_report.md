# CLV report (clv-1, 2026-11-06T14:34Z)

Credits 2026-11: 0 of 100 (0 paid calls). Missed captures logged: 19.

## PAPER_BET (live-rule) CLV

Targets 2, captured 0.

- fair-CLV: n 0
- price-CLV (same book): n 0
- price-CLV (best UK): n 0

**By sport:** tennis: n 0

**By engine:** atp_match_winner.betfair_market: n 0 · wta_match_winner.betfair_market: n 0

**By market:** tennis:match_winner: n 0

**By bookmaker:** betfair_sb_uk: n 0 · boylesports: n 0

**By ev_band:** 2-4: n 0

## Tennis EV-band study (pre-registered; research only — live rule stays EV ≥ 2%)

Study start 2026-10-08T17:53Z. Combined 0–2% Tier-A captures: **0** (looks at [100, 200]; reached: none).

| Band | N | est. EV mean | Tier A captured/eligible | top-book share | fair-CLV | Tier-B proxy | settled / ROI |
|---|---|---|---|---|---|---|---|
| <0 | 158 | -1.78% | 0/0 | 0.38 | n 0 | n 81 · mean -1.80% · median -1.50% · positive 7% CI [-2.15%, -1.43%] | 111 / -0.1169 |
| 0-1 | 3 | +0.67% | 0/3 | 0.667 | sealed | sealed | sealed |
| 1-2 | 2 | +1.44% | 0/2 | 0.5 | sealed | sealed | sealed |
| 2-4 | 2 | +2.79% | 0/2 | 0.5 | n 0 | n 2 · mean +2.25% · median +2.25% · positive 100% | 2 / -0.235 |
| 4+ | 0 |  | 0/0 | None | n 0 | n 0 | 0 / None |

Definitions: fair_clv = (1+(odds-1)(1-commission)) x p_close - 1 (tennis p_close = Betfair back/lay mid; others UK median fair); price_clv_same_book = entry odds / same book closing odds - 1; price_clv_best = entry odds / best UK closing odds - 1; p_move = p_close - p_entry
