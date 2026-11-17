# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-11-17T03:41Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 11 (open 2). Expected profit **£0.54** vs realised **£-2.19**. Expected wins 7.62 vs actual 6 (z -1.07).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (136 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 3}.

## Capacity

3 qualifying bets over 48 days → 1.9/month (LOW_SAMPLE; bets on 3 of those days). Odds mean 1.56 / median 1.53; net EV mean 0.026 / median 0.0239.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 0.6 | 1.53 | 0.0239 |
| engine=wta_match_winner.betfair_market | 2 | 1.2 | 1.575 | 0.027 |
| market=tennis:match_winner | 3 | 1.9 | 1.56 | 0.026 |
| sport=tennis | 3 | 1.9 | 1.56 | 0.026 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £1.88 | £0.05 |
| £5 | £9.38 | £0.24 |
| £10 | £18.75 | £0.49 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.05 | £0.05 | £1.88 |
| £100 | £2.0 | £10.0 | 5 | £0.1 | £0.1 | £3.75 |
| £250 | £5.0 | £25.0 | 5 | £0.24 | £0.24 | £9.38 |
| £500 | £10.0 | £50.0 | 5 | £0.49 | £0.49 | £18.75 |
| £1000 | £20.0 | £100.0 | 5 | £0.97 | £0.97 | £37.5 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 1.9 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

3511 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 2730
- NET_EV_NOT_POSITIVE: 1599
- P_BELOW_FLOOR: 1287
- NO_EXECUTABLE_PRICE: 1278
- COMMISSION_UNKNOWN: 344
- PRICE_STALE: 68
- PREDICTION_NOT_VALID: 66
- EXCHANGE_SPREAD_TOO_WIDE: 33
- NET_EV_BELOW_PAPER_GATE: 11
- PROBABILITY_NOT_SAME_SNAPSHOT: 7
- ODDS_BELOW_PAYOUT_FLOOR: 3

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
