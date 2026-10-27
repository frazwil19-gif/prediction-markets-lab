# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-10-27T00:22Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 11 (open 1). Expected profit **£0.54** vs realised **£-2.19**. Expected wins 7.62 vs actual 6 (z -1.07).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (75 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 2}.

## Capacity

2 qualifying bets over 27 days → 2.2/month (LOW_SAMPLE; bets on 2 of those days). Odds mean 1.53 / median 1.53; net EV mean 0.0278 / median 0.0278.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 1.1 | 1.53 | 0.0239 |
| engine=wta_match_winner.betfair_market | 1 | 1.1 | 1.53 | 0.0317 |
| market=tennis:match_winner | 2 | 2.2 | 1.53 | 0.0278 |
| sport=tennis | 2 | 2.2 | 1.53 | 0.0278 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £2.22 | £0.06 |
| £5 | £11.11 | £0.31 |
| £10 | £22.22 | £0.62 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.06 | £0.06 | £2.22 |
| £100 | £2.0 | £10.0 | 5 | £0.12 | £0.12 | £4.44 |
| £250 | £5.0 | £25.0 | 5 | £0.31 | £0.31 | £11.11 |
| £500 | £10.0 | £50.0 | 5 | £0.62 | £0.62 | £22.22 |
| £1000 | £20.0 | £100.0 | 5 | £1.24 | £1.24 | £44.44 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 2.2 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

2127 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 1654
- NET_EV_NOT_POSITIVE: 988
- P_BELOW_FLOOR: 782
- NO_EXECUTABLE_PRICE: 777
- COMMISSION_UNKNOWN: 190
- PREDICTION_NOT_VALID: 45
- PRICE_STALE: 40
- EXCHANGE_SPREAD_TOO_WIDE: 25
- NET_EV_BELOW_PAPER_GATE: 7
- PROBABILITY_NOT_SAME_SNAPSHOT: 5
- ODDS_BELOW_PAYOUT_FLOOR: 3

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
