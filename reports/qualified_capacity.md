# Qualified Turnover Capacity & expected vs realised (qtc-1, 2026-10-08T12:06Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 9 (open 1). Expected profit **£0.48** vs realised **£-1.72**. Expected wins 6.28 vs actual 5 (z -0.94).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

## Capacity

10 qualifying bets over 10 days → 30.0/month (LOW_SAMPLE; bets on 1 of those days). Odds mean 1.544 / median 1.5; net EV mean 0.0505 / median 0.0366.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 3.0 | 1.4 | 0.0288 |
| engine=wta_match_winner.betfair_market | 9 | 27.0 | 1.56 | 0.053 |
| market=tennis:match_winner | 10 | 30.0 | 1.544 | 0.0505 |
| sport=tennis | 10 | 30.0 | 1.544 | 0.0505 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £30.0 | £1.52 |
| £5 | £150.0 | £7.58 |
| £10 | £300.0 | £15.16 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £1.52 | £1.08 | £15.0 |
| £100 | £2.0 | £10.0 | 5 | £3.03 | £2.16 | £30.0 |
| £250 | £5.0 | £25.0 | 5 | £7.58 | £5.4 | £75.0 |
| £500 | £10.0 | £50.0 | 5 | £15.16 | £10.8 | £150.0 |
| £1000 | £20.0 | £100.0 | 5 | £30.32 | £21.59 | £300.0 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 30.0 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

182 predictions evaluated.

- NET_EV_NOT_POSITIVE: 171
- PREDICTION_NOT_VALID: 21
- EXCHANGE_SPREAD_TOO_WIDE: 8
- COMMISSION_UNKNOWN: 6
- NET_EV_BELOW_PAPER_GATE: 4
- ODDS_BELOW_PAYOUT_FLOOR: 2
- PROBABILITY_NOT_SAME_SNAPSHOT: 1
- P_BELOW_FLOOR: 1

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
