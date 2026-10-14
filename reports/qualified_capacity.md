# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-10-14T00:15Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 9 (open 2). Expected profit **£0.48** vs realised **£-1.72**. Expected wins 6.28 vs actual 5 (z -0.94).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (36 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 1}.

## Capacity

1 qualifying bets over 14 days → 2.1/month (LOW_SAMPLE; bets on 1 of those days). Odds mean 1.53 / median 1.53; net EV mean 0.0317 / median 0.0317.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=wta_match_winner.betfair_market | 1 | 2.1 | 1.53 | 0.0317 |
| market=tennis:match_winner | 1 | 2.1 | 1.53 | 0.0317 |
| sport=tennis | 1 | 2.1 | 1.53 | 0.0317 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £2.14 | £0.07 |
| £5 | £10.71 | £0.34 |
| £10 | £21.43 | £0.68 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.07 | £0.07 | £2.14 |
| £100 | £2.0 | £10.0 | 5 | £0.14 | £0.14 | £4.29 |
| £250 | £5.0 | £25.0 | 5 | £0.34 | £0.34 | £10.71 |
| £500 | £10.0 | £50.0 | 5 | £0.68 | £0.68 | £21.43 |
| £1000 | £20.0 | £100.0 | 5 | £1.36 | £1.36 | £42.86 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 2.1 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

1263 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 930
- NET_EV_NOT_POSITIVE: 619
- P_BELOW_FLOOR: 449
- NO_EXECUTABLE_PRICE: 444
- COMMISSION_UNKNOWN: 101
- PREDICTION_NOT_VALID: 45
- PRICE_STALE: 25
- EXCHANGE_SPREAD_TOO_WIDE: 13
- NET_EV_BELOW_PAPER_GATE: 7
- PROBABILITY_NOT_SAME_SNAPSHOT: 4
- ODDS_BELOW_PAYOUT_FLOOR: 3

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
