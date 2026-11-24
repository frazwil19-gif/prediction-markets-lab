# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-11-24T05:15Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 12 (open 1). Expected profit **£0.56** vs realised **£-1.57**. Expected wins 8.25 vs actual 7 (z -0.79).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (157 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 3}.

## Capacity

3 qualifying bets over 55 days → 1.6/month (LOW_SAMPLE; bets on 3 of those days). Odds mean 1.56 / median 1.53; net EV mean 0.026 / median 0.0239.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 0.5 | 1.53 | 0.0239 |
| engine=wta_match_winner.betfair_market | 2 | 1.1 | 1.575 | 0.027 |
| market=tennis:match_winner | 3 | 1.6 | 1.56 | 0.026 |
| sport=tennis | 3 | 1.6 | 1.56 | 0.026 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £1.64 | £0.04 |
| £5 | £8.18 | £0.21 |
| £10 | £16.36 | £0.42 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.04 | £0.04 | £1.64 |
| £100 | £2.0 | £10.0 | 5 | £0.08 | £0.08 | £3.27 |
| £250 | £5.0 | £25.0 | 5 | £0.21 | £0.21 | £8.18 |
| £500 | £10.0 | £50.0 | 5 | £0.42 | £0.42 | £16.36 |
| £1000 | £20.0 | £100.0 | 5 | £0.85 | £0.85 | £32.73 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 1.6 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

4155 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 3309
- NET_EV_NOT_POSITIVE: 1831
- P_BELOW_FLOOR: 1559
- NO_EXECUTABLE_PRICE: 1548
- COMMISSION_UNKNOWN: 414
- PRICE_STALE: 71
- PREDICTION_NOT_VALID: 66
- EXCHANGE_SPREAD_TOO_WIDE: 34
- NET_EV_BELOW_PAPER_GATE: 12
- PROBABILITY_NOT_SAME_SNAPSHOT: 7
- ODDS_BELOW_PAYOUT_FLOOR: 3

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
