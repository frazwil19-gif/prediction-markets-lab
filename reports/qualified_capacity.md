# Qualified Turnover Capacity & expected vs realised (qtc-2, 2026-10-31T00:39Z)

## Expected vs realised (paper qualifying bets, £1 each)

Settled 11 (open 1). Expected profit **£0.54** vs realised **£-2.19**. Expected wins 7.62 vs actual 6 (z -1.07).

Small samples: |wins_z| < 2 is ordinary noise; do not react to it (first-weekend rule).

Capacity below uses only rule **bsv2-4** (87 evaluation runs). Paper bets by rule version: {'bsv2-1': 9, 'bsv2-3': 1, 'bsv2-4': 2}.

## Capacity

2 qualifying bets over 31 days → 1.9/month (LOW_SAMPLE; bets on 2 of those days). Odds mean 1.53 / median 1.53; net EV mean 0.0278 / median 0.0278.

| Group | Bets | /month | Odds mean | EV mean |
|---|---|---|---|---|
| engine=atp_match_winner.betfair_market | 1 | 1.0 | 1.53 | 0.0239 |
| engine=wta_match_winner.betfair_market | 1 | 1.0 | 1.53 | 0.0317 |
| market=tennis:match_winner | 2 | 1.9 | 1.53 | 0.0278 |
| sport=tennis | 2 | 1.9 | 1.53 | 0.0278 |

| Flat stake | Turnover/month | Expected profit/month |
|---|---|---|
| £1 | £1.94 | £0.05 |
| £5 | £9.68 | £0.27 |
| £10 | £19.35 | £0.54 |

| Bankroll | Stake | Daily cap | Max bets/day | Exp. profit/month (no cap) | after daily cap | Turnover/month |
|---|---|---|---|---|---|---|
| £50 | £1.0 | £5.0 | 5 | £0.05 | £0.05 | £1.94 |
| £100 | £2.0 | £10.0 | 5 | £0.11 | £0.11 | £3.87 |
| £250 | £5.0 | £25.0 | 5 | £0.27 | £0.27 | £9.68 |
| £500 | £10.0 | £50.0 | 5 | £0.54 | £0.54 | £19.35 |
| £1000 | £20.0 | £100.0 | 5 | £1.08 | £1.08 | £38.71 |

Limits:
- **theoretical**: all qualifying bets staked (no caps) — bankroll_scenarios.*.theoretical
- **opportunity**: 1.9 qualifying bets/month observed — the binding limit while this is small
- **daily_cap**: bets beyond the daily cap dropped (lowest EV first) — bankroll_scenarios.*.after_daily_cap
- **bankroll**: stake = fraction of bankroll (illustrative 2%; live policy is £1 flat)
- **execution_price**: UNMEASURED — needs Bet Log fills (odds taken vs card price, min-odds misses)

Expected profit uses the model's own EV estimates; real edge is unproven until settled results and CLV accrue.

## Rejection categories (latest evaluation per prediction)

2420 predictions evaluated.

- ENGINE_STATUS_INELIGIBLE: 1947
- NET_EV_NOT_POSITIVE: 1096
- P_BELOW_FLOOR: 914
- NO_EXECUTABLE_PRICE: 909
- COMMISSION_UNKNOWN: 219
- PREDICTION_NOT_VALID: 45
- PRICE_STALE: 40
- EXCHANGE_SPREAD_TOO_WIDE: 25
- NET_EV_BELOW_PAPER_GATE: 7
- PROBABILITY_NOT_SAME_SNAPSHOT: 5
- ODDS_BELOW_PAYOUT_FLOOR: 3

Bankroll scenarios are illustrative (2% flat, 10% daily cap); live policy stays £1 flat, £5/day.
