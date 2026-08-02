# Market Rules

**Status: reference document. Automated market-rule matching
(`normalisation/market_matching.py`) is planned for Stage 2; today this
is a manual checklist.**

## Tier 1 markets (active)

### Football

- **Pre-match 1X2** — full-time result: home win / draw / away win.
  Ensure bookmaker and exchange settlement both use 90 minutes plus
  stoppage time, excluding extra time/penalties.
- **Over/under 2.5 goals** — total goals scored by both teams in
  regulation plus stoppage time. Confirm the same line (2.5) is being
  compared across bookmaker and exchange; do not mix lines.
- *Draw-no-bet* — may be added later (not active in Stage 1).

Active leagues: Premier League, Championship, Scottish Premiership,
Champions League, and other major competitions only once bookmaker
coverage is confirmed strong (`config/competitions.yaml`).

### Tennis

- **Pre-match match winner** — winner of the full match (best of 3 or
  best of 5 as scheduled). Confirm retirement/walkover rules match
  between bookmaker and exchange before comparing prices.

Avoid initially: set betting, game handicaps, exact scores, in-play
points, obscure low-liquidity tournaments.

## Before comparing any bookmaker price to an exchange price

1. Confirm the event, market type, and selection are identical.
2. Confirm the settlement rules (regulation time only, walkover
   handling, void conditions) match.
3. Confirm the price is current, not stale.
4. Confirm adequate exchange liquidity exists at that price.

If any of these fail, the market should be rejected —
`decisions.grading.grade_opportunity` enforces this via the
`exchange_price_current`, `market_rules_match`, and
`liquidity_adequate` gates.
