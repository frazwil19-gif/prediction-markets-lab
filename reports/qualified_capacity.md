# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-10-24T23:05Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 11 (open 1). Expected profit **£0.54** vs realised **£-2.19**. Expected wins 7.62 vs actual 6 (z -1.07).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (69 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 2}.

## Capacity

2 qualifying bets over 24 days → 2.5/month (LOW_SAMPLE; bets on 2 of those days). Odds mean 1.53 / median 1.53; net EV mean 0.0278 / median 0.0278.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 1.2 | 1.53 | 0.0239 |
| engine=wta_match_winner.betfair_market | 1 | 1.2 | 1.53 | 0.0317 |
| market=tennis:match_winner | 2 | 2.5 | 1.53 | 0.0278 |
| sport=tennis | 2 | 2.5 | 1.53 | 0.0278 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £2.5 | £0.07 |
| £5 | £12.5 | £0.35 |
| £10 | £25.0 | £0.7 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.07 | £0.07 | £2.5 |
| £100 | £2.0 | £10.0 | 5 | £0.14 | £0.14 | £5.0 |
| £250 | £5.0 | £25.0 | 5 | £0.35 | £0.35 | £12.5 |
| £500 | £10.0 | £50.0 | 5 | £0.7 | £0.7 | £25.0 |
| £1000 | £20.0 | £100.0 | 5 | £1.39 | £1.39 | £50.0 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 2.5 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

2114 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 1648
- NET_EV_NOT_POSITIVE: 979
- P_BELOW_FLOOR: 779
- NO_EXECUTABLE_PRICE: 774
- COMMISSION_UNKNOWN: 189
- PREDICTION_NOT_VALID: 45
- PRICE_STALE: 38
- EXCHANGE_SPREAD_TOO_WIDE: 25
- NET_EV_BELOW_PAPER_GATE: 7
- PROBABILITY_NOT_SAME_SNAPSHOT: 5
- ODDS_BELOW_PAYOUT_FLOOR: 3

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
