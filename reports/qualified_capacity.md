# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-10-15T23:39Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 10 (open 2). Expected profit **£0.51** vs realised **£-2.72**. Expected wins 6.95 vs actual 5 (z -1.36).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (42 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 2}.

## Capacity

2 qualifying bets over 15 days → 4.0/month (LOW_SAMPLE; bets on 2 of those days). Odds mean 1.53 / median 1.53; net EV mean 0.0278 / median 0.0278.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 2.0 | 1.53 | 0.0239 |
| engine=wta_match_winner.betfair_market | 1 | 2.0 | 1.53 | 0.0317 |
| market=tennis:match_winner | 2 | 4.0 | 1.53 | 0.0278 |
| sport=tennis | 2 | 4.0 | 1.53 | 0.0278 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £4.0 | £0.11 |
| £5 | £20.0 | £0.56 |
| £10 | £40.0 | £1.11 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.11 | £0.11 | £4.0 |
| £100 | £2.0 | £10.0 | 5 | £0.22 | £0.22 | £8.0 |
| £250 | £5.0 | £25.0 | 5 | £0.56 | £0.56 | £20.0 |
| £500 | £10.0 | £50.0 | 5 | £1.11 | £1.11 | £40.0 |
| £1000 | £20.0 | £100.0 | 5 | £2.23 | £2.23 | £80.0 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 4.0 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

1316 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 955
- NET_EV_NOT_POSITIVE: 644
- P_BELOW_FLOOR: 461
- NO_EXECUTABLE_PRICE: 456
- COMMISSION_UNKNOWN: 112
- PREDICTION_NOT_VALID: 45
- PRICE_STALE: 29
- EXCHANGE_SPREAD_TOO_WIDE: 15
- NET_EV_BELOW_PAPER_GATE: 6
- PROBABILITY_NOT_SAME_SNAPSHOT: 4
- ODDS_BELOW_PAYOUT_FLOOR: 2

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
